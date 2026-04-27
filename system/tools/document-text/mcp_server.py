"""A small Model Context Protocol server for document text extraction.

Speaks JSON-RPC 2.0 over stdio. One newline-delimited JSON message per line
in either direction.

The MCP methods this server understands:

- ``initialize``  — handshake; returns server name and protocol version.
- ``tools/list``  — list available tools.
- ``tools/call``  — invoke a named tool with arguments.

Tools provided:

- ``extract_text({path})`` -> ``{content: [{type: "text", text: "..."}],
                                media_type: "..."}``

All paths must resolve inside ``FS_ROOT`` (default ``/data``). UTF-8 text,
markdown, and PDFs with embedded text are supported. Scanned image PDFs are a
separate OCR capability, not this tool.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


SERVER_NAME = "aoa-course-document-text"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"


def _root() -> Path:
    return Path(os.environ.get("FS_ROOT", "/data")).resolve()


class DocumentTextError(Exception):
    """Raised for refused or failed document extraction."""


def _resolve_inside_root(raw_path: str) -> Path:
    if not raw_path:
        raise DocumentTextError("path is required")
    root = _root()
    candidate = (
        (root / raw_path).resolve()
        if not Path(raw_path).is_absolute()
        else Path(raw_path).resolve()
    )
    try:
        candidate.relative_to(root)
    except ValueError:
        raise DocumentTextError(f"path outside allowed root: {raw_path}")
    return candidate


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except Exception as e:  # noqa: BLE001
        raise DocumentTextError(f"could not extract text from PDF: {path} ({e})")
    if not text.strip():
        raise DocumentTextError(f"PDF contained no extractable text: {path}")
    return text


def _extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path), "application/pdf"
    if suffix in {".txt", ".md", ".markdown", ".text", ""}:
        try:
            return path.read_text(encoding="utf-8"), "text/plain"
        except UnicodeDecodeError as e:
            raise DocumentTextError(f"file is not utf-8 text: {path} ({e})")
    raise DocumentTextError(f"unsupported document type: {suffix or 'no extension'}")


def _tool_extract_text(args: dict[str, Any]) -> dict[str, Any]:
    path = _resolve_inside_root(args.get("path", ""))
    if not path.exists():
        raise DocumentTextError(f"no such file: {path}")
    if not path.is_file():
        raise DocumentTextError(f"not a file: {path}")
    text, media_type = _extract_text(path)
    return {
        "content": [{"type": "text", "text": text}],
        "media_type": media_type,
    }


TOOLS: dict[str, dict[str, Any]] = {
    "extract_text": {
        "name": "extract_text",
        "description": "Extract plain text from a supported document under the configured root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        "_handler": _tool_extract_text,
    },
}


def _public_tool_descriptors() -> list[dict[str, Any]]:
    return [
        {k: v for k, v in tool.items() if not k.startswith("_")}
        for tool in TOOLS.values()
    ]


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
        raise DocumentTextError(f"unknown tool: {name}")
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
        if rpc_id is None:
            return None
        return _error(rpc_id, -32601, f"unknown method: {method}")
    try:
        result = handler(params)
    except DocumentTextError as e:
        return _error(rpc_id, -32000, str(e))
    except Exception as e:  # noqa: BLE001
        return _error(rpc_id, -32603, f"internal error: {e!r}")
    if rpc_id is None:
        return None
    return _ok(rpc_id, result)


def main() -> None:
    print(
        f"# aoa-course-document-text MCP server starting (root={_root()})",
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
