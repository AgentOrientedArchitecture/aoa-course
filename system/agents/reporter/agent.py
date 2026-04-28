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

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Question\n\n{question}\n\n"
        f"## Parsed note\n\n```json\n{json.dumps(parsed_note, indent=2)}\n```\n\n"
        f"## Evaluation\n\n```json\n{json.dumps(evaluation, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=ANSWER_SYSTEM_PROMPT, temperature=0.2)
    answer, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(answer, dict):
        return error_envelope("answer must be a JSON object")

    citations = answer.get("citations")
    answer["answer_markdown"] = _answer_markdown(answer)
    return {
        "outputs": answer,
        "signals": {
            "valid_output_shape": True,
            "has_answer": isinstance(answer.get("answer"), str) and bool(answer.get("answer")),
            "has_citations": isinstance(citations, list) and len(citations) > 0,
            "has_markdown": bool(answer.get("answer_markdown")),
            "latency_seconds": completion.latency_seconds,
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
