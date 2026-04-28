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

It also exposes the standard agent HTTP surface: ``/a2a``,
``/.well-known/agent-card.json``, ``/invoke``, ``/cards/<id>``, and
``/healthz``.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
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


class ToolHandle:
    """Awaitable handle for a capability listed in ``tools.yaml``.

    Calling a handle is just an HTTP POST to the capability's endpoint, but
    the wrapper hides three pieces of plumbing so agent code reads as the
    teaching wants it to read::

        passages = await ctx.tools["tool-document-text"]({"path": p})

    Specifically the wrapper:

    1. Threads ``ctx.trace_id`` into the request body so the planner can stitch
       the call into the running trace.
    2. Posts to the registered ``endpoint`` with ``?capability=<id>`` set.
    3. Returns ``response["outputs"]`` directly — agents almost always want
       just the outputs, not the full envelope. Use ``.invoke_raw()`` if you
       want signals too.
    """

    def __init__(
        self,
        capability_id: str,
        card: dict[str, Any],
        client: httpx.AsyncClient,
        trace_id_provider: Callable[[], str],
        timeout_seconds: float = 60.0,
    ) -> None:
        self.capability_id = capability_id
        self.card = card
        self._client = client
        self._trace_id_provider = trace_id_provider
        self._timeout = timeout_seconds

    async def __call__(self, inputs: dict[str, Any]) -> dict[str, Any]:
        envelope = await self.invoke_raw(inputs)
        return envelope.get("outputs", {})

    async def invoke_raw(self, inputs: dict[str, Any]) -> dict[str, Any]:
        payload = {"trace_id": self._trace_id_provider(), "inputs": inputs}
        r = await self._client.post(
            self.card["endpoint"],
            params={"capability": self.capability_id},
            json=payload,
            timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json()


@dataclass
class Context:
    """Per-invocation context passed to ``handle``.

    Concrete agents read ``capability``, ``model``, and ``skills`` to build a
    prompt. ``tools`` holds awaitable handles for every capability the agent
    declared in ``tools.yaml`` — call them like functions.
    """

    capability: Capability
    model: Model
    skills: str
    trace_id: str
    tools: dict[str, ToolHandle] = field(default_factory=dict)


Handler = Callable[[str, dict[str, Any], Context], dict[str, Any] | Awaitable[dict[str, Any]]]


# ----------------------------------------------------------------------
# Capability discovery
# ----------------------------------------------------------------------

def _agent_endpoint() -> str:
    """The endpoint other services use to call this agent."""
    host = os.environ.get("AGENT_HOST", os.environ.get("AGENT_NAME", "agent"))
    port = int(os.environ.get("AGENT_PORT", "7300"))
    return f"http://{host}:{port}/invoke"


def _agent_a2a_endpoint() -> str:
    """The A2A JSON-RPC endpoint for this agent."""
    host = os.environ.get("AGENT_HOST", os.environ.get("AGENT_NAME", "agent"))
    port = int(os.environ.get("AGENT_PORT", "7300"))
    return f"http://{host}:{port}/a2a"


def _agent_card_url() -> str:
    """The well-known URL for this agent's A2A Agent Card."""
    host = os.environ.get("AGENT_HOST", os.environ.get("AGENT_NAME", "agent"))
    port = int(os.environ.get("AGENT_PORT", "7300"))
    return f"http://{host}:{port}/.well-known/agent-card.json"


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
        if card.get("kind") == "au":
            card["agent_card_url"] = _agent_card_url()
            card["a2a_endpoint"] = _agent_a2a_endpoint()

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

def _resolve_tool_cards(
    capabilities: list[Capability],
    registry: RegistryClient,
) -> dict[str, dict[str, Any]]:
    """Resolve every tools.yaml `needs` entry into a registered card.

    Returns a dict of ``capability_id -> card``. The cards are wrapped into
    ``ToolHandle`` instances per request, since each handle binds a trace id.
    """
    needed: set[str] = set()
    for cap in capabilities:
        needed.update(cap.tools_needs)
    if not needed:
        return {}
    registry.wait_for_capabilities(sorted(needed))
    cards: dict[str, dict[str, Any]] = {}
    for cap_id in sorted(needed):
        card = registry.find(cap_id)
        if card is None:
            raise RuntimeError(f"required capability {cap_id} disappeared from registry")
        cards[cap_id] = card
    return cards


def _description_from_purpose(card: dict[str, Any]) -> str:
    purpose = str(card.get("purpose", "")).strip()
    if not purpose:
        return f"Capability {card.get('id', 'unknown')}"
    return " ".join(purpose.split())


def _build_agent_card(capabilities: list[Capability]) -> dict[str, Any]:
    """Build the public A2A Agent Card for this process.

    AOA capability cards carry richer course-specific contracts than A2A skills,
    so the full cards are advertised through a data-only A2A extension.
    """
    agent_name = os.environ.get("AGENT_NAME", "agent")
    descriptions = [_description_from_purpose(cap.card) for cap in capabilities]
    description = (
        descriptions[0]
        if len(descriptions) == 1
        else f"{agent_name} agent serving {len(descriptions)} AOA capabilities."
    )
    return {
        "protocolVersion": "0.3.0",
        "name": agent_name,
        "description": description,
        "url": _agent_a2a_endpoint(),
        "preferredTransport": "JSONRPC",
        "version": "0.1.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
            "extensions": [
                {
                    "uri": "urn:aoa:extensions:capability-card:v1",
                    "description": "AOA capability-card contracts exposed by this A2A agent.",
                    "required": False,
                    "params": {
                        "capabilities": [cap.card for cap in capabilities],
                    },
                }
            ],
        },
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json", "text/markdown", "text/plain"],
        "skills": [
            {
                "id": cap.id,
                "name": cap.id,
                "description": _description_from_purpose(cap.card),
                "tags": ["aoa", "agentic-unit"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json", "text/markdown"],
            }
            for cap in capabilities
        ],
    }


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _extract_a2a_invocation(params: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Extract AOA invocation details from A2A MessageSendParams."""
    metadata = params.get("metadata") or {}
    message = params.get("message") or {}
    message_metadata = message.get("metadata") or {}
    capability_id = (
        metadata.get("aoa_capability")
        or message_metadata.get("aoa_capability")
        or metadata.get("capability")
        or message_metadata.get("capability")
        or ""
    )
    trace_id = (
        metadata.get("trace_id")
        or message_metadata.get("trace_id")
        or params.get("taskId")
        or ""
    )

    inputs: dict[str, Any] = {}
    for part in message.get("parts") or []:
        if part.get("kind") != "data":
            continue
        data = part.get("data")
        if not isinstance(data, dict):
            continue
        if not capability_id:
            capability_id = str(data.get("aoa_capability") or data.get("capability") or "")
        if not trace_id:
            trace_id = str(data.get("trace_id") or "")
        maybe_inputs = data.get("inputs", data)
        if isinstance(maybe_inputs, dict):
            inputs = maybe_inputs
            break

    return capability_id, trace_id, inputs


def _markdown_output(outputs: dict[str, Any]) -> str | None:
    for key in ("report_markdown", "answer_markdown", "ingest_markdown", "markdown"):
        value = outputs.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def build_app(handle: Handler) -> FastAPI:
    """Build the FastAPI app for an agent given its ``handle`` function."""
    app = FastAPI()

    capabilities = discover_capabilities()
    by_id = {c.id: c for c in capabilities}
    agent_card = _build_agent_card(capabilities)
    registry = RegistryClient()
    model: Model | None = None
    tool_cards: dict[str, dict[str, Any]] = {}
    tool_client: httpx.AsyncClient | None = None

    @app.on_event("startup")
    async def _startup() -> None:
        nonlocal tool_cards, tool_client
        registry.wait_until_ready()
        tool_cards = _resolve_tool_cards(capabilities, registry)
        tool_client = httpx.AsyncClient()
        for cap in capabilities:
            registry.register(cap.card)
            logger.info("registered %s", cap.id)
        # Start hot-reload watcher in the background.
        asyncio.create_task(_watch_skills(capabilities, registry))

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        if tool_client is not None:
            await tool_client.aclose()

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "capabilities": [c.id for c in capabilities]}

    @app.get("/cards/{capability_id}")
    async def get_card(capability_id: str) -> JSONResponse:
        cap = by_id.get(capability_id)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")
        return JSONResponse(cap.card)

    @app.get("/.well-known/agent-card.json")
    async def get_agent_card() -> JSONResponse:
        return JSONResponse(agent_card)

    @app.get("/a2a/.well-known/agent-card.json")
    async def get_scoped_agent_card() -> JSONResponse:
        return JSONResponse(agent_card)

    async def _invoke_capability(
        capability_id: str,
        trace_id: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        nonlocal model
        cap = by_id.get(capability_id)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"unknown capability: {capability_id}")

        try:
            if model is None:
                model = Model()

            # Bind a fresh ToolHandle set per request so trace_id propagates.
            assert tool_client is not None
            handles: dict[str, ToolHandle] = {
                cid: ToolHandle(cid, card, tool_client, lambda tid=trace_id: tid)
                for cid, card in tool_cards.items()
            }
            ctx = Context(
                capability=cap,
                model=model,
                skills=cap.skills_text,
                trace_id=trace_id,
                tools=handles,
            )

            result = handle(capability_id, inputs, ctx)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception as e:  # noqa: BLE001
            logger.exception("capability %s failed", capability_id)
            return {
                "trace_id": trace_id,
                "outputs": {"error": str(e)},
                "signals": {
                    "exception": True,
                    "exception_type": type(e).__name__,
                    "error": str(e),
                },
            }

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail=f"handle() returned {type(result).__name__}, expected dict",
            )
        outputs = result.get("outputs", {})
        signals = result.get("signals", {})
        return {"trace_id": trace_id, "outputs": outputs, "signals": signals}

    @app.post("/invoke")
    async def invoke(request: Request) -> JSONResponse:
        capability_id = request.query_params.get("capability")
        if not capability_id:
            raise HTTPException(status_code=400, detail="missing ?capability=<id>")

        body = await request.json()
        trace_id = body.get("trace_id", "")
        inputs = body.get("inputs", {})
        envelope = await _invoke_capability(capability_id, trace_id, inputs)
        return JSONResponse(envelope)

    @app.post("/a2a")
    async def a2a(request: Request) -> JSONResponse:
        body = await request.json()
        request_id = body.get("id")
        if body.get("jsonrpc") != "2.0":
            return JSONResponse(_jsonrpc_error(request_id, -32600, "expected JSON-RPC 2.0"))
        if body.get("method") != "message/send":
            return JSONResponse(_jsonrpc_error(request_id, -32601, "method not found"))
        params = body.get("params") or {}
        if not isinstance(params, dict):
            return JSONResponse(_jsonrpc_error(request_id, -32602, "params must be an object"))

        capability_id, trace_id, inputs = _extract_a2a_invocation(params)
        if not capability_id:
            return JSONResponse(_jsonrpc_error(request_id, -32602, "missing aoa_capability metadata"))
        if not trace_id:
            trace_id = uuid.uuid4().hex[:12]

        try:
            envelope = await _invoke_capability(capability_id, trace_id, inputs)
        except HTTPException as e:
            return JSONResponse(_jsonrpc_error(request_id, e.status_code, str(e.detail)))

        outputs = envelope.get("outputs", {})
        signals = envelope.get("signals", {})
        parts: list[dict[str, Any]] = []
        if isinstance(outputs, dict):
            markdown = _markdown_output(outputs)
            if markdown is not None:
                parts.append({"kind": "text", "text": markdown})
        parts.append({
            "kind": "data",
            "data": {
                "trace_id": trace_id,
                "aoa_capability": capability_id,
                "outputs": outputs,
                "signals": signals,
            },
        })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "kind": "message",
                "messageId": f"{trace_id}-{capability_id}-response",
                "role": "agent",
                "parts": parts,
                "metadata": {
                    "trace_id": trace_id,
                    "aoa_capability": capability_id,
                },
            },
        })

    return app


def run(handle: Handler) -> None:
    """Entry point for an agent ``__main__`` block.

    Concrete agents call ``run(handle)`` from their ``agent.py``. The function
    builds the FastAPI app and starts uvicorn listening on ``AGENT_PORT``.
    """
    app = build_app(handle)
    port = int(os.environ.get("AGENT_PORT", "7300"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
