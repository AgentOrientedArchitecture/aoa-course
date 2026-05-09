# registry

A small HTTP service that holds the set of registered capabilities.

Agents and tools `POST /register` on boot. The studio subscribes to `/stream`
to keep its registry pane live. The planner calls `POST /discover` to rank
capabilities for a task, then uses the selected card to orchestrate work.
`GET /find?id=<id>` remains available for direct lookup and inspection.

On registration the registry also stamps a lightweight governance lifecycle
onto the card. The course uses seeded actor identities such as
`urn:aoa:role:platform-team-publisher` and
`urn:aoa:role:risk-curator-approver` so Studio can show who published and
approved each card without adding a full approval workflow.

The state of the registry is a single file, `cards.json`, in the volume mounted
at `/data`. The service watches that file: if you edit it by hand (say, to bump
a version number), the change is broadcast to subscribers. Most of the time
you won't touch it — agents push their cards in.

## Endpoints

| Method | Path | Body / params | Returns |
|---|---|---|---|
| `POST` | `/register` | capability card | `{ "ok": true }` |
| `POST` | `/update`   | capability card | `{ "ok": true }` |
| `POST` | `/discover` | task query | ranked capability candidates |
| `GET`  | `/find`     | `?id=<id>` | the card, or 404 |
| `GET`  | `/list`     | — | `{ "capabilities": [...] }` |
| `GET`  | `/stream`   | — | SSE: `{"event": "...", "card": ...}` including `card_published`, `card_approved`, and `card_deprecated` lifecycle events |
| `GET`  | `/healthz`  | — | `{ "ok": true }` |

## Running locally

The registry runs in the `registry` service of `docker-compose.yml`. Listens on
port 7100. `cards.json` is persisted at `/data/cards.json` inside the container,
backed by the named Docker volume `registry-data`.

Governance demo actors are configured with:

```
REGISTRY_PUBLISHER_AGENT_ID=urn:aoa:role:platform-team-publisher
REGISTRY_APPROVER_AGENT_ID=urn:aoa:role:risk-curator-approver
REGISTRY_REVIEWER_AGENT_ID=urn:aoa:role:registry-reviewer
REGISTRY_DEFAULT_LIFECYCLE_STATUS=approved
```
