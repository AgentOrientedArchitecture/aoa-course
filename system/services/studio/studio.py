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
PLANNER_REQUEST_TIMEOUT = float(os.environ.get("PLANNER_REQUEST_TIMEOUT", "420"))
SUPPORTED_WORKFLOWS = ("cv-fit", "knowledge-ingest", "wiki-graph", "knowledge-query")


def _configured_workflows() -> list[str]:
    raw = os.environ.get("STUDIO_WORKFLOWS", ",".join(SUPPORTED_WORKFLOWS))
    requested = [item.strip() for item in raw.split(",") if item.strip()]
    workflows = [item for item in requested if item in SUPPORTED_WORKFLOWS]
    return workflows or ["cv-fit"]


ENABLED_WORKFLOWS = _configured_workflows()

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


def _inbox_path(suggested_name: str) -> Path:
    """Return a fresh path inside the shared inbox."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = _sanitize_name(suggested_name)
    path = INBOX_DIR / f"{stamp}-{safe}"
    counter = 1
    while path.exists():
        path = INBOX_DIR / f"{stamp}-{counter}-{safe}"
        counter += 1
    return path


def _write_inbox(content: str, suggested_name: str) -> Path:
    """Persist a text intent payload to the shared inbox and return its path."""
    path = _inbox_path(suggested_name)
    path.write_text(content)
    return path


async def _write_upload(upload: Any, suggested_name: str) -> Path:
    """Persist an uploaded file to the shared inbox and return its path."""
    path = _inbox_path(suggested_name)
    content = await upload.read()
    path.write_bytes(content)
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
        {
            "request": request,
            "registry_url": REGISTRY_URL,
            "planner_url": PLANNER_URL,
            "studio_config": {"workflows": ENABLED_WORKFLOWS},
        },
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


@app.get("/api/wiki/graph")
async def get_wiki_graph() -> JSONResponse:
    """Return a typed graph projection of the local wiki store."""
    if "wiki-graph" not in ENABLED_WORKFLOWS:
        raise HTTPException(status_code=404, detail="wiki graph workflow is not enabled")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            card_resp = await client.get(f"{REGISTRY_URL}/find", params={"id": "tool-wiki-store"})
            card_resp.raise_for_status()
            card = card_resp.json()
            invoke_resp = await client.post(
                card["endpoint"],
                params={"capability": "tool-wiki-store"},
                json={"trace_id": "studio-wiki-graph", "inputs": {"op": "graph"}},
            )
            invoke_resp.raise_for_status()
            envelope = invoke_resp.json()
            graph = envelope.get("outputs", {}).get("graph", {"nodes": [], "edges": []})
            return JSONResponse(graph)
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                {
                    "nodes": [],
                    "edges": [],
                    "error": e.response.text,
                },
                status_code=e.response.status_code,
            )
        except httpx.HTTPError as e:
            return JSONResponse({"nodes": [], "edges": [], "error": repr(e)}, status_code=502)
        except KeyError:
            return JSONResponse(
                {"nodes": [], "edges": [], "error": "tool-wiki-store endpoint is not registered"},
                status_code=502,
            )


@app.post("/api/intent")
async def submit_intent(request: Request) -> JSONResponse:
    """Persist browser payloads to the inbox and submit paths to the planner.

    The browser sends pasted text or uploaded files. The studio writes payloads
    to ``inbox/`` so the filesystem tool can later read or extract them. Agents
    only ever see paths — never bytes — from the studio.
    """
    content_type = request.headers.get("content-type", "")
    files: dict[str, Any] = {}
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        kind = str(form.get("kind") or "cv-fit")
        inputs = {
            key: str(form.get(key) or "")
            for key in (
                "cv_text",
                "jd_text",
                "note_text",
                "question",
                "cv_name",
                "jd_name",
                "note_name",
            )
        }
        files = {
            key: form[key]
            for key in ("cv_file", "jd_file", "note_file")
            if key in form and hasattr(form[key], "read")
        }
    else:
        body = await request.json()
        kind = body.get("kind", "cv-fit")
        inputs = body.get("inputs", {}) or {}

    if kind not in ENABLED_WORKFLOWS:
        return JSONResponse({"error": f"workflow is not enabled: {kind}"}, status_code=404)

    if kind == "knowledge-ingest":
        return await _submit_knowledge_ingest(inputs, files)

    if kind == "knowledge-query":
        return await _submit_knowledge_query(inputs, files)

    if kind != "cv-fit":
        return JSONResponse({"error": f"unknown intent kind: {kind}"}, status_code=400)

    return await _submit_cv_fit(inputs, files)


async def _submit_cv_fit(inputs: dict[str, Any], files: dict[str, Any] | None = None) -> JSONResponse:
    files = files or {}
    cv_text = inputs.get("cv_text") or ""
    jd_text = inputs.get("jd_text") or ""
    cv_name = inputs.get("cv_name") or "cv.txt"
    jd_name = inputs.get("jd_name") or "jd.txt"
    has_cv = bool(files.get("cv_file")) or bool(cv_text.strip())
    has_jd = bool(files.get("jd_file")) or bool(jd_text.strip())
    if not has_cv or not has_jd:
        return JSONResponse(
            {"error": "both CV and job description are required"}, status_code=400
        )

    if files.get("cv_file"):
        cv_upload = files["cv_file"]
        cv_path = await _write_upload(cv_upload, getattr(cv_upload, "filename", None) or cv_name)
    else:
        cv_path = _write_inbox(cv_text, cv_name)

    if files.get("jd_file"):
        jd_upload = files["jd_file"]
        jd_path = await _write_upload(jd_upload, getattr(jd_upload, "filename", None) or jd_name)
    else:
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


async def _submit_knowledge_ingest(inputs: dict[str, Any], files: dict[str, Any] | None = None) -> JSONResponse:
    files = files or {}
    note_text = inputs.get("note_text") or ""
    note_name = inputs.get("note_name") or "source-note.txt"
    has_note = bool(files.get("note_file")) or bool(note_text.strip())
    if not has_note:
        return JSONResponse(
            {"error": "source material is required"}, status_code=400
        )

    if files.get("note_file"):
        note_upload = files["note_file"]
        note_path = await _write_upload(
            note_upload, getattr(note_upload, "filename", None) or note_name
        )
    else:
        note_path = _write_inbox(note_text, note_name)
    planner_body = {
        "kind": "knowledge-ingest",
        "inputs": {"note_path": str(note_path)},
    }
    result = await _post_planner_intent(planner_body)
    if isinstance(result, JSONResponse):
        return result
    result["note_path"] = str(note_path)
    return JSONResponse(result)


async def _submit_knowledge_query(inputs: dict[str, Any], files: dict[str, Any] | None = None) -> JSONResponse:
    question = inputs.get("question") or ""
    if not question.strip():
        return JSONResponse({"error": "question is required"}, status_code=400)

    planner_body = {
        "kind": "knowledge-query",
        "inputs": {"question": question},
    }
    result = await _post_planner_intent(planner_body)
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(result)


async def _post_planner_intent(planner_body: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    async with httpx.AsyncClient(timeout=PLANNER_REQUEST_TIMEOUT) as client:
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
