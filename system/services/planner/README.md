# planner

The planner turns an intent into a task breakdown, discovers matching
capabilities, assembles a plan, and then orchestrates capability invocations.
By default it uses a hybrid strategy: a small-registry planner model sees the
available AU capability cards and proposes the plan, then deterministic
validation either accepts that plan or falls back to the built-in course plan.

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

1. Loads the current capability cards from the registry.
2. Gives the planner model the intent, compact AU card summaries, and few-shot
   examples.
3. Validates the proposed JSON plan against registry contracts.
4. Falls back to the deterministic course plan if validation fails.
5. Records task breakdown, selected capabilities, and the resolved plan.
6. Starts AU capabilities over A2A `message/send`; tool bridges remain direct.
7. Threads outputs into the next task's inputs.
8. Writes every visible step to `traces/<event-id>.jsonl`.

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
{"ts": "...", "trace_id": "...", "step": "capability-context", "capabilities": [...]}
{"ts": "...", "trace_id": "...", "step": "breakdown", "tasks": [...]}
{"ts": "...", "trace_id": "...", "step": "plan-proposal", "source": "llm", "validation": {...}}
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

`PLANNER_STRATEGY` controls planning:

- `hybrid` — default. Ask the model for a plan, validate, fall back if needed.
- `deterministic` — skip the model and use the built-in course task plan.
- `llm` — require a valid model-generated plan; fail if validation fails.
