"""parser agent.

Backs ``parser-cv`` for the ``cv-parser`` runtime, plus ``parser-notes`` and
``parser-query`` for the ``wiki-parser`` runtime.
The shared scaffold in ``_base`` does the discovery, registration, and hot
reload work; this file is just the agent-specific wiring: build a prompt from
the loaded ``skills.md`` plus the inputs, call the model, parse the JSON
response, return it.
"""
from __future__ import annotations

from _base.base import Context, run
from _base.json_utils import error_envelope, parse_json


SYSTEM_PROMPT = (
    "You are a CV parser. You read a CV (in plain text) and extract a "
    "structured representation of it. You always respond with a single JSON "
    "object - no preamble, no commentary, no code fence."
)

NOTES_SYSTEM_PROMPT = (
    "You are a research-note parser. You extract structured knowledge from "
    "plain text notes. You always respond with a single JSON object - no "
    "preamble, no commentary, no code fence."
)

QUERY_SYSTEM_PROMPT = (
    "You are a retrieval query parser. You always respond with a single JSON "
    "object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "parser-cv":
        return await _parse_cv(inputs, ctx)
    if capability_id == "parser-notes":
        return await _parse_notes(inputs, ctx)
    if capability_id == "parser-query":
        return await _parse_query(inputs, ctx)
    return error_envelope(f"parser does not back capability {capability_id!r}")


async def _parse_cv(inputs: dict, ctx: Context) -> dict:
    cv_path = inputs.get("cv_path")
    if not cv_path:
        return error_envelope("cv_path is required")

    # Extract the CV through a registered tool so the trace shows the boundary.
    doc_text = ctx.tools.get("tool-document-text")
    if doc_text is None:
        return error_envelope("tool-document-text is not available")
    doc_outputs = await doc_text({"path": cv_path})
    cv_text = doc_outputs.get("text", "")
    if not cv_text.strip():
        return error_envelope(f"CV at {cv_path} was empty")

    prompt = f"{ctx.skills}\n\n## CV to parse\n\n{cv_text}\n"
    completion = ctx.model.complete(prompt, system=SYSTEM_PROMPT, temperature=0.1)
    parsed, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)

    return {
        "outputs": {"parsed": parsed},
        "signals": {
            "valid_output_shape": True,
            "has_name": bool(parsed.get("name")) if isinstance(parsed, dict) else False,
            "has_skills": isinstance(parsed.get("skills"), list) if isinstance(parsed, dict) else False,
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _parse_notes(inputs: dict, ctx: Context) -> dict:
    note_path = inputs.get("note_path")
    if not note_path:
        return error_envelope("note_path is required")

    doc_text = ctx.tools.get("tool-document-text")
    if doc_text is None:
        return error_envelope("tool-document-text is not available")
    doc_outputs = await doc_text({"path": note_path})
    note_text = doc_outputs.get("text", "")
    if not note_text.strip():
        return error_envelope(f"note at {note_path} was empty")

    prompt = f"{ctx.skills}\n\n## Research note to parse\n\n{note_text}\n"
    completion = ctx.model.complete(prompt, system=NOTES_SYSTEM_PROMPT, temperature=0.1)
    parsed, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(parsed, dict):
        return error_envelope("parsed note must be a JSON object")

    passages = parsed.get("passages")
    return {
        "outputs": {"parsed_note": parsed},
        "signals": {
            "valid_output_shape": True,
            "has_summary": isinstance(parsed.get("summary"), str) and bool(parsed.get("summary")),
            "has_passages": isinstance(passages, list) and len(passages) > 0,
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _parse_query(inputs: dict, ctx: Context) -> dict:
    question = inputs.get("question")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")

    prompt = f"{ctx.skills}\n\n## Question\n\n{question}\n"
    completion = ctx.model.complete(prompt, system=QUERY_SYSTEM_PROMPT, temperature=0.0)
    query, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(query, dict):
        return error_envelope("query must be a JSON object")

    terms = query.get("terms")
    return {
        "outputs": {"query": query},
        "signals": {
            "valid_output_shape": True,
            "has_terms": isinstance(terms, list) and len(terms) > 0,
            "latency_seconds": completion.latency_seconds,
        },
    }


if __name__ == "__main__":
    run(handle)
