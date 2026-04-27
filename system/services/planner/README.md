# planner

The planner turns an intent into a task breakdown, discovers matching
capabilities, assembles a plan, and then orchestrates capability invocations.

For Session 2 there is one workflow:

```
cv-fit:  parse-cv → evaluate-cv-fit → write-cv-fit-report
```

Session 4 adds a second workflow on the same registry and the same three
agent codebases:

```
knowledge-query:  parse-note → evaluate-question → write-grounded-answer
```

Receiving an intent, the planner:

1. Decides which task breakdown applies.
2. Emits task specs with required inputs, required outputs, and discovery text.
3. Calls registry `/discover` for each task.
4. Selects the top-ranked capability and records the resolved plan.
5. Starts AU capabilities over A2A `message/send`; tool bridges remain direct.
6. Threads outputs into the next task's inputs.
7. Writes every visible step to `traces/<event-id>.jsonl`.

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
{"ts": "...", "trace_id": "...", "step": "breakdown", "tasks": [...]}
{"ts": "...", "trace_id": "...", "step": "discover", "task": "parse-cv", "candidates": [...]}
{"ts": "...", "trace_id": "...", "step": "select", "task": "parse-cv", "capability": "parser-cv"}
{"ts": "...", "trace_id": "...", "step": "plan", "plan": [...]}
{"ts": "...", "trace_id": "...", "step": "lookup", "capability": "parser-cv", "card": {...}}
{"ts": "...", "trace_id": "...", "step": "invoke",   "capability": "parser-cv", "inputs": {...}}
{"ts": "...", "trace_id": "...", "step": "response", "capability": "parser-cv", "outputs": {...}, "signals": {...}}
```

Traces persist under `/data/traces/` in the planner container, mounted from
`system/services/planner/traces/` on the host. They're plain text — open them in
any editor.

## Running locally

The planner runs on port 7200. It expects `REGISTRY_URL=http://registry:7100`.
