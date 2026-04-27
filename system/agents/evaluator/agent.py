"""evaluator agent.

Backs ``evaluator-cv`` for Session 2 and ``evaluator-query`` for Session 4.
The same Python process serves both through capability-id dispatch in
``handle``.

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

QUERY_SYSTEM_PROMPT = (
    "You are a passage relevance evaluator. You rank parsed research-note "
    "passages against a user question. You always respond with a single JSON "
    "object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "evaluator-cv":
        return await _evaluate_cv(inputs, ctx)
    if capability_id == "evaluator-query":
        return await _evaluate_query(inputs, ctx)
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


async def _evaluate_query(inputs: dict, ctx: Context) -> dict:
    question = inputs.get("question")
    parsed_note = inputs.get("parsed_note")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")
    if not isinstance(parsed_note, dict):
        return error_envelope("parsed_note (object) is required")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Question\n\n{question}\n\n"
        f"## Parsed note\n\n```json\n{json.dumps(parsed_note, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=QUERY_SYSTEM_PROMPT, temperature=0.1)
    evaluation, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(evaluation, dict):
        return error_envelope("query evaluation must be a JSON object")

    ranked = evaluation.get("ranked_passages")
    scores = [
        item.get("relevance")
        for item in ranked
        if isinstance(item, dict) and isinstance(item.get("relevance"), int)
    ] if isinstance(ranked, list) else []
    return {
        "outputs": evaluation,
        "signals": {
            "valid_output_shape": True,
            "has_ranked_passages": isinstance(ranked, list) and len(ranked) > 0,
            "score_distribution_not_degenerate": len(set(scores)) > 1 if len(scores) > 1 else bool(scores),
            "latency_seconds": completion.latency_seconds,
        },
    }


if __name__ == "__main__":
    run(handle)
