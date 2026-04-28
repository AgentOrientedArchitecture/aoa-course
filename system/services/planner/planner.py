"""Planner service.

The planner receives intents from the studio, asks the registry for the
capabilities it needs, sequences the agent invocations, and records the trace.
Session 2 starts with one workflow (`cv-fit`). Session 4 reuses the same
parser/evaluator/reporter shape for cut-down knowledge-management workflows:
ingest material into a wiki store, then answer questions from that store.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("planner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://registry:7100").rstrip("/")
TRACES_DIR = Path(os.environ.get("PLANNER_TRACES_DIR", "/data/traces"))
PORT = int(os.environ.get("PLANNER_PORT", "7200"))
INVOKE_TIMEOUT = float(os.environ.get("PLANNER_INVOKE_TIMEOUT", "300"))
PLANNER_STRATEGY = os.environ.get("PLANNER_STRATEGY", "hybrid").strip().lower()
PLANNER_MODEL_TIMEOUT = float(os.environ.get("PLANNER_MODEL_TIMEOUT_SECONDS", "60"))
PLANNER_MODEL_MAX_TOKENS = int(os.environ.get("PLANNER_MODEL_MAX_TOKENS", "2048"))


# ----------------------------------------------------------------------
# Workflow definitions
# ----------------------------------------------------------------------

@dataclass
class TaskSpec:
    """A task produced from intent before discovery binds it to a capability.

    ``input_map`` maps this step's input name to a path in the running context
    (``inputs.cv`` or ``parser-cv.outputs.parsed``). The planner resolves these
    against the bag of step outputs accumulated so far.
    """

    id: str
    purpose: str
    discovery: dict[str, Any]
    input_map: dict[str, str]
    selected_capability: str | None = None


@dataclass
class Workflow:
    name: str
    tasks: list[TaskSpec]


@dataclass
class ResolvedStep:
    task: TaskSpec
    capability: str
    card: dict[str, Any]


@dataclass
class PlanBuildResult:
    tasks: list[TaskSpec]
    source: str
    proposal: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    error: str | None = None


WORKFLOWS: dict[str, Workflow] = {
    "cv-fit": Workflow(
        name="cv-fit",
        tasks=[
            # The parser extracts the CV text via tool-document-text itself; the
            # planner only threads the path through.
            TaskSpec(
                id="parse-cv",
                purpose="Extract structured CV data from a document path.",
                discovery={
                    "kind": "au",
                    "text": "read parse extract structured cv data from document",
                    "required_inputs": [{"name": "cv_path", "type": "string"}],
                    "required_outputs": [{"type": "structured-cv"}],
                },
                input_map={"cv_path": "inputs.cv_path"},
            ),
            # The evaluator extracts the JD text via tool-document-text too; this is
            # how Session 2 shows that tools.yaml is honest about what each
            # agent actually reaches for.
            TaskSpec(
                id="evaluate-cv-fit",
                purpose="Score a structured CV against a job description.",
                discovery={
                    "kind": "au",
                    "text": "score evaluate cv against job description verdict strengths gaps",
                    "required_inputs": [
                        {"name": "cv", "type": "structured-cv"},
                        {"name": "jd_path", "type": "string"},
                    ],
                    "required_outputs": [
                        {"name": "scores"},
                        {"name": "verdict"},
                    ],
                },
                input_map={
                    "cv": "parse-cv.outputs.parsed",
                    "jd_path": "inputs.jd_path",
                },
            ),
            TaskSpec(
                id="write-cv-fit-report",
                purpose="Write a concise markdown CV fit report for a human reader.",
                discovery={
                    "kind": "au",
                    "text": "write report markdown cv fit recommendation highlights concerns",
                    "required_inputs": [
                        {"name": "cv", "type": "structured-cv"},
                        {"name": "evaluation", "type": "object"},
                    ],
                    "required_outputs": [{"name": "report_markdown"}],
                },
                input_map={
                    "cv": "parse-cv.outputs.parsed",
                    "evaluation": "evaluate-cv-fit.outputs",
                },
            ),
        ],
    ),
    "knowledge-ingest": Workflow(
        name="knowledge-ingest",
        tasks=[
            TaskSpec(
                id="parse-note",
                purpose="Extract structured passages and concepts from a source note.",
                discovery={
                    "kind": "au",
                    "text": "read parse note passages concepts structured-note",
                    "required_inputs": [{"name": "note_path", "type": "string"}],
                    "required_outputs": [{"type": "structured-note"}],
                },
                input_map={"note_path": "inputs.note_path"},
            ),
            TaskSpec(
                id="promote-note",
                purpose="Decide which parsed-note material should be promoted into the course wiki.",
                discovery={
                    "kind": "au",
                    "text": "promote parsed note into wiki concepts passages relationships open questions",
                    "required_inputs": [
                        {"name": "parsed_note", "type": "structured-note"},
                        {"name": "source_path", "type": "string"},
                    ],
                    "required_outputs": [
                        {"name": "promotion"},
                    ],
                },
                input_map={
                    "parsed_note": "parse-note.outputs.parsed_note",
                    "source_path": "inputs.note_path",
                },
            ),
            TaskSpec(
                id="write-wiki-ingest",
                purpose="Store promoted material in the wiki and report what changed.",
                discovery={
                    "kind": "au",
                    "text": "write wiki ingest summary store promoted knowledge markdown",
                    "required_inputs": [
                        {"name": "promotion", "type": "object"},
                        {"name": "source_path", "type": "string"},
                    ],
                    "required_outputs": [{"name": "ingest_markdown"}],
                },
                input_map={
                    "promotion": "promote-note.outputs.promotion",
                    "source_path": "inputs.note_path",
                },
            ),
        ],
    ),
    "knowledge-query": Workflow(
        name="knowledge-query",
        tasks=[
            TaskSpec(
                id="parse-query",
                purpose="Parse the user question into a compact wiki retrieval query.",
                discovery={
                    "kind": "au",
                    "text": "parse question retrieval query intent terms focus constraints",
                    "required_inputs": [{"name": "question", "type": "string"}],
                    "required_outputs": [{"name": "query"}],
                },
                input_map={"question": "inputs.question"},
            ),
            TaskSpec(
                id="evaluate-wiki-query",
                purpose="Search wiki passages and rank evidence against the user question.",
                discovery={
                    "kind": "au",
                    "text": "search wiki rank passages evaluate question answer possible gaps rationale",
                    "required_inputs": [
                        {"name": "question", "type": "string"},
                        {"name": "query", "type": "object"},
                    ],
                    "required_outputs": [
                        {"name": "parsed_note"},
                        {"name": "ranked_passages"},
                        {"name": "direct_answer_possible"},
                    ],
                },
                input_map={
                    "question": "inputs.question",
                    "query": "parse-query.outputs.query",
                },
            ),
            TaskSpec(
                id="write-grounded-answer",
                purpose="Write a grounded markdown answer with citations and gaps.",
                discovery={
                    "kind": "au",
                    "text": "write grounded answer markdown citations gaps confidence",
                    "required_inputs": [
                        {"name": "question", "type": "string"},
                        {"name": "parsed_note", "type": "structured-note"},
                        {"name": "evaluation", "type": "object"},
                    ],
                    "required_outputs": [{"name": "answer_markdown"}],
                },
                input_map={
                    "question": "inputs.question",
                    "parsed_note": "evaluate-wiki-query.outputs.parsed_note",
                    "evaluation": "evaluate-wiki-query.outputs",
                },
            ),
        ],
    ),
}


def _select_workflow(intent: dict[str, Any]) -> Workflow:
    """Pick the deterministic task breakdown for the incoming intent."""
    kind = intent.get("kind")
    if kind in WORKFLOWS:
        return WORKFLOWS[kind]
    if kind is None and {"cv_path", "jd_path"} <= set(intent.get("inputs", {})):
        return WORKFLOWS["cv-fit"]
    if kind is None and {"note_path"} <= set(intent.get("inputs", {})):
        return WORKFLOWS["knowledge-ingest"]
    if kind is None and {"question"} <= set(intent.get("inputs", {})):
        return WORKFLOWS["knowledge-query"]
    raise HTTPException(status_code=400, detail=f"no workflow for intent kind={kind!r}")


# ----------------------------------------------------------------------
# In-memory state (subscribers)
# ----------------------------------------------------------------------

class State:
    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def broadcast(self, record: dict[str, Any]) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(record)
            except asyncio.QueueFull:
                self.subscribers.discard(q)


state = State()


# ----------------------------------------------------------------------
# Trace writing
# ----------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _trace_path(trace_id: str) -> Path:
    return TRACES_DIR / f"{trace_id}.jsonl"


async def _record(record: dict[str, Any]) -> None:
    record.setdefault("ts", _now_iso())
    line = json.dumps(record) + "\n"
    path = _trace_path(record["trace_id"])
    # File IO is sync but tiny — a thread keeps the event loop responsive.
    await asyncio.to_thread(_append_line, path, line)
    await state.broadcast(record)


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(line)


def _task_trace(task: TaskSpec) -> dict[str, Any]:
    return {
        "id": task.id,
        "purpose": task.purpose,
        "discovery": task.discovery,
        "input_map": task.input_map,
        "selected_capability": task.selected_capability,
    }


def _candidate_trace(candidate: dict[str, Any]) -> dict[str, Any]:
    card = candidate.get("card", {}) or {}
    return {
        "id": card.get("id"),
        "kind": card.get("kind"),
        "score": candidate.get("score"),
        "reasons": candidate.get("reasons", []),
        "purpose": card.get("purpose"),
        "inputs": card.get("inputs", []),
        "outputs": card.get("outputs", []),
        "agent_card_url": card.get("agent_card_url"),
        "a2a_endpoint": card.get("a2a_endpoint"),
        "endpoint": card.get("endpoint"),
    }


def _compact_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card.get("id"),
        "version": card.get("version"),
        "kind": card.get("kind"),
        "purpose": " ".join(str(card.get("purpose", "")).split()),
        "inputs": card.get("inputs", []),
        "outputs": card.get("outputs", []),
        "constraints": card.get("constraints", [])[:3],
    }


def _workflow_example(workflow: Workflow) -> dict[str, Any]:
    return {
        "workflow": workflow.name,
        "tasks": [
            {
                "id": task.id,
                "purpose": task.purpose,
                "capability": _deterministic_capability_for_task(task),
                "input_map": task.input_map,
            }
            for task in workflow.tasks
        ],
    }


def _deterministic_capability_for_task(task: TaskSpec) -> str:
    matches = {
        "parse-cv": "parser-cv",
        "evaluate-cv-fit": "evaluator-cv",
        "write-cv-fit-report": "reporter-cv-fit",
        "parse-note": "parser-notes",
        "promote-note": "evaluator-promote",
        "write-wiki-ingest": "reporter-ingest-summary",
        "parse-query": "parser-query",
        "evaluate-wiki-query": "evaluator-wiki-query",
        "write-grounded-answer": "reporter-answer",
    }
    return matches.get(task.id, "")


def _parse_json_block(text: str) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("planner model returned an empty response")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("planner model response did not contain a JSON object")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("planner model response must be a JSON object")
    return value


def _build_planner_prompt(
    workflow: Workflow,
    intent: dict[str, Any],
    cards: list[dict[str, Any]],
) -> str:
    intent_summary = {
        "kind": intent.get("kind"),
        "available_inputs": sorted((intent.get("inputs") or {}).keys()),
    }
    examples = [_workflow_example(wf) for wf in WORKFLOWS.values()]
    body = {
        "intent": intent_summary,
        "available_capabilities": [_compact_card(card) for card in cards if card.get("kind") == "au"],
        "few_shot_examples": examples,
        "output_schema": {
            "goal": "short human-readable goal",
            "tasks": [
                {
                    "id": "stable kebab-case task id",
                    "purpose": "what the task accomplishes",
                    "capability": "one id from available_capabilities",
                    "input_map": {
                        "capability_input_name": "inputs.x or previous-task.outputs.y"
                    },
                }
            ],
        },
    }
    return (
        "You are the planner in a small Agent-oriented Architecture demo.\n"
        "Generate a valid task plan for the requested workflow.\n"
        "Use only capability ids from available_capabilities.\n"
        "Use only input references that are available from intent inputs or earlier tasks.\n"
        "Return a single JSON object and no commentary.\n\n"
        f"{json.dumps(body, indent=2)}"
    )


async def _planner_model_complete(prompt: str) -> tuple[str, dict[str, Any]]:
    provider = os.environ.get("PROVIDER", "ollama").strip().lower()
    model = os.environ.get("MODEL", "").strip()
    if not model:
        raise RuntimeError("MODEL env var is not set")
    if provider == "ollama":
        return await _planner_ollama(prompt, model)
    if provider == "openai":
        return await _planner_openai(prompt, model)
    raise RuntimeError(f"planner model provider {provider!r} is not supported")


async def _planner_ollama(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
    host = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
    response_format = os.environ.get("OLLAMA_RESPONSE_FORMAT", "json").strip()
    think = os.environ.get("OLLAMA_THINK", "false").strip().lower()
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": PLANNER_MODEL_MAX_TOKENS,
        },
    }
    if response_format:
        payload["format"] = response_format
    if think in {"true", "false"}:
        payload["think"] = think == "true"
    async with httpx.AsyncClient(timeout=PLANNER_MODEL_TIMEOUT) as client:
        r = await client.post(f"{host}/api/generate", json=payload)
        r.raise_for_status()
        raw = r.json()
    text = raw.get("response") or ""
    if not text.strip() and isinstance(raw.get("thinking"), str):
        text = raw["thinking"]
    return text, raw


async def _planner_openai(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
    base_url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only a valid JSON object."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": PLANNER_MODEL_MAX_TOKENS,
    }
    response_format = os.environ.get("OPENAI_RESPONSE_FORMAT", "json_object").strip()
    if response_format:
        payload["response_format"] = {"type": response_format}
    reasoning_effort = os.environ.get("OPENAI_REASONING_EFFORT", "low").strip()
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=PLANNER_MODEL_TIMEOUT) as client:
        r = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        raw = r.json()
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return message.get("content") or message.get("reasoning") or "", raw


def _fallback_plan(workflow: Workflow, reason: str | None = None) -> PlanBuildResult:
    return PlanBuildResult(tasks=workflow.tasks, source="deterministic", error=reason)


def _validate_plan(
    proposal: dict[str, Any],
    intent_inputs: dict[str, Any],
    cards_by_id: dict[str, dict[str, Any]],
) -> tuple[list[TaskSpec], dict[str, Any]]:
    tasks = proposal.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("plan.tasks must be a non-empty array")
    prior_outputs: dict[str, set[str]] = {}
    seen_task_ids: set[str] = set()
    planned_tasks: list[TaskSpec] = []
    checks: list[dict[str, Any]] = []

    for index, raw_task in enumerate(tasks):
        if not isinstance(raw_task, dict):
            raise ValueError(f"task {index} must be an object")
        task_id = str(raw_task.get("id") or "").strip()
        capability_id = str(raw_task.get("capability") or "").strip()
        purpose = str(raw_task.get("purpose") or "").strip()
        input_map = raw_task.get("input_map") or {}
        if not task_id:
            raise ValueError(f"task {index} is missing id")
        if task_id in seen_task_ids:
            raise ValueError(f"duplicate task id: {task_id}")
        if capability_id not in cards_by_id:
            raise ValueError(f"unknown capability: {capability_id}")
        if not isinstance(input_map, dict):
            raise ValueError(f"task {task_id} input_map must be an object")

        card = cards_by_id[capability_id]
        if card.get("kind") != "au":
            raise ValueError(f"task {task_id} selected non-AU capability {capability_id}")
        required_inputs = [
            field for field in card.get("inputs", []) or [] if field.get("required", True)
        ]
        for field in required_inputs:
            name = field.get("name")
            if name not in input_map:
                raise ValueError(f"task {task_id} missing input mapping for {name}")
            _validate_reference(str(input_map[name]), intent_inputs, prior_outputs)

        output_names = {field.get("name") for field in card.get("outputs", []) or [] if field.get("name")}
        prior_outputs[task_id] = output_names
        prior_outputs[capability_id] = output_names
        seen_task_ids.add(task_id)
        planned_tasks.append(TaskSpec(
            id=task_id,
            purpose=purpose or f"Run {capability_id}",
            discovery={
                "kind": "au",
                "text": purpose or capability_id,
                "required_inputs": card.get("inputs", []),
                "required_outputs": card.get("outputs", []),
            },
            input_map={str(k): str(v) for k, v in input_map.items()},
            selected_capability=capability_id,
        ))
        checks.append({
            "task": task_id,
            "capability": capability_id,
            "required_inputs": [field.get("name") for field in required_inputs],
            "outputs": sorted(output_names),
        })

    final_outputs = prior_outputs.get(planned_tasks[-1].id, set())
    final_markdown_outputs = {"report_markdown", "answer_markdown", "ingest_markdown"}
    if not final_markdown_outputs.intersection(final_outputs):
        raise ValueError("final task must produce report_markdown, answer_markdown, or ingest_markdown")
    return planned_tasks, {"valid": True, "checks": checks}


def _validate_reference(
    path: str,
    intent_inputs: dict[str, Any],
    prior_outputs: dict[str, set[str]],
) -> None:
    parts = path.split(".")
    if len(parts) < 2:
        raise ValueError(f"input reference {path!r} is too short")
    if parts[0] == "inputs":
        if parts[1] not in intent_inputs:
            raise ValueError(f"input reference {path!r} points to missing intent input")
        return
    if parts[0] not in prior_outputs:
        raise ValueError(f"input reference {path!r} points to a future or unknown task")
    if parts[1] != "outputs":
        raise ValueError(f"input reference {path!r} must use .outputs")
    if len(parts) >= 3 and parts[2] not in prior_outputs[parts[0]]:
        raise ValueError(f"input reference {path!r} points to an unknown output")


async def _build_plan(
    workflow: Workflow,
    intent: dict[str, Any],
    cards: list[dict[str, Any]],
) -> PlanBuildResult:
    if PLANNER_STRATEGY == "deterministic":
        return _fallback_plan(workflow)
    try:
        prompt = _build_planner_prompt(workflow, intent, cards)
        text, raw = await _planner_model_complete(prompt)
        proposal = _parse_json_block(text)
        proposal["_model"] = {
            "provider": os.environ.get("PROVIDER", "ollama"),
            "model": os.environ.get("MODEL", ""),
            "eval_count": raw.get("eval_count"),
            "prompt_eval_count": raw.get("prompt_eval_count"),
        }
        cards_by_id = {card["id"]: card for card in cards if card.get("id")}
        tasks, validation = _validate_plan(proposal, intent.get("inputs", {}) or {}, cards_by_id)
        return PlanBuildResult(tasks=tasks, source="llm", proposal=proposal, validation=validation)
    except Exception as e:  # noqa: BLE001
        if PLANNER_STRATEGY == "llm":
            raise
        logger.warning("planner model failed; falling back to deterministic plan: %r", e)
        return _fallback_plan(workflow, reason=str(e))


# ----------------------------------------------------------------------
# Registry + agent IO
# ----------------------------------------------------------------------

async def _registry_list(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    r = await client.get(f"{REGISTRY_URL}/list")
    r.raise_for_status()
    return r.json().get("capabilities", [])


async def _registry_discover(client: httpx.AsyncClient, query: dict[str, Any]) -> dict[str, Any]:
    r = await client.post(f"{REGISTRY_URL}/discover", json=query)
    r.raise_for_status()
    return r.json()


async def _invoke(
    client: httpx.AsyncClient, card: dict[str, Any], trace_id: str, inputs: dict[str, Any]
) -> dict[str, Any]:
    if card.get("a2a_endpoint"):
        return await _invoke_a2a(client, card, trace_id, inputs)
    return await _invoke_http(client, card, trace_id, inputs)


async def _invoke_http(
    client: httpx.AsyncClient, card: dict[str, Any], trace_id: str, inputs: dict[str, Any]
) -> dict[str, Any]:
    endpoint = card["endpoint"]
    payload = {"trace_id": trace_id, "inputs": inputs}
    r = await client.post(
        endpoint, params={"capability": card["id"]}, json=payload, timeout=INVOKE_TIMEOUT
    )
    r.raise_for_status()
    return r.json()


async def _invoke_a2a(
    client: httpx.AsyncClient, card: dict[str, Any], trace_id: str, inputs: dict[str, Any]
) -> dict[str, Any]:
    capability_id = card["id"]
    payload = {
        "jsonrpc": "2.0",
        "id": f"{trace_id}-{capability_id}",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": uuid.uuid4().hex,
                "role": "user",
                "parts": [
                    {
                        "kind": "data",
                        "data": {
                            "inputs": inputs,
                        },
                    }
                ],
                "metadata": {
                    "trace_id": trace_id,
                    "aoa_capability": capability_id,
                },
            },
            "metadata": {
                "trace_id": trace_id,
                "aoa_capability": capability_id,
            },
        },
    }
    r = await client.post(card["a2a_endpoint"], json=payload, timeout=INVOKE_TIMEOUT)
    r.raise_for_status()
    response = r.json()
    if response.get("error"):
        raise RuntimeError(response["error"])
    result = response.get("result") or {}
    outputs: dict[str, Any] = {}
    signals: dict[str, Any] = {}
    for part in result.get("parts") or []:
        if part.get("kind") != "data":
            continue
        data = part.get("data") or {}
        if not isinstance(data, dict):
            continue
        outputs = data.get("outputs", {})
        signals = data.get("signals", {})
        break
    return {"trace_id": trace_id, "outputs": outputs, "signals": signals}


# ----------------------------------------------------------------------
# Input resolution
# ----------------------------------------------------------------------

def _resolve_path(path: str, intent_inputs: dict[str, Any], step_outputs: dict[str, dict[str, Any]]) -> Any:
    """Resolve ``inputs.x.y`` or ``<capability>.outputs.x.y`` against context."""
    parts = path.split(".")
    if not parts:
        raise ValueError(f"empty input path")
    head, *rest = parts
    if head == "inputs":
        cur: Any = intent_inputs
    elif head in step_outputs:
        cur = step_outputs[head]
    else:
        raise ValueError(f"unknown reference {head!r} in input path {path!r}")
    for part in rest:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise ValueError(f"cannot resolve {path!r}: missing {part!r}")
    return cur


# ----------------------------------------------------------------------
# Workflow execution
# ----------------------------------------------------------------------

async def _run_workflow(
    workflow: Workflow, intent: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    trace_id = uuid.uuid4().hex[:12]
    intent_inputs: dict[str, Any] = intent.get("inputs", {})
    step_outputs: dict[str, dict[str, Any]] = {}

    await _record({
        "trace_id": trace_id,
        "step": "start",
        "workflow": workflow.name,
        "intent": intent,
    })

    resolved_steps: list[ResolvedStep] = []
    async with httpx.AsyncClient() as client:
        capability_cards = await _registry_list(client)
        au_cards = [card for card in capability_cards if card.get("kind") == "au"]
        await _record({
            "trace_id": trace_id,
            "step": "capability-context",
            "workflow": workflow.name,
            "capabilities": [_compact_card(card) for card in au_cards],
        })

        plan_result = await _build_plan(workflow, intent, capability_cards)
        await _record({
            "trace_id": trace_id,
            "step": "breakdown",
            "workflow": workflow.name,
            "source": plan_result.source,
            "tasks": [_task_trace(task) for task in plan_result.tasks],
        })
        await _record({
            "trace_id": trace_id,
            "step": "plan-proposal",
            "workflow": workflow.name,
            "source": plan_result.source,
            "proposal": plan_result.proposal,
            "validation": plan_result.validation,
            "fallback_reason": plan_result.error,
        })

        cards_by_id = {card["id"]: card for card in capability_cards if card.get("id")}
        for task in plan_result.tasks:
            if task.selected_capability:
                card = cards_by_id.get(task.selected_capability)
                if card is None:
                    raise HTTPException(
                        status_code=502,
                        detail=f"planner selected missing capability {task.selected_capability}",
                    )
                candidates = [{
                    "score": None,
                    "reasons": ["selected_by_planner_model"],
                    "card": card,
                }]
                query = {
                    "strategy": "small-registry-llm-context",
                    "considered_capabilities": [card.get("id") for card in au_cards],
                    "task": _task_trace(task),
                }
            else:
                discovery = await _registry_discover(client, task.discovery)
                candidates = discovery.get("candidates", [])
                query = task.discovery
            await _record({
                "trace_id": trace_id,
                "step": "discover",
                "task": task.id,
                "query": query,
                "candidates": [_candidate_trace(candidate) for candidate in candidates],
            })
            if not candidates:
                message = f"no capability discovered for task {task.id}"
                await _record({
                    "trace_id": trace_id,
                    "step": "error",
                    "task": task.id,
                    "error": message,
                })
                raise HTTPException(status_code=502, detail=message)

            selected = candidates[0]
            card = selected["card"]
            resolved_steps.append(ResolvedStep(task=task, capability=card["id"], card=card))
            await _record({
                "trace_id": trace_id,
                "step": "select",
                "task": task.id,
                "capability": card["id"],
                "score": selected.get("score"),
                "reasons": selected.get("reasons", []),
                "card": card,
            })

        await _record({
            "trace_id": trace_id,
            "step": "plan",
            "workflow": workflow.name,
            "plan": [
                {
                    "task": step.task.id,
                    "purpose": step.task.purpose,
                    "capability": step.capability,
                    "input_map": step.task.input_map,
                }
                for step in resolved_steps
            ],
        })

        for step in resolved_steps:
            card = step.card
            await _record({
                "trace_id": trace_id,
                "step": "lookup",
                "task": step.task.id,
                "capability": step.capability,
                "card": card,
            })

            try:
                inputs = {
                    name: _resolve_path(path, intent_inputs, step_outputs)
                    for name, path in step.task.input_map.items()
                }
            except ValueError as e:
                await _record({
                    "trace_id": trace_id,
                    "step": "error",
                    "task": step.task.id,
                    "capability": step.capability,
                    "error": str(e),
                })
                raise HTTPException(status_code=500, detail=str(e))

            await _record({
                "trace_id": trace_id,
                "step": "invoke",
                "task": step.task.id,
                "capability": step.capability,
                "inputs": inputs,
            })
            t0 = time.perf_counter()
            try:
                response = await _invoke(client, card, trace_id, inputs)
            except httpx.HTTPError as e:
                await _record({
                    "trace_id": trace_id,
                    "step": "error",
                    "task": step.task.id,
                    "capability": step.capability,
                    "error": repr(e),
                })
                raise HTTPException(status_code=502, detail=f"{step.capability}: {e!r}")
            elapsed = time.perf_counter() - t0
            await _record({
                "trace_id": trace_id,
                "step": "response",
                "task": step.task.id,
                "capability": step.capability,
                "outputs": response.get("outputs", {}),
                "signals": response.get("signals", {}),
                "latency_seconds": elapsed,
            })
            if _response_failed(response):
                final_outputs = {
                    "error": response.get("outputs", {}).get("error", "capability failed"),
                    "failed_capability": step.capability,
                    "failed_task": step.task.id,
                    "signals": response.get("signals", {}),
                }
                await _record({
                    "trace_id": trace_id,
                    "step": "finish",
                    "workflow": workflow.name,
                    "outputs": final_outputs,
                })
                return trace_id, final_outputs
            step_result = {
                "outputs": response.get("outputs", {}),
                "signals": response.get("signals", {}),
            }
            step_outputs[step.task.id] = step_result
            step_outputs[step.capability] = step_result

    final = step_outputs[resolved_steps[-1].task.id]
    await _record({
        "trace_id": trace_id,
        "step": "finish",
        "workflow": workflow.name,
        "outputs": final.get("outputs", {}),
    })
    return trace_id, final.get("outputs", {})


def _response_failed(response: dict[str, Any]) -> bool:
    outputs = response.get("outputs", {})
    signals = response.get("signals", {})
    has_output_error = isinstance(outputs, dict) and bool(outputs.get("error"))
    has_exception_signal = isinstance(signals, dict) and bool(signals.get("exception"))
    return has_output_error or has_exception_signal


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------

app = FastAPI()


@app.on_event("startup")
async def _startup() -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("planner ready: registry=%s traces=%s", REGISTRY_URL, TRACES_DIR)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True, "workflows": sorted(WORKFLOWS), "planner_strategy": PLANNER_STRATEGY}


@app.post("/intent")
async def intent(request: Request) -> JSONResponse:
    body = await request.json()
    workflow = _select_workflow(body)
    trace_id, outputs = await _run_workflow(workflow, body)
    return JSONResponse({"trace_id": trace_id, "workflow": workflow.name, "outputs": outputs})


@app.get("/traces")
async def list_traces() -> JSONResponse:
    if not TRACES_DIR.exists():
        return JSONResponse({"traces": []})
    ids = sorted(
        (p.stem for p in TRACES_DIR.glob("*.jsonl")),
        key=lambda s: (TRACES_DIR / f"{s}.jsonl").stat().st_mtime,
        reverse=True,
    )
    return JSONResponse({"traces": ids[:100]})


@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> JSONResponse:
    path = _trace_path(trace_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"unknown trace: {trace_id}")
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return JSONResponse({"trace_id": trace_id, "records": records})


@app.get("/events")
async def events() -> StreamingResponse:
    """SSE stream of trace records. The studio subscribes to this."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1024)
    state.subscribers.add(queue)

    async def _gen() -> AsyncIterator[bytes]:
        try:
            yield b": connected\n\n"
            while True:
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(record)}\n\n".encode("utf-8")
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"
        finally:
            state.subscribers.discard(queue)

    return StreamingResponse(_gen(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
