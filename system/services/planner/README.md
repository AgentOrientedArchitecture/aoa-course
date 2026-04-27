# planner

The planner turns an intent into a sequence of capability invocations.

For Session 2 there is one workflow:

```
cv-fit:  parser-cv → evaluator-cv → reporter-cv-fit
```

Session 4 adds a second workflow on the same registry and the same three
agent codebases:

```
knowledge-query:  parser-notes → evaluator-query → reporter-answer
```

Receiving an intent, the planner:

1. Decides which workflow runs (small mapping today, registry-aware tomorrow).
2. Asks the registry for each capability in turn.
3. POSTs to its `endpoint` and waits for the response.
4. Threads outputs into the next step's inputs.
5. Writes every request and response to `traces/<event-id>.jsonl`.

The studio subscribes to `/events` and renders the running trace live.

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/intent` | `{ "kind": "...", "inputs": {...} }` | `{ "trace_id": "...", "outputs": {...} }` |
| `GET`  | `/events` | — | SSE stream of trace lines |
| `GET`  | `/traces` | — | list of recent trace ids |
| `GET`  | `/traces/{id}` | — | trace as a JSON array |
| `GET`  | `/healthz` | — | `{ "ok": true }` |

## Trace format

Each trace is a JSON-lines file. One record per planner-visible step:

```json
{"ts": "...", "trace_id": "...", "step": "lookup", "capability": "parser-cv", "card": {...}}
{"ts": "...", "trace_id": "...", "step": "invoke",   "capability": "parser-cv", "inputs": {...}}
{"ts": "...", "trace_id": "...", "step": "response", "capability": "parser-cv", "outputs": {...}, "signals": {...}}
```

Traces persist under `/data/traces/` in the planner container, mounted from
`system/services/planner/traces/` on the host. They're plain text — open them in
any editor.

## Running locally

The planner runs on port 7200. It expects `REGISTRY_URL=http://registry:7100`.
