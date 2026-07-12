"""parser agent.

Backs ``parser-cv`` for the ``cv-parser`` runtime, plus ``parser-notes`` and
``parser-query`` for the ``wiki-parser`` runtime.
The shared scaffold in ``_base`` does the discovery, registration, and hot
reload work; this file is just the agent-specific wiring: build a prompt from
the loaded ``instructions.md`` plus the inputs, call the model, parse the JSON
response, return it.
"""
from __future__ import annotations

from typing import Any

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
    plans = _parse_plan_traces(trace_lines)

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
        # Match the acting-capability key precisely: findings and context
        # records may mention other capability ids without invoking them.
        evidence_lines = [
            line for line in trace_lines
            if f'"capability": "{cap_id}"' in line
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
        "plans": plans,
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


def _parse_plan_traces(trace_lines: list[str]) -> list[dict[str, Any]]:
    """Reduce planner JSONL records into per-trace plan evidence."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for line in trace_lines:
        try:
            record = _json.loads(line)
        except (_json.JSONDecodeError, TypeError):
            continue
        if not isinstance(record, dict):
            continue
        trace_id = record.get("trace_id")
        if not isinstance(trace_id, str) or not trace_id.strip():
            continue
        grouped.setdefault(trace_id, []).append(record)

    plans: list[dict[str, Any]] = []
    for trace_id, records in grouped.items():
        if _is_evidence_scan_trace(records):
            continue
        if not any(record.get("step") == "plan" for record in records):
            continue
        plans.append(_summarize_plan_trace(trace_id, records))
    plans.sort(key=lambda item: str(item.get("started_at") or ""), reverse=True)
    return plans


def _is_evidence_scan_trace(records: list[dict[str, Any]]) -> bool:
    evidence_workflows = {"agent-card-check", "flow-audit", "estate-check"}
    for record in records:
        if record.get("workflow") in evidence_workflows:
            return True
        intent = record.get("intent")
        if isinstance(intent, dict) and intent.get("kind") in evidence_workflows:
            return True
    return False


def _summarize_plan_trace(
    trace_id: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    plan: dict[str, Any] = {"trace_id": trace_id}

    workflow = next(
        (
            record.get("workflow")
            for record in records
            if isinstance(record.get("workflow"), str) and record.get("workflow")
        ),
        None,
    )
    start = next((record for record in records if record.get("step") == "start"), None)
    start_intent = start.get("intent") if isinstance(start, dict) else None
    if isinstance(start, dict) and start.get("ts"):
        plan["started_at"] = start["ts"]
    if not workflow and isinstance(start_intent, dict):
        workflow = start_intent.get("kind")
    if workflow:
        plan["workflow"] = workflow

    governance_invoke = next(
        (record for record in records if record.get("step") == "governance-invoke"),
        None,
    )
    governance_inputs = (
        governance_invoke.get("inputs") if isinstance(governance_invoke, dict) else None
    )
    if isinstance(start_intent, dict) and isinstance(start_intent.get("use_context"), dict):
        plan["use_context"] = start_intent["use_context"]
    elif isinstance(governance_inputs, dict) and isinstance(
        governance_inputs.get("use_context"), dict
    ):
        plan["use_context"] = governance_inputs["use_context"]

    plan_event = next(
        (record for record in records if record.get("step") == "plan"),
        None,
    )
    resolved_plan = plan_event.get("plan") if isinstance(plan_event, dict) else None
    if not isinstance(resolved_plan, list) and isinstance(governance_inputs, dict):
        resolved_plan = governance_inputs.get("resolved_plan")
    if isinstance(resolved_plan, list):
        plan["resolved_composition"] = resolved_plan
        capability_ids = []
        for item in resolved_plan:
            capability_id = item.get("capability") if isinstance(item, dict) else None
            if (
                isinstance(capability_id, str)
                and capability_id
                and capability_id not in capability_ids
            ):
                capability_ids.append(capability_id)
        plan["capability_ids"] = capability_ids

    if isinstance(governance_inputs, dict) and isinstance(
        governance_inputs.get("capability_cards"), list
    ):
        plan["capability_cards"] = governance_inputs["capability_cards"]

    plan_digest = next(
        (
            record.get("plan_digest")
            for record in records
            if isinstance(record.get("plan_digest"), str) and record.get("plan_digest")
        ),
        None,
    )
    if not plan_digest and isinstance(governance_inputs, dict):
        value = governance_inputs.get("plan_digest")
        if isinstance(value, str) and value:
            plan_digest = value
    if plan_digest:
        plan["plan_digest"] = plan_digest

    governance_result = next(
        (record for record in records if record.get("step") == "plan-governance"),
        None,
    )
    governance_release = next(
        (record for record in records if record.get("step") == "governance-release"),
        None,
    )
    governance: dict[str, Any] = {}
    if isinstance(governance_invoke, dict):
        _copy_if_present(
            governance,
            governance_invoke,
            (("capability_id", "capability"), ("invoked_at", "ts")),
        )
    if isinstance(governance_result, dict):
        _copy_if_present(
            governance,
            governance_result,
            (
                ("capability_id", "capability"),
                ("decision", "decision"),
                ("report", "evaluation_markdown"),
                ("findings", "findings"),
                ("recorded_at", "ts"),
            ),
        )
    elif isinstance(governance_release, dict):
        _copy_if_present(
            governance,
            governance_release,
            (("decision", "decision"), ("recorded_at", "ts")),
        )
    if governance:
        plan["governance"] = governance

    hold_event = next(
        (record for record in records if record.get("step") == "hold"),
        None,
    )
    if isinstance(hold_event, dict):
        hold: dict[str, Any] = {}
        _copy_if_present(
            hold,
            hold_event,
            (
                ("timestamp", "ts"),
                ("decision", "decision"),
                ("plan_digest", "plan_digest"),
                ("approval_required", "approval_required"),
            ),
        )
        plan["hold"] = hold

    approval_event = next(
        (record for record in records if record.get("step") == "plan-approval"),
        None,
    )
    if isinstance(approval_event, dict):
        approval: dict[str, Any] = {}
        _copy_if_present(
            approval,
            approval_event,
            (
                ("decision", "decision"),
                ("actor_id", "actor_id"),
                ("timestamp", "approved_at"),
                ("plan_digest", "plan_digest"),
                ("reason", "reason"),
            ),
        )
        if "timestamp" not in approval and "ts" in approval_event:
            approval["timestamp"] = approval_event["ts"]
        plan["approval"] = approval

    resume_event = next(
        (record for record in records if record.get("step") == "resume"),
        None,
    )
    if isinstance(resume_event, dict):
        resume: dict[str, Any] = {}
        _copy_if_present(
            resume,
            resume_event,
            (
                ("timestamp", "ts"),
                ("actor_id", "actor_id"),
                ("plan_digest", "plan_digest"),
            ),
        )
        plan["resume"] = resume

    governance_capabilities = {
        record.get("capability")
        for record in records
        if record.get("step") in {"governance-invoke", "plan-governance"}
        and isinstance(record.get("capability"), str)
    }
    first_application_invoke = next(
        (
            record
            for record in records
            if record.get("step") == "invoke"
            and record.get("capability") not in governance_capabilities
        ),
        None,
    )
    if isinstance(first_application_invoke, dict):
        if "ts" in first_application_invoke:
            plan["first_application_invoke_at"] = first_application_invoke["ts"]
        invoke_index = records.index(first_application_invoke)
        plan["governance_preceded_application_invoke"] = (
            isinstance(governance_result, dict)
            and records.index(governance_result) < invoke_index
        )
        if isinstance(approval_event, dict):
            plan["approval_preceded_application_invoke"] = (
                records.index(approval_event) < invoke_index
            )
        if isinstance(resume_event, dict):
            plan["resume_preceded_application_invoke"] = (
                records.index(resume_event) < invoke_index
            )

    finish_event = next(
        (record for record in reversed(records) if record.get("step") == "finish"),
        None,
    )
    if isinstance(finish_event, dict) and "ts" in finish_event:
        plan["finished_at"] = finish_event["ts"]
    plan["execution_status"] = _execution_status(
        records,
        first_application_invoke=first_application_invoke,
        finish_event=finish_event,
        hold_event=hold_event,
        approval_event=approval_event,
        resume_event=resume_event,
        governance_result=governance_result,
    )
    return plan


def _copy_if_present(
    target: dict[str, Any],
    source: dict[str, Any],
    fields: tuple[tuple[str, str], ...],
) -> None:
    for output_name, source_name in fields:
        if source_name in source:
            target[output_name] = source[source_name]


def _execution_status(
    records: list[dict[str, Any]],
    *,
    first_application_invoke: dict[str, Any] | None,
    finish_event: dict[str, Any] | None,
    hold_event: dict[str, Any] | None,
    approval_event: dict[str, Any] | None,
    resume_event: dict[str, Any] | None,
    governance_result: dict[str, Any] | None,
) -> str:
    steps = {record.get("step") for record in records}
    if "rejected" in steps or (
        isinstance(approval_event, dict) and approval_event.get("decision") == "reject"
    ):
        return "rejected"
    if isinstance(finish_event, dict):
        outputs = finish_event.get("outputs")
        if "error" in steps or (isinstance(outputs, dict) and outputs.get("error")):
            return "error"
        return "finished"
    if "error" in steps:
        return "error"
    if isinstance(first_application_invoke, dict):
        return "running"
    if isinstance(resume_event, dict):
        return "resumed"
    if isinstance(approval_event, dict):
        return "approved"
    if isinstance(hold_event, dict):
        return "held"
    if "governance-release" in steps:
        return "released"
    if isinstance(governance_result, dict) and governance_result.get("decision") == "reject":
        return "rejected"
    if "plan" in steps:
        return "resolved"
    if "start" in steps:
        return "started"
    return "observed"


async def _read_trace_lines(fs, estate_root: str) -> tuple[list[str], int]:
    """Read every planner trace file and return its JSONL records."""
    traces_dir = f"{estate_root}/traces"
    try:
        listing = await fs({"op": "list_directory", "path": traces_dir})
    except Exception as exc:  # visible, not silent: the scan is evidence
        return [f'__trace_read_error__ {exc!r}'], 0
    entries = listing.get("entries") or []
    names = sorted(
        str(e.get("name")) for e in entries
        if isinstance(e, dict) and str(e.get("name", "")).endswith(".jsonl")
    )
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
