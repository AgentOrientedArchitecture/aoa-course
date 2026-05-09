"""evaluator agent.

Backs ``evaluator-cv`` for Session 2, plus wiki promotion and wiki-query
evidence evaluation for Session 4. The same Python process serves each through
capability-id dispatch in ``handle``.

For ``evaluator-cv`` we receive a parsed CV (the parser's output) and a path
to a job description on the shared inbox volume. We read the JD through
``tool-document-text`` so the call shows up in the trace, hand both to the
model with the rubric in ``skills.md``, and return a JSON evaluation.
"""
from __future__ import annotations

import json

from _base.base import Context, run
from _base.json_utils import error_envelope, parse_json


SYSTEM_PROMPT = (
    "You are a hiring evaluator. You assess how well a candidate fits a job "
    "description. You always respond with a single JSON object - no "
    "preamble, no commentary, no code fence."
)

PROMOTE_SYSTEM_PROMPT = (
    "You are a knowledge promotion evaluator for an Agent-oriented Architecture "
    "wiki. You always respond with a single JSON object - no preamble, no "
    "commentary, no code fence."
)

WIKI_QUERY_SYSTEM_PROMPT = (
    "You are a wiki evidence evaluator. You always respond with a single JSON "
    "object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "evaluator-cv":
        return await _evaluate_cv(inputs, ctx)
    if capability_id == "evaluator-promote":
        return await _promote_note(inputs, ctx)
    if capability_id == "evaluator-wiki-query":
        return await _evaluate_wiki_query(inputs, ctx)
    return error_envelope(f"evaluator does not back capability {capability_id!r}")


async def _evaluate_cv(inputs: dict, ctx: Context) -> dict:
    cv = inputs.get("cv")
    jd_path = inputs.get("jd_path")
    if not isinstance(cv, dict):
        return error_envelope("cv (parsed object) is required")
    if not jd_path:
        return error_envelope("jd_path is required")

    doc_text = ctx.tools.get("tool-document-text")
    if doc_text is None:
        return error_envelope("tool-document-text is not available")
    doc_outputs = await doc_text({"path": jd_path})
    jd_text = doc_outputs.get("text", "")
    if not jd_text.strip():
        return error_envelope(f"JD at {jd_path} was empty")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Job description\n\n{jd_text}\n\n"
        f"## Parsed CV\n\n```json\n{json.dumps(cv, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=SYSTEM_PROMPT, temperature=0.1)
    evaluation, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation must be a JSON object")

    scores = evaluation.get("scores")
    verdict = evaluation.get("verdict")
    return {
        "outputs": evaluation,
        "signals": {
            "valid_output_shape": True,
            "has_scores": isinstance(scores, dict) and len(scores) > 0,
            "has_verdict": verdict in {"strong", "fit", "weak", "no"},
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _promote_note(inputs: dict, ctx: Context) -> dict:
    parsed_note = inputs.get("parsed_note")
    source_path = inputs.get("source_path")
    if not isinstance(parsed_note, dict):
        return error_envelope("parsed_note (object) is required")
    if not isinstance(source_path, str) or not source_path.strip():
        return error_envelope("source_path is required")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Source path\n\n{source_path}\n\n"
        f"## Parsed note\n\n```json\n{json.dumps(parsed_note, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=PROMOTE_SYSTEM_PROMPT, temperature=0.1)
    promotion, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(promotion, dict):
        return error_envelope("promotion must be a JSON object")

    concepts = promotion.get("concepts")
    passages = promotion.get("promoted_passages")
    return {
        "outputs": {"promotion": promotion},
        "signals": {
            "valid_output_shape": True,
            "has_concepts": isinstance(concepts, list) and len(concepts) > 0,
            "has_promoted_passages": isinstance(passages, list) and len(passages) > 0,
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _evaluate_wiki_query(inputs: dict, ctx: Context) -> dict:
    question = inputs.get("question")
    query = inputs.get("query")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")
    if not isinstance(query, dict):
        return error_envelope("query object is required")

    wiki = ctx.tools.get("tool-wiki-store")
    if wiki is None:
        return error_envelope("tool-wiki-store is not available")
    search_text = " ".join(
        [question] + [str(term) for term in query.get("terms", []) if str(term).strip()]
    )
    search_outputs = await wiki({"op": "search", "query": search_text, "limit": 8})
    passages = search_outputs.get("passages", [])
    ranked = _rank_wiki_passages(passages)

    parsed_note = {
        "title": "Course wiki search results",
        "summary": f"Retrieved {len(passages)} passages from the course wiki.",
        "key_points": [],
        "entities": [],
        "candidate_concepts": query.get("terms", []),
        "passages": [
            {
                "passage_id": p.get("passage_id"),
                "quote": p.get("quote"),
                "why_it_matters": p.get("why_it_matters", ""),
                "source_path": p.get("source_path"),
            }
            for p in passages
            if isinstance(p, dict)
        ],
    }
    direct_answer_possible = bool(ranked and ranked[0].get("relevance", 0) >= 3)
    evaluation = {
        "ranked_passages": ranked,
        "direct_answer_possible": direct_answer_possible,
        "gaps": [] if direct_answer_possible else ["The wiki did not return enough cited passages to answer directly."],
        "rationale": (
            "Ranked deterministically from wiki-store retrieval scores; answer text must stay within returned passages."
        ),
        "parsed_note": parsed_note,
    }
    return {
        "outputs": evaluation,
        "signals": {
            "valid_output_shape": True,
            "has_ranked_passages": isinstance(ranked, list) and len(ranked) > 0,
            "passages_have_citations": all(
                isinstance(item, dict) and item.get("passage_id")
                for item in ranked
            ) if isinstance(ranked, list) else False,
            "latency_seconds": 0,
        },
    }


def _rank_wiki_passages(passages: object) -> list[dict]:
    """Convert wiki-store retrieval scores into evaluator output.

    The Session 4 query path is a grounding demo, so this capability keeps the
    ranking deterministic and citation-preserving instead of asking the model to
    judge sparse evidence.
    """
    if not isinstance(passages, list):
        return []
    ranked = []
    for passage in passages:
        if not isinstance(passage, dict) or not passage.get("passage_id"):
            continue
        score = int(passage.get("score") or 0)
        relevance = max(1, min(5, score))
        matched = passage.get("matched_terms") if isinstance(passage.get("matched_terms"), list) else []
        reason = (
            f"Matched wiki terms: {', '.join(str(term) for term in matched[:6])}."
            if matched
            else "Returned by wiki search."
        )
        ranked.append({
            "passage_id": passage["passage_id"],
            "relevance": relevance,
            "reason": reason,
        })
    ranked.sort(key=lambda item: (-item["relevance"], item["passage_id"]))
    return ranked


if __name__ == "__main__":
    run(handle)
