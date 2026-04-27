# registry

A small HTTP service that holds the set of registered capabilities.

Agents and tools `POST /register` on boot. The studio subscribes to `/stream`
to keep its registry pane live. The planner calls `GET /find?id=<id>` to look
a capability up by id.

The state of the registry is a single file, `cards.json`, in the volume mounted
at `/data`. The service watches that file: if you edit it by hand (say, to bump
a version number), the change is broadcast to subscribers. Most of the time
you won't touch it — agents push their cards in.

## Endpoints

| Method | Path | Body / params | Returns |
|---|---|---|---|
| `POST` | `/register` | capability card | `{ "ok": true }` |
| `POST` | `/update`   | capability card | `{ "ok": true }` |
| `GET`  | `/find`     | `?id=<id>` | the card, or 404 |
| `GET`  | `/list`     | — | `{ "capabilities": [...] }` |
| `GET`  | `/stream`   | — | SSE: `{"event": "...", "card": ...}` |
| `GET`  | `/healthz`  | — | `{ "ok": true }` |

## Running locally

The registry runs in the `registry` service of `docker-compose.yml`. Listens on
port 7100. `cards.json` is persisted at `/data/cards.json` inside the container,
mounted from `system/services/registry/data/` on the host.
