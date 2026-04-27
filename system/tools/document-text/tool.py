"""Registered document-text extraction tool.

This tool keeps document parsing separate from low-level filesystem access.
Agents hand it an inbox path and receive extracted plain text. The studio
writes uploaded bytes; this tool owns the decision about how to interpret
those bytes.
"""
from __future__ import annotations

import logging
import os
import asyncio
from pathlib import Path
from typing import Any

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("document-text")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://registry:7100").rstrip("/")
PORT = int(os.environ.get("TOOL_PORT", "7402"))
HOST = os.environ.get("TOOL_HOST", "tool-document-text")
FS_ROOT = Path(os.environ.get("FS_ROOT", "/data")).resolve()
CARD_PATH = Path(os.environ.get("CARD_PATH", "/app/capability-card.yaml"))


class ToolError(Exception):
    pass


def _resolve_inside_root(raw_path: str) -> Path:
    if not raw_path:
        raise ToolError("path is required")
    candidate = (
        (FS_ROOT / raw_path).resolve()
        if not Path(raw_path).is_absolute()
        else Path(raw_path).resolve()
    )
    try:
        candidate.relative_to(FS_ROOT)
    except ValueError:
        raise ToolError(f"path outside allowed root: {raw_path}")
    return candidate


def _extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path), "application/pdf"
    if suffix in {".txt", ".md", ".markdown", ".text", ""}:
        try:
            return path.read_text(encoding="utf-8"), "text/plain"
        except UnicodeDecodeError as e:
            raise ToolError(f"file is not utf-8 text: {path} ({e})")
    raise ToolError(f"unsupported document type: {suffix or 'no extension'}")


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except Exception as e:  # noqa: BLE001
        raise ToolError(f"could not extract text from PDF: {path} ({e})")
    if not text.strip():
        raise ToolError(f"PDF contained no extractable text: {path}")
    return text


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
card: dict[str, Any] = {}


@app.on_event("startup")
async def _startup() -> None:
    global card
    card = _load_card()
    await _register(card)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True, "capability": card.get("id"), "root": str(FS_ROOT)}


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
    try:
        path = _resolve_inside_root(inputs.get("path", ""))
        if not path.exists():
            raise ToolError(f"no such file: {path}")
        if not path.is_file():
            raise ToolError(f"not a file: {path}")
        text, media_type = _extract_text(path)
    except ToolError as e:
        return JSONResponse(
            {
                "trace_id": trace_id,
                "outputs": {},
                "signals": {
                    "path_within_root": "outside allowed root" not in str(e),
                    "extracted_text_present": False,
                    "error": str(e),
                },
            },
            status_code=400,
        )

    return JSONResponse(
        {
            "trace_id": trace_id,
            "outputs": {"text": text, "media_type": media_type},
            "signals": {
                "path_within_root": True,
                "extracted_text_present": bool(text.strip()),
            },
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
