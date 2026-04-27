# tool-document-text

A registered deterministic capability of `kind: tool`. The container runs two
processes:

1. `mcp_server.py` — a Model Context Protocol server speaking JSON-RPC 2.0
   over stdio. Exposes one MCP tool, `extract_text`.
2. `bridge.py` — a small FastAPI service that registers `tool-document-text`
   with the system registry, exposes `/invoke?capability=tool-document-text`,
   and forwards calls to the MCP server as `tools/call` JSON-RPC requests.

It turns an uploaded document path into plain text. It supports UTF-8 text,
markdown, and PDFs with embedded text. Scanned image PDFs are intentionally not
handled here; that would be a separate OCR capability.

Agents call it through the registry using the same AOA envelope as any other
registered capability:

```json
{
  "trace_id": "...",
  "inputs": { "path": "/data/inbox/cv.pdf" }
}
```

The response uses the standard envelope:

```json
{
  "outputs": {
    "text": "Extracted document text...",
    "media_type": "application/pdf"
  },
  "signals": {
    "path_within_root": true,
    "extracted_text_present": true
  }
}
```

This keeps `tool-filesystem` as low-level file/list access and makes document
interpretation a separate replaceable capability.

## MCP tool provided

| Tool | Arguments | Returns |
|---|---|---|
| `extract_text` | `path` (string) | MCP `content` text block plus `media_type` |

The MCP server owns document interpretation and path safety. The bridge owns
registry registration and AOA envelope compatibility.
