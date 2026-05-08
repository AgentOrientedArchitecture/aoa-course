"""reporter agent.

Backs ``reporter-cv-fit`` for Session 2, plus Session 4 answer and ingest
reporting. Some reporter capabilities only consume structured data; others
use a declared tool to store the finished result.
"""
from __future__ import annotations

import json

from _base.base import Context, run
from _base.json_utils import error_envelope, parse_json


SYSTEM_PROMPT = (
    "You are a hiring report writer. Given a parsed CV and a JD evaluation, "
    "you produce a short, decisive report for a human reader. You always "
    "respond with a single JSON object - no preamble, no commentary, "
    "no code fence."
)

ANSWER_SYSTEM_PROMPT = (
    "You are a grounded knowledge-base answer writer. You answer using only "
    "the provided parsed note and evaluation. You always respond with a "
    "single JSON object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "reporter-cv-fit":
        return await _report_cv_fit(inputs, ctx)
    if capability_id == "reporter-answer":
        return await _report_answer(inputs, ctx)
    if capability_id == "reporter-ingest-summary":
        return await _report_ingest_summary(inputs, ctx)
    return error_envelope(f"reporter does not back capability {capability_id!r}")


async def _report_cv_fit(inputs: dict, ctx: Context) -> dict:
    cv = inputs.get("cv")
    evaluation = inputs.get("evaluation")
    if not isinstance(cv, dict):
        return error_envelope("cv (parsed object) is required")
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation (object) is required")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Parsed CV\n\n```json\n{json.dumps(cv, indent=2)}\n```\n\n"
        f"## Evaluation\n\n```json\n{json.dumps(evaluation, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=SYSTEM_PROMPT, temperature=0.2)
    report, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(report, dict):
        return error_envelope("report must be a JSON object")

    headline = report.get("headline")
    recommendation = report.get("recommendation")
    report["report_markdown"] = _cv_report_markdown(report)
    return {
        "outputs": report,
        "signals": {
            "valid_output_shape": True,
            "has_headline": isinstance(headline, str) and len(headline) > 0,
            "has_recommendation": recommendation in {"interview", "hold", "pass"},
            "has_markdown": bool(report.get("report_markdown")),
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _report_answer(inputs: dict, ctx: Context) -> dict:
    question = inputs.get("question")
    parsed_note = inputs.get("parsed_note")
    evaluation = inputs.get("evaluation")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")
    if not isinstance(parsed_note, dict):
        return error_envelope("parsed_note (object) is required")
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation (object) is required")

    answer = _grounded_wiki_answer(question, parsed_note, evaluation)
    citations = answer.get("citations")
    answer["answer_markdown"] = _answer_markdown(answer)
    return {
        "outputs": answer,
        "signals": {
            "valid_output_shape": True,
            "has_answer": isinstance(answer.get("answer"), str) and bool(answer.get("answer")),
            "has_citations": isinstance(citations, list) and len(citations) > 0,
            "has_markdown": bool(answer.get("answer_markdown")),
            "grounded_from_passages": True,
            "latency_seconds": 0,
        },
    }


async def _report_ingest_summary(inputs: dict, ctx: Context) -> dict:
    promotion = inputs.get("promotion")
    source_path = inputs.get("source_path")
    if not isinstance(promotion, dict):
        return error_envelope("promotion (object) is required")
    if not isinstance(source_path, str) or not source_path.strip():
        return error_envelope("source_path is required")
    wiki_store = ctx.tools.get("tool-wiki-store")
    if wiki_store is None:
        return error_envelope("tool-wiki-store is not available")

    stored_outputs = await wiki_store({
        "op": "write_ingest",
        "promotion": promotion,
        "source_path": source_path,
    })
    stored = stored_outputs.get("stored")
    if not isinstance(stored, dict):
        return error_envelope(stored_outputs.get("error") or "wiki store did not return stored result")

    markdown = _ingest_markdown(promotion, source_path, stored)
    return {
        "outputs": {
            "stored": stored,
            "ingest_markdown": markdown,
        },
        "signals": {
            "valid_output_shape": True,
            "stored_document": bool(stored.get("document_id")),
            "has_markdown": bool(markdown),
            "passage_count": stored.get("passage_count", 0),
            "latency_seconds": 0,
        },
    }


def _cv_report_markdown(report: dict) -> str:
    headline = str(report.get("headline") or "CV fit report").strip()
    summary = str(report.get("summary") or "").strip()
    recommendation = str(report.get("recommendation") or "").strip()
    highlights = report.get("highlights") if isinstance(report.get("highlights"), list) else []
    concerns = report.get("concerns") if isinstance(report.get("concerns"), list) else []

    lines = [f"# {headline}", ""]
    if recommendation:
        lines += [f"**Recommendation:** {recommendation}", ""]
    if summary:
        lines += [summary, ""]
    lines += _markdown_list("Highlights", highlights)
    lines += _markdown_list("Concerns", concerns)
    return "\n".join(lines).strip()


def _answer_markdown(answer: dict) -> str:
    body = str(answer.get("answer") or "").strip()
    confidence = str(answer.get("confidence") or "").strip()
    citations = answer.get("citations") if isinstance(answer.get("citations"), list) else []
    gaps = answer.get("gaps") if isinstance(answer.get("gaps"), list) else []
    follow_ups = answer.get("follow_ups") if isinstance(answer.get("follow_ups"), list) else []

    lines = ["# Answer", ""]
    if body:
        lines += [body, ""]
    if confidence:
        lines += [f"**Confidence:** {confidence}", ""]
    lines += _markdown_list("Citations", citations)
    lines += _markdown_list("Gaps", gaps)
    lines += _markdown_list("Follow-ups", follow_ups)
    return "\n".join(lines).strip()


def _grounded_wiki_answer(question: str, parsed_note: dict, evaluation: dict) -> dict:
    """Build the wiki answer from retrieved passages only.

    This is stricter than the CV reporter path on purpose: it prevents the
    model's prior knowledge from leaking into the Session 4 knowledge-base
    answer and makes citation behaviour easy to inspect.
    """
    passages = parsed_note.get("passages") if isinstance(parsed_note.get("passages"), list) else []
    by_id = {
        str(p.get("passage_id")): p
        for p in passages
        if isinstance(p, dict) and p.get("passage_id")
    }
    ranked = evaluation.get("ranked_passages") if isinstance(evaluation.get("ranked_passages"), list) else []
    cited: list[dict] = []
    seen: set[str] = set()
    for item in ranked:
        if not isinstance(item, dict):
            continue
        passage_id = str(item.get("passage_id") or "")
        if passage_id in by_id and passage_id not in seen:
            cited.append(by_id[passage_id])
            seen.add(passage_id)
        if len(cited) >= 8:
            break

    if not cited:
        return {
            "answer": "The wiki does not currently contain enough cited evidence to answer this question.",
            "citations": [],
            "gaps": _string_list(evaluation.get("gaps")) or ["No relevant passages were retrieved."],
            "follow_ups": ["Ingest source material that directly addresses the question."],
            "confidence": "low",
        }

    principle_rows = _principle_rows(cited)
    if _asks_for_principles(question) and principle_rows:
        answer = "The retrieved wiki evidence supports these AOA principles: " + "; ".join(
            f"{name}: {quote}" for name, quote, _pid in principle_rows
        ) + "."
        citations = [pid for _name, _quote, pid in principle_rows]
    else:
        answer = "The retrieved wiki evidence says: " + " ".join(
            f"{_clean_sentence(str(p.get('quote') or ''))} ({p.get('passage_id')})."
            for p in cited[:3]
            if str(p.get("quote") or "").strip()
        ).strip()
        citations = [str(p.get("passage_id")) for p in cited[:3]]

    direct = bool(evaluation.get("direct_answer_possible"))
    return {
        "answer": answer,
        "citations": citations,
        "gaps": _string_list(evaluation.get("gaps")) if direct else (
            _string_list(evaluation.get("gaps")) or ["The answer is partial because retrieval did not mark the evidence as directly sufficient."]
        ),
        "follow_ups": [],
        "confidence": "high" if direct and len(citations) >= 3 else "medium",
    }


def _asks_for_principles(question: str) -> bool:
    lowered = question.lower()
    return "principle" in lowered and ("aoa" in lowered or "agent" in lowered)


def _principle_rows(passages: list[dict]) -> list[tuple[str, str, str]]:
    rows = []
    for passage in passages:
        pid = str(passage.get("passage_id") or "")
        quote = _clean_sentence(str(passage.get("quote") or ""))
        why = str(passage.get("why_it_matters") or "")
        name = _principle_name(why)
        if name and quote and pid:
            rows.append((name, quote, pid))
    order = {"Decompose": 0, "Compose": 1, "Substitute": 2, "Trust": 3}
    rows.sort(key=lambda row: (order.get(row[0], 99), row[0]))
    unique = []
    seen = set()
    for row in rows:
        if row[0] not in seen:
            unique.append(row)
            seen.add(row[0])
    return unique


def _principle_name(text: str) -> str:
    for name in ("Decompose", "Compose", "Substitute", "Trust"):
        if name.lower() in text.lower():
            return name
    return ""


def _clean_sentence(text: str) -> str:
    return text.strip().rstrip(".")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _ingest_markdown(promotion: dict, source_path: str, stored: dict) -> str:
    title = str(promotion.get("title") or "Wiki ingest").strip()
    summary = str(promotion.get("summary") or "").strip()
    concepts = promotion.get("concepts") if isinstance(promotion.get("concepts"), list) else []
    open_questions = (
        promotion.get("open_questions")
        if isinstance(promotion.get("open_questions"), list)
        else []
    )
    promoted_passages = (
        promotion.get("promoted_passages")
        if isinstance(promotion.get("promoted_passages"), list)
        else []
    )

    lines = [f"# Ingested: {title}", "", f"**Source:** `{source_path}`", ""]
    if summary:
        lines += [summary, ""]
    lines += [
        "## Stored",
        f"- Raw: `{stored.get('raw_path', '')}`",
        f"- Promoted: `{stored.get('promoted_path', '')}`",
        f"- Passages indexed: {stored.get('passage_count', 0)}",
        "",
    ]
    lines += _markdown_list(
        "Concepts",
        [_concept_label(item) for item in concepts],
    )
    lines += _markdown_list(
        "Promoted Passages",
        [_passage_label(item) for item in promoted_passages],
    )
    lines += _markdown_list("Open Questions", open_questions)
    return "\n".join(lines).strip()


def _concept_label(value: object) -> str:
    if isinstance(value, dict):
        name = str(value.get("name") or "").strip()
        description = str(value.get("description") or "").strip()
        return f"{name}: {description}" if name and description else name or description
    return str(value).strip()


def _passage_label(value: object) -> str:
    if isinstance(value, dict):
        passage_id = str(value.get("passage_id") or "").strip()
        why = str(value.get("why_it_matters") or "").strip()
        return f"{passage_id}: {why}" if passage_id and why else passage_id or why
    return str(value).strip()


def _markdown_list(title: str, values: list) -> list[str]:
    if not values:
        return []
    lines = [f"## {title}"]
    for value in values:
        text = str(value).strip()
        if text:
            lines.append(f"- {text}")
    return lines + [""]


if __name__ == "__main__":
    run(handle)
