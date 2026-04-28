"""AOA bridge for the wiki-store MCP server."""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("wiki-store-bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://registry:7100").rstrip("/")
PORT = int(os.environ.get("TOOL_PORT", "7403"))
HOST = os.environ.get("TOOL_HOST", "tool-wiki-store")
CARD_PATH = Path(os.environ.get("CARD_PATH", "/app/capability-card.yaml"))
MCP_SERVER_CMD = [sys.executable, "/app/mcp_server.py"]


class McpClient:
    def __init__(self, command: list[str]) -> None:
        self._command = command
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._ids = itertools.count(1)

    async def start(self) -> None:
        env = os.environ.copy()
        self._proc = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr.buffer,
            env=env,
        )
        await self.request("initialize", {})
        tools = (await self.request("tools/list", {})).get("tools", [])
        logger.info("MCP server up; tools: %s", [t.get("name") for t in tools])

    async def stop(self) -> None:
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._proc.kill()

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("MCP server is not running")
        rpc_id = next(self._ids)
        message = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}
        line = json.dumps(message) + "\n"
        async with self._lock:
            self._proc.stdin.write(line.encode("utf-8"))
            await self._proc.stdin.drain()
            raw = await self._proc.stdout.readline()
        if not raw:
            raise RuntimeError("MCP server closed its stdout")
        try:
            response = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"MCP server returned non-JSON: {raw!r} ({e})")
        if "error" in response:
            err = response["error"]
            raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
        return response.get("result", {})


def _load_card() -> dict[str, Any]:
    card = yaml.safe_load(CARD_PATH.read_text()) or {}
    if not card.get("id"):
        raise RuntimeError(f"{CARD_PATH} is missing 'id'")
    card["endpoint"] = f"http://{HOST}:{PORT}/invoke"
    card.setdefault("provenance", {}).setdefault("model", "none")
    return card


async def _wait_for_registry(client: httpx.AsyncClient, deadline_seconds: float = 30.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + deadline_seconds
    while loop.time() < deadline:
        try:
            r = await client.get(f"{REGISTRY_URL}/healthz", timeout=2.0)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError(f"registry at {REGISTRY_URL} did not become ready")


async def _register(card: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        await _wait_for_registry(client)
        r = await client.post(f"{REGISTRY_URL}/register", json=card)
        r.raise_for_status()
        logger.info("registered %s with %s", card["id"], REGISTRY_URL)


app = FastAPI()
mcp = McpClient(MCP_SERVER_CMD)
card: dict[str, Any] = {}


@app.on_event("startup")
async def _startup() -> None:
    global card
    card = _load_card()
    await mcp.start()
    await _register(card)


@app.on_event("shutdown")
async def _shutdown() -> None:
    await mcp.stop()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True, "capability": card.get("id")}


@app.get("/cards/{capability_id}")
async def get_card(capability_id: str) -> JSONResponse:
    if capability_id != card.get("id"):
        raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
    return JSONResponse(card)


@app.post("/invoke")
async def invoke(request: Request) -> JSONResponse:
    capability_id = request.query_params.get("capability")
    if capability_id != card.get("id"):
        raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
    body = await request.json()
    trace_id = body.get("trace_id", "")
    inputs = body.get("inputs", {}) or {}
    op = inputs.get("op")
    if op not in {"write_ingest", "search"}:
        raise HTTPException(status_code=400, detail=f"unsupported op: {op!r}")

    try:
        mcp_result = await mcp.request("tools/call", {"name": op, "arguments": inputs})
    except RuntimeError as e:
        return JSONResponse(
            {
                "trace_id": trace_id,
                "outputs": {},
                "signals": {"path_within_root": False, "error": str(e)},
            },
            status_code=400,
        )

    outputs: dict[str, Any] = {}
    if op == "write_ingest":
        outputs["stored"] = mcp_result.get("stored", {})
        outputs["markdown"] = _first_text(mcp_result)
    elif op == "search":
        outputs["passages"] = mcp_result.get("passages", [])
        outputs["text"] = _first_text(mcp_result)

    return JSONResponse(
        {
            "trace_id": trace_id,
            "outputs": outputs,
            "signals": {
                "path_within_root": True,
                "index_updated": op == "write_ingest" and bool(outputs.get("stored")),
                "passages_have_citations": op != "search" or all(
                    isinstance(p, dict) and p.get("passage_id") and p.get("source_path")
                    for p in outputs.get("passages", [])
                ),
            },
        }
    )


def _first_text(mcp_result: dict[str, Any]) -> str:
    for block in mcp_result.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
    return ""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
