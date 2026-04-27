"""Capability registry service.

A flat dictionary of capability cards keyed by ``id``, persisted to a single
JSON file. Agents and tools register on boot; the planner reads the registry
when it needs to dispatch; the studio subscribes to ``/stream`` for live
updates of its registry pane.

The state file (``cards.json``) is also watched so that hand-edits — useful in
class — are picked up and broadcast.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("registry")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


DATA_DIR = Path(os.environ.get("REGISTRY_DATA_DIR", "/data"))
CARDS_PATH = DATA_DIR / "cards.json"
PORT = int(os.environ.get("REGISTRY_PORT", "7100"))


# ----------------------------------------------------------------------
# In-memory state
# ----------------------------------------------------------------------

class State:
    """Holds the live set of capability cards plus subscribers."""

    def __init__(self) -> None:
        self.cards: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def broadcast(self, event: str, card: dict[str, Any]) -> None:
        message = {"event": event, "card": card}
        for q in list(self.subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                # Drop slow subscribers rather than block the registry.
                self.subscribers.discard(q)

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self.cards.values())


state = State()


# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------

def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CARDS_PATH.exists():
        CARDS_PATH.write_text("{}")


def _read_cards_file() -> dict[str, dict[str, Any]]:
    if not CARDS_PATH.exists():
        return {}
    try:
        text = CARDS_PATH.read_text()
        if not text.strip():
            return {}
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.exception("cards.json is not valid JSON, starting empty")
        return {}
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    if isinstance(data, list):
        # Allow a list-of-cards layout for hand-edited files.
        return {c["id"]: c for c in data if isinstance(c, dict) and "id" in c}
    return {}


def _write_cards_file(cards: dict[str, dict[str, Any]]) -> None:
    tmp = CARDS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cards, indent=2, sort_keys=True))
    tmp.replace(CARDS_PATH)


# ----------------------------------------------------------------------
# File watcher
# ----------------------------------------------------------------------

async def _watch_cards_file() -> None:
    """Re-read cards.json when it changes on disk and broadcast diffs."""
    from watchfiles import awatch

    try:
        async for _changes in awatch(str(CARDS_PATH)):
            on_disk = _read_cards_file()
            async with state.lock:
                old_ids = set(state.cards)
                new_ids = set(on_disk)
                added = new_ids - old_ids
                removed = old_ids - new_ids
                changed = {
                    cid for cid in old_ids & new_ids if state.cards[cid] != on_disk[cid]
                }
                state.cards = on_disk

            for cid in added:
                await state.broadcast("registered", on_disk[cid])
            for cid in changed:
                await state.broadcast("updated", on_disk[cid])
            for cid in removed:
                await state.broadcast("deregistered", {"id": cid})
            if added or changed or removed:
                logger.info(
                    "cards.json reload: +%d ~%d -%d", len(added), len(changed), len(removed)
                )
    except Exception:  # noqa: BLE001
        logger.exception("cards.json watcher stopped")


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------

app = FastAPI()


def _validate_card(card: dict[str, Any]) -> None:
    cid = card.get("id")
    if not cid or not isinstance(cid, str):
        raise HTTPException(status_code=400, detail="card.id is required (string)")
    if "endpoint" not in card:
        raise HTTPException(status_code=400, detail="card.endpoint is required")


async def _store(card: dict[str, Any], event: str) -> None:
    async with state.lock:
        state.cards[card["id"]] = card
        _write_cards_file(state.cards)
    await state.broadcast(event, card)


@app.on_event("startup")
async def _startup() -> None:
    _ensure_data_dir()
    state.cards = _read_cards_file()
    logger.info("loaded %d cards from %s", len(state.cards), CARDS_PATH)
    asyncio.create_task(_watch_cards_file())


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True, "count": len(state.cards)}


@app.post("/register")
async def register(request: Request) -> JSONResponse:
    card = await request.json()
    _validate_card(card)
    await _store(card, "registered")
    logger.info("registered %s", card["id"])
    return JSONResponse({"ok": True})


@app.post("/update")
async def update(request: Request) -> JSONResponse:
    card = await request.json()
    _validate_card(card)
    await _store(card, "updated")
    logger.info("updated %s", card["id"])
    return JSONResponse({"ok": True})


@app.post("/deregister")
async def deregister(request: Request) -> JSONResponse:
    body = await request.json()
    cid = body.get("id")
    if not cid:
        raise HTTPException(status_code=400, detail="id is required")
    async with state.lock:
        existed = state.cards.pop(cid, None)
        if existed is not None:
            _write_cards_file(state.cards)
    if existed is not None:
        await state.broadcast("deregistered", {"id": cid})
        logger.info("deregistered %s", cid)
    return JSONResponse({"ok": True})


@app.get("/find")
async def find(id: str) -> JSONResponse:
    card = state.cards.get(id)
    if card is None:
        raise HTTPException(status_code=404, detail=f"unknown capability: {id}")
    return JSONResponse(card)


@app.get("/list")
async def list_capabilities() -> JSONResponse:
    return JSONResponse({"capabilities": state.snapshot()})


@app.get("/stream")
async def stream() -> StreamingResponse:
    """SSE stream of registry events. The studio subscribes to this."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
    state.subscribers.add(queue)

    async def _gen() -> AsyncIterator[bytes]:
        try:
            # Replay current state so subscribers reach a consistent view.
            yield _sse({"event": "snapshot", "cards": state.snapshot()})
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _sse(msg)
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"
        finally:
            state.subscribers.discard(queue)

    return StreamingResponse(_gen(), media_type="text/event-stream")


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
