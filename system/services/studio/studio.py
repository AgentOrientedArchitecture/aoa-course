"""Studio service.

Backend for the browser surface at http://localhost:8080. The studio is a thin
proxy: it subscribes to the registry's and planner's SSE streams, merges them
into one stream the browser reads from, forwards intents to the planner, and
serves the static frontend.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("studio")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://registry:7100").rstrip("/")
PLANNER_URL = os.environ.get("PLANNER_URL", "http://planner:7200").rstrip("/")
PORT = int(os.environ.get("STUDIO_PORT", "8080"))

# The inbox is a shared volume the studio writes to and the filesystem tool
# reads from. Both containers see it at the same path so the agents can be
# handed cv_path / jd_path strings that resolve identically in either place.
INBOX_DIR = Path(os.environ.get("INBOX_DIR", "/data/inbox"))

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_name(name: str) -> str:
    name = name.strip().lstrip(".") or "file"
    return _SAFE_NAME_RE.sub("-", name)[:80] or "file"


def _write_inbox(content: str, suggested_name: str) -> Path:
    """Persist an intent payload to the shared inbox and return its path."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = _sanitize_name(suggested_name)
    path = INBOX_DIR / f"{stamp}-{safe}"
    counter = 1
    while path.exists():
        path = INBOX_DIR / f"{stamp}-{counter}-{safe}"
        counter += 1
    path.write_text(content)
    return path


# ----------------------------------------------------------------------
# Upstream SSE fan-in
# ----------------------------------------------------------------------

class Hub:
    """Holds browser subscribers and re-emits upstream events into them."""

    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def broadcast(self, source: str, payload: dict[str, Any]) -> None:
        message = {"source": source, "payload": payload}
        for q in list(self.subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                self.subscribers.discard(q)


hub = Hub()


async def _follow_upstream(url: str, source: str) -> None:
    """Subscribe to an upstream SSE feed and fan its events into the hub.

    Reconnects on disconnect — the registry or planner may come up later.
    """
    backoff = 1.0
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    backoff = 1.0
                    logger.info("connected to %s", url)
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        try:
                            payload = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        await hub.broadcast(source, payload)
        except Exception as e:  # noqa: BLE001
            logger.warning("upstream %s disconnected: %r (retry in %.1fs)", url, e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 15.0)


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
async def _startup() -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(_follow_upstream(f"{REGISTRY_URL}/stream", "registry"))
    asyncio.create_task(_follow_upstream(f"{PLANNER_URL}/events", "planner"))
    logger.info(
        "studio up on :%d (registry=%s planner=%s inbox=%s)",
        PORT, REGISTRY_URL, PLANNER_URL, INBOX_DIR,
    )


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "registry_url": REGISTRY_URL, "planner_url": PLANNER_URL},
    )


@app.get("/api/capabilities")
async def list_capabilities() -> JSONResponse:
    """Initial registry snapshot for first paint."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{REGISTRY_URL}/list")
            r.raise_for_status()
            return JSONResponse(r.json())
        except httpx.HTTPError:
            return JSONResponse({"capabilities": []})


@app.get("/api/capabilities/{capability_id}")
async def get_capability(capability_id: str) -> JSONResponse:
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{REGISTRY_URL}/find", params={"id": capability_id})
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
        r.raise_for_status()
        return JSONResponse(r.json())


@app.post("/api/intent")
async def submit_intent(request: Request) -> JSONResponse:
    """Persist browser payloads to the inbox and submit paths to the planner.

    The browser sends raw text (typed or read from a dropped file). The studio
    writes bytes to ``inbox/`` so the filesystem tool can later read them.
    Agents only ever see paths — never bytes — from the studio.
    """
    body = await request.json()
    kind = body.get("kind", "cv-fit")
    inputs = body.get("inputs", {}) or {}

    if kind == "knowledge-query":
        return await _submit_knowledge_query(inputs)

    if kind != "cv-fit":
        return JSONResponse({"error": f"unknown intent kind: {kind}"}, status_code=400)

    return await _submit_cv_fit(inputs)


async def _submit_cv_fit(inputs: dict[str, Any]) -> JSONResponse:
    cv_text = inputs.get("cv_text") or ""
    jd_text = inputs.get("jd_text") or ""
    cv_name = inputs.get("cv_name") or "cv.txt"
    jd_name = inputs.get("jd_name") or "jd.txt"
    if not cv_text.strip() or not jd_text.strip():
        return JSONResponse(
            {"error": "both cv_text and jd_text are required"}, status_code=400
        )

    cv_path = _write_inbox(cv_text, cv_name)
    jd_path = _write_inbox(jd_text, jd_name)

    planner_body = {
        "kind": "cv-fit",
        "inputs": {"cv_path": str(cv_path), "jd_path": str(jd_path)},
    }
    result = await _post_planner_intent(planner_body)
    if isinstance(result, JSONResponse):
        return result
    result["cv_path"] = str(cv_path)
    result["jd_path"] = str(jd_path)
    return JSONResponse(result)


async def _submit_knowledge_query(inputs: dict[str, Any]) -> JSONResponse:
    note_text = inputs.get("note_text") or ""
    question = inputs.get("question") or ""
    note_name = inputs.get("note_name") or "source-note.txt"
    if not note_text.strip() or not question.strip():
        return JSONResponse(
            {"error": "both note_text and question are required"}, status_code=400
        )

    note_path = _write_inbox(note_text, note_name)
    planner_body = {
        "kind": "knowledge-query",
        "inputs": {"note_path": str(note_path), "question": question},
    }
    result = await _post_planner_intent(planner_body)
    if isinstance(result, JSONResponse):
        return result
    result["note_path"] = str(note_path)
    return JSONResponse(result)


async def _post_planner_intent(planner_body: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            r = await client.post(f"{PLANNER_URL}/intent", json=planner_body)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                {"error": e.response.text}, status_code=e.response.status_code
            )
        except httpx.HTTPError as e:
            return JSONResponse({"error": repr(e)}, status_code=502)


@app.get("/events")
async def events() -> StreamingResponse:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1024)
    hub.subscribers.add(queue)

    async def _gen() -> AsyncIterator[bytes]:
        try:
            yield b": connected\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(msg)}\n\n".encode("utf-8")
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"
        finally:
            hub.subscribers.discard(queue)

    return StreamingResponse(_gen(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
