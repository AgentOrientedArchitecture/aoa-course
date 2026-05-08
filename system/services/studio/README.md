# studio

A browser surface at `http://localhost:8080`.

The studio has two roles in this system:

**Observation** — three live panes:

- **Registry.** Every registered capability — capability id, Agent ID,
  version, kind, and current `skills_hash`. Updates as capabilities register,
  deregister, or change.
- **Intent Studio.** The centre pane shows the selected intent, supplied
  inputs, lifecycle rail, trace summary, responsibility walk, planner summary,
  task cards, and final result. Raw event payloads remain available behind an
  expandable details section.
- **Details.** Click a registry row to read its card, or click a wiki graph
  node to inspect that node.
- **Wiki graph.** A typed graph view of the Session 4 wiki store: documents,
  concepts, passages, and open questions use different shapes and colours. The
  reset button clears the local wiki store so the ingest demo can be replayed.

**Intent** — two ways to drive the system:

- A mode switch for `cv-fit`, `knowledge-ingest`, `wiki-graph`, and
  `knowledge-query`.
- Text boxes and file drops that forward course inputs to the planner.

The studio drives the demo workflows and shows the trace. The responsibility
walk is the Session 2 teaching surface: it follows intent, planner proposal,
registry selection, AU invocation, inward tool calls, AU responses, signals,
timings, Agent ID, and the final artefact. For the cut-down
knowledge-management system, ingest returns a stored wiki summary and query
returns a grounded answer. The graph mode is read-only and refreshes the wiki
graph without submitting a planner intent.

The visible workflow modes are controlled by `STUDIO_WORKFLOWS`, a comma
separated list of `cv-fit`, `knowledge-ingest`, `wiki-graph`, and
`knowledge-query`. The Session 2 compose override sets it to `cv-fit`; Session
4 uses all modes.

## Internals

The backend (`studio.py`) is a thin FastAPI proxy:

- Subscribes to `registry/stream` and `planner/events` and re-emits them on
  `/events` so the browser only opens one SSE connection.
- Forwards `POST /intent` to the planner.
- Serves `templates/index.html` and `static/`.

The frontend is plain HTML and ES modules — no build step. Look at
`templates/index.html` and `static/app.js` to see what's going on.

The graph view is intentionally direct: Studio asks `tool-wiki-store` for a
read-only graph projection and for demo reset. Those actions are UI controls
over wiki state, not AU workflows, so the AU responsibility trace remains
focused on ingest and query.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET`  | `/` | the studio page |
| `GET`  | `/events` | merged SSE stream of registry + trace events |
| `POST` | `/intent` | proxied to the planner |
| `GET`  | `/api/wiki/graph` | read-only wiki graph projection |
| `POST` | `/api/wiki/reset` | clear the local wiki store for replay |
| `GET`  | `/healthz` | `{ "ok": true }` |

## Running locally

The studio runs on port 8080. It expects:

```
REGISTRY_URL=http://registry:7100
PLANNER_URL=http://planner:7200
STUDIO_WORKFLOWS=cv-fit,knowledge-ingest,wiki-graph,knowledge-query
```
