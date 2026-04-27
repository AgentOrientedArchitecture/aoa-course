# studio

A browser surface at `http://localhost:8080`.

The studio has two roles in this system:

**Observation** — three live panes:

- **Registry.** Every registered capability — id, version, kind, current `skills_hash`. Updates as capabilities register, deregister, or change.
- **Trace.** The currently-running flow as a vertical timeline. Each row shows
  a planner step: capability context, planner proposal, validation/fallback,
  discovery, selection, plan, lookup, invocation, response. Rows expand for
  full payloads.
- **Capability card.** Click a registry row to read its card.

**Intent** — two ways to drive the system:

- A workflow switch for `cv-fit` and `knowledge-query`.
- Text boxes and file drops that forward course inputs to the planner.

The studio drives the demo workflows and shows the trace. For the cut-down
knowledge-management workflow, the grounded answer appears as the final trace
output.

## Internals

The backend (`studio.py`) is a thin FastAPI proxy:

- Subscribes to `registry/stream` and `planner/events` and re-emits them on
  `/events` so the browser only opens one SSE connection.
- Forwards `POST /intent` to the planner.
- Serves `templates/index.html` and `static/`.

The frontend is plain HTML and ES modules — no build step. Look at
`templates/index.html` and `static/app.js` to see what's going on.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET`  | `/` | the studio page |
| `GET`  | `/events` | merged SSE stream of registry + trace events |
| `POST` | `/intent` | proxied to the planner |
| `GET`  | `/healthz` | `{ "ok": true }` |

## Running locally

The studio runs on port 8080. It expects:

```
REGISTRY_URL=http://registry:7100
PLANNER_URL=http://planner:7200
```
