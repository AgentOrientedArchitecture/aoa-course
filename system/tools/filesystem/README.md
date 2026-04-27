# tool-filesystem

A registered capability of `kind: tool`. The container runs two processes:

1. `mcp_server.py` — a Model Context Protocol server speaking JSON-RPC 2.0
   over stdio. Exposes two MCP tools, `read_file` and `list_directory`,
   restricted to a single allowed root.
2. `bridge.py` — a small FastAPI service that registers `tool-filesystem`
   with the system registry, exposes `/invoke?capability=tool-filesystem`,
   and forwards calls to the MCP server as `tools/call` JSON-RPC requests.

Two protocols, side by side, with one explicit boundary between them. The MCP
server is interchangeable: any conforming MCP server with the same tool surface
could replace `mcp_server.py` and the bridge would not notice.

## Why the bridge

Agents in this system find tools through the AOA registry and call them with
the same shape they use for any other capability:

```
POST http://tool-filesystem:7401/invoke?capability=tool-filesystem
Content-Type: application/json

{
  "trace_id": "...",
  "inputs": { "op": "read_file", "path": "/data/inbox/20260427-cv.txt" }
}
```

The bridge translates that into JSON-RPC over stdio:

```
{"jsonrpc": "2.0", "id": 7, "method": "tools/call",
 "params": {"name": "read_file", "arguments": {"path": "..."}}}
```

…reads the response, and returns the standard agent envelope.

## MCP tools provided

| Name | Arguments | Returns |
|---|---|---|
| `read_file`      | `path` (string) | `text` (UTF-8) |
| `list_directory` | `path` (string) | `entries` (array of `{name, kind}`) |

The allowed root is set via the `FS_ROOT` env var (defaults to `/data`). Any
path outside the root returns an MCP error.

## Capability card

`capability-card.yaml` registers this tool with the AOA registry. Note
`kind: tool` and `provenance.model: none` — there is no LLM behind the
capability. The planner does not branch on `kind`; this card is invoked the
same way any AU is invoked.

## Running locally

`docker compose up tool-filesystem` brings the container up on port 7401.
Inside the container, the bridge spawns the MCP server as a long-lived
subprocess and pipes JSON-RPC over its stdin/stdout.
