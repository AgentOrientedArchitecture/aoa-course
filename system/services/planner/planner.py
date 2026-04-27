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
class Step:
    """A single capability invocation in a workflow.

    ``input_map`` maps this step's input name to a path in the running context
    (``inputs.cv`` or ``parser-cv.outputs.parsed``). The planner resolves these
    against the bag of step outputs accumulated so far.
    """

    capability: str
    input_map: dict[str, str]


@dataclass
class Workflow:
    name: str
    steps: list[Step]


WORKFLOWS: dict[str, Workflow] = {
    "cv-fit": Workflow(
        name="cv-fit",
        steps=[
            # The parser extracts the CV text via tool-document-text itself; the
            # planner only threads the path through.
            Step(
                capability="parser-cv",
                input_map={"cv_path": "inputs.cv_path"},
            ),
            # The evaluator extracts the JD text via tool-document-text too; this is
            # how Session 2 shows that tools.yaml is honest about what each
            # agent actually reaches for.
            Step(
                capability="evaluator-cv",
                input_map={
                    "cv": "parser-cv.outputs.parsed",
                    "jd_path": "inputs.jd_path",
                },
            ),
            Step(
                capability="reporter-cv-fit",
                input_map={
                    "cv": "parser-cv.outputs.parsed",
                    "evaluation": "evaluator-cv.outputs",
                },
            ),
        ],
    ),
    "knowledge-query": Workflow(
        name="knowledge-query",
        steps=[
            Step(
                capability="parser-notes",
                input_map={"note_path": "inputs.note_path"},
            ),
            Step(
                capability="evaluator-query",
                input_map={
                    "question": "inputs.question",
                    "parsed_note": "parser-notes.outputs.parsed_note",
                },
            ),
            Step(
                capability="reporter-answer",
                input_map={
                    "question": "inputs.question",
                    "parsed_note": "parser-notes.outputs.parsed_note",
                    "evaluation": "evaluator-query.outputs",
                },
            ),
        ],
    ),
}


def _select_workflow(intent: dict[str, Any]) -> Workflow:
    """Pick a workflow for the incoming intent.

    Today this is a small mapping. The architectural point — that the planner
    consults the registry for each step — does not depend on this mapping
    being clever, and Session 4 keeps it just as small.
    """
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


# ----------------------------------------------------------------------
# Registry + agent IO
# ----------------------------------------------------------------------

async def _registry_find(client: httpx.AsyncClient, capability_id: str) -> dict[str, Any]:
    r = await client.get(f"{REGISTRY_URL}/find", params={"id": capability_id})
    if r.status_code == 404:
        raise HTTPException(status_code=502, detail=f"registry has no capability {capability_id}")
    r.raise_for_status()
    return r.json()


async def _invoke(
    client: httpx.AsyncClient, card: dict[str, Any], trace_id: str, inputs: dict[str, Any]
) -> dict[str, Any]:
    endpoint = card["endpoint"]
    payload = {"trace_id": trace_id, "inputs": inputs}
    r = await client.post(
        endpoint, params={"capability": card["id"]}, json=payload, timeout=INVOKE_TIMEOUT
    )
    r.raise_for_status()
    return r.json()


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

    async with httpx.AsyncClient() as client:
        for step in workflow.steps:
            card = await _registry_find(client, step.capability)
            await _record({
                "trace_id": trace_id,
                "step": "lookup",
                "capability": step.capability,
                "card": card,
            })

            try:
                inputs = {
                    name: _resolve_path(path, intent_inputs, step_outputs)
                    for name, path in step.input_map.items()
                }
            except ValueError as e:
                await _record({
                    "trace_id": trace_id,
                    "step": "error",
                    "capability": step.capability,
                    "error": str(e),
                })
                raise HTTPException(status_code=500, detail=str(e))

            await _record({
                "trace_id": trace_id,
                "step": "invoke",
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
                    "capability": step.capability,
                    "error": repr(e),
                })
                raise HTTPException(status_code=502, detail=f"{step.capability}: {e!r}")
            elapsed = time.perf_counter() - t0
            await _record({
                "trace_id": trace_id,
                "step": "response",
                "capability": step.capability,
                "outputs": response.get("outputs", {}),
                "signals": response.get("signals", {}),
                "latency_seconds": elapsed,
            })
            if _response_failed(response):
                final_outputs = {
                    "error": response.get("outputs", {}).get("error", "capability failed"),
                    "failed_capability": step.capability,
                    "signals": response.get("signals", {}),
                }
                await _record({
                    "trace_id": trace_id,
                    "step": "finish",
                    "workflow": workflow.name,
                    "outputs": final_outputs,
                })
                return trace_id, final_outputs
            step_outputs[step.capability] = {
                "outputs": response.get("outputs", {}),
                "signals": response.get("signals", {}),
            }

    final = step_outputs[workflow.steps[-1].capability]
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
