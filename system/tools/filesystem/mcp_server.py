"""A small Model Context Protocol server for filesystem reads.

Speaks JSON-RPC 2.0 over stdio. One newline-delimited JSON message per line
in either direction.

The MCP methods this server understands:

- ``initialize``  — handshake; returns server name and protocol version.
- ``tools/list``  — list available tools.
- ``tools/call``  — invoke a named tool with arguments.

Tools provided:

- ``read_file({path})``      → ``{content: [{type: "text", text: "..."}]}``
- ``list_directory({path})`` → ``{content: [{type: "text", text: "..."}],
                                  entries: [{name, kind}, ...]}``

All paths must resolve inside ``FS_ROOT`` (default ``/data``). Anything else
returns a JSON-RPC error.

The wire shape follows the MCP 2025-06-18 spec for ``tools/call`` (a content
array with typed blocks). The bridge in ``bridge.py`` parses the structured
extras (``entries``) when present.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


SERVER_NAME = "aoa-course-filesystem"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"


def _root() -> Path:
    return Path(os.environ.get("FS_ROOT", "/data")).resolve()


# ----------------------------------------------------------------------
# Path safety
# ----------------------------------------------------------------------

class FsError(Exception):
    """Raised for any filesystem operation refused on safety or IO grounds."""


def _resolve_inside_root(raw_path: str) -> Path:
    if not raw_path:
        raise FsError("path is required")
    root = _root()
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise FsError(f"path outside allowed root: {raw_path}")
    return candidate


# ----------------------------------------------------------------------
# Tool implementations
# ----------------------------------------------------------------------

def _tool_read_file(args: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_inside_root(args.get("path", ""))
    if not path.exists():
        raise FsError(f"no such file: {path}")
    if not path.is_file():
        raise FsError(f"not a file: {path}")
    if path.suffix.lower() == ".pdf":
        return {"content": [{"type": "text", "text": _read_pdf_text(path)}]}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise FsError(f"file is not utf-8: {path} ({e})")
    return {"content": [{"type": "text", "text": text}]}


def _read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except Exception as e:  # noqa: BLE001
        raise FsError(f"could not extract text from PDF: {path} ({e})")
    if not text.strip():
        raise FsError(f"PDF contained no extractable text: {path}")
    return text


def _tool_list_directory(args: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_inside_root(args.get("path", ""))
    if not path.exists():
        raise FsError(f"no such directory: {path}")
    if not path.is_dir():
        raise FsError(f"not a directory: {path}")
    entries = []
    for child in sorted(path.iterdir()):
        kind = "dir" if child.is_dir() else "file"
        entries.append({"name": child.name, "kind": kind})
    rendered = "\n".join(
        f"[{'DIR' if e['kind'] == 'dir' else 'FILE'}] {e['name']}" for e in entries
    )
    # Per the MCP spec, the standard surface is the content array. We add
    # ``entries`` as a structured extra so the bridge can return it without
    # parsing the rendered text.
    return {
        "content": [{"type": "text", "text": rendered}],
        "entries": entries,
    }


TOOLS: dict[str, dict[str, Any]] = {
    "read_file": {
        "name": "read_file",
        "description": "Read a UTF-8 text file or extract text from a PDF under the configured root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        "_handler": _tool_read_file,
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List the contents of a directory under the configured root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        "_handler": _tool_list_directory,
    },
}


def _public_tool_descriptors() -> list[dict[str, Any]]:
    """Tool list returned to clients, with internal handler keys stripped."""
    return [
        {k: v for k, v in tool.items() if not k.startswith("_")}
        for tool in TOOLS.values()
    ]


# ----------------------------------------------------------------------
# JSON-RPC dispatch
# ----------------------------------------------------------------------

def _handle_initialize(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "capabilities": {"tools": {}},
    }


def _handle_tools_list(_params: dict[str, Any]) -> dict[str, Any]:
    return {"tools": _public_tool_descriptors()}


def _handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments") or {}
    tool = TOOLS.get(name)
    if tool is None:
        raise FsError(f"unknown tool: {name}")
    return tool["_handler"](args)


METHODS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def _error(rpc_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


def _ok(rpc_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _dispatch(message: dict[str, Any]) -> dict[str, Any] | None:
    rpc_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method is None:
        return _error(rpc_id, -32600, "method is required")
    handler = METHODS.get(method)
    if handler is None:
        # Notifications (no id) don't get a response.
        if rpc_id is None:
            return None
        return _error(rpc_id, -32601, f"unknown method: {method}")
    try:
        result = handler(params)
    except FsError as e:
        return _error(rpc_id, -32000, str(e))
    except Exception as e:  # noqa: BLE001
        return _error(rpc_id, -32603, f"internal error: {e!r}")
    if rpc_id is None:
        return None
    return _ok(rpc_id, result)


# ----------------------------------------------------------------------
# Stdio loop
# ----------------------------------------------------------------------

def main() -> None:
    print(
        f"# aoa-course-filesystem MCP server starting (root={_root()})",
        file=sys.stderr,
        flush=True,
    )
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as e:
            sys.stdout.write(json.dumps(_error(None, -32700, f"parse error: {e}")) + "\n")
            sys.stdout.flush()
            continue
        response = _dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
