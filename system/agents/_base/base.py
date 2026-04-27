"""Shared FastAPI scaffold every agent extends.

A concrete agent does roughly this::

    from _base.base import run, Context

    def handle(capability_id, inputs, ctx: Context):
        ...
        return {"outputs": {...}, "signals": {...}}

    if __name__ == "__main__":
        run(handle)

The scaffold takes care of the four jobs every agent does the same way:

1. Discover capability cards under ``capabilities/<name>/``.
2. Compute ``skills_hash`` for each by SHA-ing the matching ``skills.md``.
3. Register each capability with the registry on boot.
4. Watch each ``skills.md`` for changes and re-register on edit.

It also exposes the standard agent HTTP surface: ``/invoke``, ``/cards/<id>``,
and ``/healthz``.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .model import Model
from .registry_client import RegistryClient

logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


# ----------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------

@dataclass
class Capability:
    """A capability loaded from disk and ready to register."""

    id: str
    card: dict[str, Any]            # the full capability card, with skills_hash filled in
    skills_text: str                # current contents of skills.md
    skills_path: Path               # path to skills.md (for hot reload)
    card_path: Path                 # path to capability-card.yaml
    tools_needs: list[str] = field(default_factory=list)


@dataclass
class Context:
    """Per-invocation context passed to ``handle``.

    Concrete agents read ``capability``, ``model``, and ``skills`` to build a
    prompt; ``trace_id`` is forwarded into any tool calls so the planner can
    stitch the trace together.
    """

    capability: Capability
    model: Model
    skills: str
    trace_id: str
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)


Handler = Callable[[str, dict[str, Any], Context], dict[str, Any] | Awaitable[dict[str, Any]]]


# ----------------------------------------------------------------------
# Capability discovery
# ----------------------------------------------------------------------

def _agent_endpoint() -> str:
    """The endpoint other services use to call this agent."""
    host = os.environ.get("AGENT_HOST", os.environ.get("AGENT_NAME", "agent"))
    port = int(os.environ.get("AGENT_PORT", "7300"))
    return f"http://{host}:{port}/invoke"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _capabilities_root() -> Path:
    return Path(os.environ.get("CAPABILITIES_DIR", "/app/capabilities"))


def discover_capabilities() -> list[Capability]:
    """Walk ``capabilities/<name>/`` and load every capability card.

    A capability folder must contain ``capability-card.yaml``. ``skills.md``
    is required for AU capabilities and absent for tool capabilities (tools
    are deterministic; their behaviour is in their code).
    """
    root = _capabilities_root()
    if not root.exists():
        raise RuntimeError(f"capabilities directory not found: {root}")

    capabilities: list[Capability] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        card_path = child / "capability-card.yaml"
        if not card_path.exists():
            logger.warning("skipping %s: no capability-card.yaml", child)
            continue
        with card_path.open() as f:
            card = yaml.safe_load(f) or {}

        cap_id = card.get("id")
        if not cap_id:
            raise RuntimeError(f"{card_path} is missing 'id'")

        skills_path = child / "skills.md"
        if skills_path.exists():
            skills_text = skills_path.read_text()
            card.setdefault("provenance", {})["skills_hash"] = _sha256(skills_text)
        else:
            skills_text = ""
            card.setdefault("provenance", {}).setdefault("skills_hash", "")

        # Substitute ${MODEL} so the registry shows the concrete model in use.
        prov = card.setdefault("provenance", {})
        if prov.get("model") in (None, "${MODEL}"):
            prov["model"] = os.environ.get("MODEL", "${MODEL}")

        # Endpoint is filled in by the scaffold so cards don't have to know
        # their host. Per AGENTS.md the planner uses the registered endpoint.
        card["endpoint"] = _agent_endpoint()

        # tools.yaml is optional; an empty needs list is fine.
        tools_path = child / "tools.yaml"
        tools_needs: list[str] = []
        if tools_path.exists():
            tools_doc = yaml.safe_load(tools_path.read_text()) or {}
            tools_needs = list(tools_doc.get("needs", []) or [])

        capabilities.append(
            Capability(
                id=cap_id,
                card=card,
                skills_text=skills_text,
                skills_path=skills_path,
                card_path=card_path,
                tools_needs=tools_needs,
            )
        )

    if not capabilities:
        raise RuntimeError(f"no capabilities found under {root}")
    return capabilities


# ----------------------------------------------------------------------
# Hot reload
# ----------------------------------------------------------------------

async def _watch_skills(
    capabilities: list[Capability],
    registry: RegistryClient,
) -> None:
    """Watch every skills.md file and re-register the affected capability on change.

    This runs as a background asyncio task started during FastAPI startup.
    """
    from watchfiles import awatch

    paths = [str(c.skills_path) for c in capabilities if c.skills_path.exists()]
    if not paths:
        return

    by_path = {str(c.skills_path): c for c in capabilities}
    logger.info("watching %d skills.md file(s) for hot reload", len(paths))

    async for changes in awatch(*paths):
        touched: set[str] = set()
        for _change_type, changed_path in changes:
            if changed_path in by_path:
                touched.add(changed_path)
        for changed_path in touched:
            cap = by_path[changed_path]
            try:
                new_text = cap.skills_path.read_text()
            except FileNotFoundError:
                continue
            new_hash = _sha256(new_text)
            old_hash = cap.card.get("provenance", {}).get("skills_hash")
            if new_hash == old_hash:
                continue
            cap.skills_text = new_text
            cap.card.setdefault("provenance", {})["skills_hash"] = new_hash
            try:
                registry.update(cap.card)
                logger.info("reloaded %s (skills_hash %s)", cap.id, new_hash[:8])
            except Exception:  # noqa: BLE001
                logger.exception("failed to update %s on registry", cap.id)


# ----------------------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------------------

def _resolve_tool_handles(
    capabilities: list[Capability],
    registry: RegistryClient,
) -> dict[str, dict[str, Any]]:
    """Resolve every tools.yaml `needs` entry into a registered card.

    Per AGENTS.md, agents call other capabilities through the registry. The
    handles are just the cards (which contain the endpoint); the agent does
    the HTTP call itself when invoking a tool.
    """
    needed: set[str] = set()
    for cap in capabilities:
        needed.update(cap.tools_needs)
    if not needed:
        return {}
    registry.wait_for_capabilities(sorted(needed))
    handles: dict[str, dict[str, Any]] = {}
    for cap_id in sorted(needed):
        card = registry.find(cap_id)
        if card is None:
            raise RuntimeError(f"required capability {cap_id} disappeared from registry")
        handles[cap_id] = card
    return handles


def build_app(handle: Handler) -> FastAPI:
    """Build the FastAPI app for an agent given its ``handle`` function."""
    app = FastAPI()

    capabilities = discover_capabilities()
    by_id = {c.id: c for c in capabilities}
    registry = RegistryClient()
    model = Model()
    tool_handles: dict[str, dict[str, Any]] = {}

    @app.on_event("startup")
    async def _startup() -> None:
        nonlocal tool_handles
        registry.wait_until_ready()
        tool_handles = _resolve_tool_handles(capabilities, registry)
        for cap in capabilities:
            registry.register(cap.card)
            logger.info("registered %s", cap.id)
        # Start hot-reload watcher in the background.
        asyncio.create_task(_watch_skills(capabilities, registry))

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "capabilities": [c.id for c in capabilities]}

    @app.get("/cards/{capability_id}")
    async def get_card(capability_id: str) -> JSONResponse:
        cap = by_id.get(capability_id)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
        return JSONResponse(cap.card)

    @app.post("/invoke")
    async def invoke(request: Request) -> JSONResponse:
        capability_id = request.query_params.get("capability")
        if not capability_id:
            raise HTTPException(status_code=400, detail="missing ?capability=<id>")
        cap = by_id.get(capability_id)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")

        body = await request.json()
        trace_id = body.get("trace_id", "")
        inputs = body.get("inputs", {})

        ctx = Context(
            capability=cap,
            model=model,
            skills=cap.skills_text,
            trace_id=trace_id,
            tools=tool_handles,
        )

        result = handle(capability_id, inputs, ctx)
        if asyncio.iscoroutine(result):
            result = await result

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail=f"handle() returned {type(result).__name__}, expected dict",
            )
        outputs = result.get("outputs", {})
        signals = result.get("signals", {})
        return JSONResponse(
            {"trace_id": trace_id, "outputs": outputs, "signals": signals}
        )

    return app


def run(handle: Handler) -> None:
    """Entry point for an agent ``__main__`` block.

    Concrete agents call ``run(handle)`` from their ``agent.py``. The function
    builds the FastAPI app and starts uvicorn listening on ``AGENT_PORT``.
    """
    app = build_app(handle)
    port = int(os.environ.get("AGENT_PORT", "7300"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
