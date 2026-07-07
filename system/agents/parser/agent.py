"""parser agent.

Backs ``parser-cv`` for the ``cv-parser`` runtime, plus ``parser-notes`` and
``parser-query`` for the ``wiki-parser`` runtime.
The shared scaffold in ``_base`` does the discovery, registration, and hot
reload work; this file is just the agent-specific wiring: build a prompt from
the loaded ``instructions.md`` plus the inputs, call the model, parse the JSON
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
    if capability_id == "parser-estate":
        return await _parse_estate(inputs, ctx)
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

# ----------------------------------------------------------------------
# parser-estate — deterministic estate inventory (no model call)
# ----------------------------------------------------------------------

import json as _json
import time as _time

_OVERSIGHT_MARKERS = ("escalat", "human review", "human oversight", "approval", "judgement boundary", "judgment boundary")


async def _parse_estate(inputs: dict, ctx: Context) -> dict:
    """Inventory registered cards, lifecycle state, and trace evidence.

    Deliberately deterministic: the estate scan is a read of governance
    artefacts, not a judgement. Reads go through tool-filesystem so the trace
    shows the boundary.
    """
    started = _time.monotonic()
    estate_root = inputs.get("estate_root")
    if not estate_root:
        return error_envelope("estate_root is required")

    fs = ctx.tools.get("tool-filesystem")
    if fs is None:
        return error_envelope("tool-filesystem is not available")

    cards_path = f"{estate_root}/registry/cards.json"
    cards_outputs = await fs({"op": "read_file", "path": cards_path})
    try:
        cards = _json.loads(cards_outputs.get("text") or "{}")
    except _json.JSONDecodeError:
        return error_envelope(f"could not parse {cards_path} as JSON")
    if isinstance(cards, list):
        cards = {c.get("id", f"card-{i}"): c for i, c in enumerate(cards)}
    if not isinstance(cards, dict):
        return error_envelope("cards.json did not contain a card mapping")

    trace_lines, trace_files = await _read_trace_lines(fs, estate_root)

    inventory = []
    for cap_id, card in sorted(cards.items()):
        if not isinstance(card, dict) or card.get("kind") != "au":
            continue
        constraints = [str(c) for c in card.get("constraints") or []]
        oversight = [
            c for c in constraints
            if any(marker in c.lower() for marker in _OVERSIGHT_MARKERS)
        ]
        purpose_l = str(card.get("purpose") or "").lower()
        oversight_in_purpose = any(m in purpose_l for m in _OVERSIGHT_MARKERS)
        lifecycle = card.get("lifecycle") or {}
        evidence_lines = [
            line for line in trace_lines
            if f'"{cap_id}"' in line and '"capability-context"' not in line
        ]
        inventory.append({
            "capability_id": cap_id,
            "kind": "au",
            "agent_id": card.get("agent_id", ""),
            "purpose": str(card.get("purpose") or "").strip(),
            "version": card.get("version", ""),
            "card_fields": {
                "has_purpose": bool(str(card.get("purpose") or "").strip()),
                "has_inputs": bool(card.get("inputs")),
                "has_outputs": bool(card.get("outputs")),
                "has_constraints": bool(constraints),
                "has_version": bool(card.get("version")),
            },
            "lifecycle": {
                "status": lifecycle.get("status", ""),
                "published_by": lifecycle.get("published_by", ""),
                "approved_by": lifecycle.get("approved_by", ""),
                "reviewed_by": lifecycle.get("reviewed_by", ""),
                "replaced_by": lifecycle.get("replaced_by", ""),
                "deprecated_by": lifecycle.get("deprecated_by", ""),
            },
            "evaluation_signals": [str(sig) for sig in card.get("evaluation_signals") or []],
            "declared_tools": [
                item.get("name") if isinstance(item, dict) else str(item)
                for item in card.get("inputs") or []
            ],
            "oversight_declared": bool(oversight) or oversight_in_purpose,
            "oversight_evidence": oversight[:2],
            "trace_evidence": {
                "invocations": len(evidence_lines),
                "trace_files_scanned": trace_files,
            },
        })

    outputs = {
        "inventory": inventory,
        "scanned_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "trace_files_scanned": trace_files,
    }
    return {
        "outputs": outputs,
        "signals": {
            "valid_output_shape": True,
            "cards_read": len(inventory),
            "traces_scanned": trace_files,
            "latency_seconds": round(_time.monotonic() - started, 2),
        },
    }


async def _read_trace_lines(fs, estate_root: str, cap: int = 20) -> tuple[list[str], int]:
    """Read the most recent trace files (by name) and return their lines."""
    traces_dir = f"{estate_root}/traces"
    try:
        listing = await fs({"op": "list_directory", "path": traces_dir})
    except Exception as exc:  # visible, not silent: the scan is evidence
        return [f'__trace_read_error__ {exc!r}'], 0
    entries = listing.get("entries") or []
    names = sorted(
        e.get("name") for e in entries
        if isinstance(e, dict) and str(e.get("name", "")).endswith(".jsonl")
    )[-cap:]
    lines: list[str] = []
    count = 0
    for name in names:
        try:
            read = await fs({"op": "read_file", "path": f"{traces_dir}/{name}"})
        except Exception:
            continue
        text = read.get("text") or ""
        if text:
            lines.extend(text.splitlines())
            count += 1
    return lines, count


if __name__ == "__main__":
    run(handle)
