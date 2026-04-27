"""Planner service.

The planner receives intents from the studio, asks the registry for the
capabilities it needs, sequences the agent invocations, and records the trace.
Session 2 starts with one workflow (`cv-fit`). Session 4 reuses the same
parser/evaluator/reporter shape for a cut-down knowledge-management workflow
(`knowledge-query`).
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


@dataclass
class Workflow:
    name: str
    tasks: list[TaskSpec]


@dataclass
class ResolvedStep:
    task: TaskSpec
    capability: str
    card: dict[str, Any]


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
    "knowledge-query": Workflow(
        name="knowledge-query",
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
                id="evaluate-question",
                purpose="Rank parsed-note evidence against a user question.",
                discovery={
                    "kind": "au",
                    "text": "rank passages evaluate question answer possible gaps rationale",
                    "required_inputs": [
                        {"name": "question", "type": "string"},
                        {"name": "parsed_note", "type": "structured-note"},
                    ],
                    "required_outputs": [
                        {"name": "ranked_passages"},
                        {"name": "direct_answer_possible"},
                    ],
                },
                input_map={
                    "question": "inputs.question",
                    "parsed_note": "parse-note.outputs.parsed_note",
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
                    "parsed_note": "parse-note.outputs.parsed_note",
                    "evaluation": "evaluate-question.outputs",
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
    if kind is None and {"note_path", "question"} <= set(intent.get("inputs", {})):
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


# ----------------------------------------------------------------------
# Registry + agent IO
# ----------------------------------------------------------------------

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

    await _record({
        "trace_id": trace_id,
        "step": "breakdown",
        "workflow": workflow.name,
        "tasks": [_task_trace(task) for task in workflow.tasks],
    })

    resolved_steps: list[ResolvedStep] = []
    async with httpx.AsyncClient() as client:
        for task in workflow.tasks:
            discovery = await _registry_discover(client, task.discovery)
            candidates = discovery.get("candidates", [])
            await _record({
                "trace_id": trace_id,
                "step": "discover",
                "task": task.id,
                "query": task.discovery,
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
    return {"ok": True, "workflows": sorted(WORKFLOWS)}


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
