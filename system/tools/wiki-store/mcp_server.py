"""A small MCP server for the course wiki store.

The store has three layers:

- ``raw/`` keeps a copy of the source material when the source path is readable.
- ``promoted/`` contains generated markdown pages.
- ``index.json`` is the deterministic access surface used by search.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVER_NAME = "aoa-course-wiki-store"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
TOKEN_RE = re.compile(r"[a-z0-9]+")
SLUG_RE = re.compile(r"[^a-z0-9]+")


class WikiError(Exception):
    pass


def _root() -> Path:
    return Path(os.environ.get("WIKI_ROOT", "/data/wiki")).resolve()


def _data_root() -> Path:
    return Path(os.environ.get("FS_ROOT", "/data")).resolve()


def _ensure_dirs() -> None:
    for name in ("raw", "promoted"):
        (_root() / name).mkdir(parents=True, exist_ok=True)
    if not _index_path().exists():
        _write_index({"documents": []})


def _index_path() -> Path:
    return _root() / "index.json"


def _read_index() -> dict[str, Any]:
    _ensure_dirs()
    try:
        return json.loads(_index_path().read_text())
    except json.JSONDecodeError as e:
        raise WikiError(f"index.json is not valid JSON: {e}")


def _write_index(index: dict[str, Any]) -> None:
    _root().mkdir(parents=True, exist_ok=True)
    tmp = _index_path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
    tmp.replace(_index_path())


def _slug(value: str) -> str:
    slug = SLUG_RE.sub("-", value.lower()).strip("-")
    return slug[:80] or "untitled"


def _resolve_inside_data(raw_path: str) -> Path:
    if not raw_path:
        raise WikiError("path is required")
    root = _data_root()
    candidate = (
        (root / raw_path).resolve()
        if not Path(raw_path).is_absolute()
        else Path(raw_path).resolve()
    )
    try:
        candidate.relative_to(root)
    except ValueError:
        raise WikiError(f"path outside allowed data root: {raw_path}")
    return candidate


def _markdown_for_promotion(promotion: dict[str, Any], source_path: str, stored_at: str) -> str:
    title = str(promotion.get("title") or "Untitled AOA note").strip()
    summary = str(promotion.get("summary") or "").strip()
    concepts = promotion.get("concepts") if isinstance(promotion.get("concepts"), list) else []
    passages = promotion.get("promoted_passages") if isinstance(promotion.get("promoted_passages"), list) else []
    relationships = promotion.get("relationships") if isinstance(promotion.get("relationships"), list) else []
    questions = promotion.get("open_questions") if isinstance(promotion.get("open_questions"), list) else []

    lines = [
        f"# {title}",
        "",
        f"- source: `{source_path}`",
        f"- stored_at: `{stored_at}`",
        "",
    ]
    if summary:
        lines += ["## Summary", summary, ""]
    lines += _object_list("Concepts", concepts)
    lines += _object_list("Promoted passages", passages)
    lines += _object_list("Relationships", relationships)
    lines += _object_list("Open questions", questions)
    return "\n".join(lines).strip() + "\n"


def _object_list(title: str, values: list[Any]) -> list[str]:
    if not values:
        return []
    lines = [f"## {title}"]
    for item in values:
        if isinstance(item, dict):
            label = item.get("name") or item.get("title") or item.get("passage_id") or item.get("term")
            text = item.get("description") or item.get("summary") or item.get("claim") or item.get("quote")
            parts = [str(label).strip()] if label else []
            if text:
                parts.append(str(text).strip())
            if not parts:
                parts.append(json.dumps(item, sort_keys=True))
            lines.append(f"- {' - '.join(parts)}")
        else:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")
    return lines + [""]


def _passages_for_index(promotion: dict[str, Any], doc_id: str, title: str, markdown_path: str) -> list[dict[str, Any]]:
    raw_passages = promotion.get("promoted_passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        summary = str(promotion.get("summary") or "").strip()
        if not summary:
            return []
        raw_passages = [{"passage_id": "summary", "quote": summary, "why_it_matters": "summary"}]

    passages = []
    for i, item in enumerate(raw_passages, start=1):
        if isinstance(item, dict):
            passage_id = str(item.get("passage_id") or f"p{i}")
            quote = str(item.get("quote") or item.get("claim") or item.get("summary") or "").strip()
            why = str(item.get("why_it_matters") or item.get("reason") or "").strip()
        else:
            passage_id = f"p{i}"
            quote = str(item).strip()
            why = ""
        if quote:
            passages.append({
                "passage_id": f"{doc_id}:{passage_id}",
                "document_id": doc_id,
                "title": title,
                "quote": quote,
                "why_it_matters": why,
                "source_path": markdown_path,
            })
    return passages


def _tool_write_ingest(args: dict[str, Any]) -> dict[str, Any]:
    promotion = args.get("promotion")
    source_path = str(args.get("source_path") or "")
    if not isinstance(promotion, dict):
        raise WikiError("promotion object is required")
    if not source_path:
        raise WikiError("source_path is required")

    _ensure_dirs()
    stored_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title = str(promotion.get("title") or "Untitled AOA note").strip()
    doc_id = _slug(title)
    markdown_rel = f"promoted/{doc_id}.md"
    markdown_path = _root() / markdown_rel
    counter = 2
    while markdown_path.exists():
        doc_id = f"{_slug(title)}-{counter}"
        markdown_rel = f"promoted/{doc_id}.md"
        markdown_path = _root() / markdown_rel
        counter += 1

    raw_rel = ""
    try:
        source = _resolve_inside_data(source_path)
        if source.exists() and source.is_file():
            raw_rel = f"raw/{doc_id}{source.suffix or '.txt'}"
            shutil.copyfile(source, _root() / raw_rel)
    except WikiError:
        raise
    except OSError:
        raw_rel = ""

    markdown = _markdown_for_promotion(promotion, source_path, stored_at)
    markdown_path.write_text(markdown)

    index = _read_index()
    doc = {
        "document_id": doc_id,
        "title": title,
        "summary": str(promotion.get("summary") or ""),
        "source_path": source_path,
        "raw_path": raw_rel,
        "markdown_path": markdown_rel,
        "stored_at": stored_at,
        "concepts": promotion.get("concepts", []),
        "relationships": promotion.get("relationships", []),
        "open_questions": promotion.get("open_questions", []),
        "passages": _passages_for_index(promotion, doc_id, title, markdown_rel),
    }
    index.setdefault("documents", []).append(doc)
    _write_index(index)
    return {
        "content": [{"type": "text", "text": markdown}],
        "stored": {
            "document_id": doc_id,
            "title": title,
            "promoted_path": str(markdown_path),
            "markdown_path": str(markdown_path),
            "raw_path": str(_root() / raw_rel) if raw_rel else "",
            "passage_count": len(doc["passages"]),
        },
    }


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _tool_search(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    limit = int(args.get("limit") or 8)
    if not query:
        raise WikiError("query is required")
    query_tokens = _tokens(query)
    index = _read_index()
    scored = []
    for doc in index.get("documents", []) or []:
        for passage in doc.get("passages", []) or []:
            text = " ".join([
                str(doc.get("title", "")),
                str(doc.get("summary", "")),
                str(passage.get("quote", "")),
                str(passage.get("why_it_matters", "")),
            ])
            overlap = sorted(query_tokens & _tokens(text))
            if not overlap:
                continue
            scored.append({
                **passage,
                "score": len(overlap),
                "matched_terms": overlap,
            })
    scored.sort(key=lambda p: (-p["score"], p["passage_id"]))
    passages = scored[:limit]
    rendered = "\n\n".join(
        f"[{p['passage_id']}] {p['quote']}" for p in passages
    )
    return {
        "content": [{"type": "text", "text": rendered}],
        "passages": passages,
    }


TOOLS: dict[str, dict[str, Any]] = {
    "write_ingest": {
        "name": "write_ingest",
        "description": "Persist promoted knowledge into raw/promoted/index wiki layers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "promotion": {"type": "object"},
                "source_path": {"type": "string"},
            },
            "required": ["promotion", "source_path"],
        },
        "_handler": _tool_write_ingest,
    },
    "search": {
        "name": "search",
        "description": "Search the local wiki index for passages relevant to a question.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        "_handler": _tool_search,
    },
}


def _public_tool_descriptors() -> list[dict[str, Any]]:
    return [
        {k: v for k, v in tool.items() if not k.startswith("_")}
        for tool in TOOLS.values()
    ]


def _handle_initialize(_params: dict[str, Any]) -> dict[str, Any]:
    _ensure_dirs()
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
        raise WikiError(f"unknown tool: {name}")
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
    except WikiError as e:
        return _error(rpc_id, -32000, str(e))
    except Exception as e:  # noqa: BLE001
        return _error(rpc_id, -32603, f"internal error: {e!r}")
    if rpc_id is None:
        return None
    return _ok(rpc_id, result)


def main() -> None:
    print(
        f"# aoa-course-wiki-store MCP server starting (root={_root()})",
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
