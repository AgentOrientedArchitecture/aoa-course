# studio

Studio is the browser surface at `http://localhost:8080`. It submits course
intents, merges registry and planner event streams, and renders the correlated
trace. Session 4 exposes exactly Agent card check, CV fit, and Flow audit, and
uses Studio as the human interaction point for a held CV-fit plan.

## Observation

- **Registry** lists registered capability ID, Agent ID, lifecycle actors and
  status, version, kind, and current `skills_hash`. It also shows recent card
  lifecycle events.
- **Intent Studio** renders intent, capability context, resolved tasks, **Plan
  governance**, the responsibility walk, evidence, and the final result.
- **Plan governance** displays the deterministic evaluator's Markdown report,
  decision, and plan digest. For a held CV-fit run it shows **Approve this plan
  and run** and states that execution is paused before the first application AU.
- **Details** displays a selected capability card, governance actor, or wiki
  graph node.
- **Wiki graph** projects the Session 2 store as documents, concepts, passages,
  and open questions. Graph inspection and reset are direct UI controls, not AU
  workflows.

Raw event payloads remain available in expandable details.

## Session 4 behavior

The Session 4 mode switch exposes exactly:

```text
agent-card-check,cv-fit,flow-audit
```

### Agent card check

Agent card check runs
`parser-estate → evaluator-agent-evidence → reporter-agent-evidence`. It shows
current declared card evidence and verbatim regulation citations retrieved from
the wiki store. The wiki remains a hidden knowledge source, not a Session 4
mode.

After the learner adds the Article 14 oversight constraint to the
`evaluator-cv` capability card, the registry pane shows the card hot reload.
Rerunning Agent card check shows the declaration and evidence improve. Green
means declared evidence only, not legal compliance or an effective control.

### CV fit

Studio sends a declared employment use context with the input paths. After the
planner resolves the concrete plan, `evaluator-plan-governance` returns
`require-human-approval`. Studio renders the report and digest; no application
AU has been looked up or invoked. Clicking **Approve this plan and run** posts
approval for that exact digest. The same trace records `plan-approval`,
`resume`, application execution, and the result.

The planner rejects a different or stale digest with HTTP `409`; Studio displays
the returned error and does not release the held plan.

### Flow audit

Flow audit runs
`parser-estate → evaluator-flow-evidence → reporter-flow-audit` after execution.
It reports only observed evidence for the gate, exact digest, event order,
resume, and completion. It does not treat an Agent card declaration as proof
that execution occurred.

Agent card check and Flow audit auto-proceed under the deterministic course
policy. Card evidence, operational release, and execution evidence are distinct.
None establishes legal permission, legal compliance or certification, or proof
of effective human oversight.

## Course-state limitation

Studio proxies active-run reads and approvals to planner memory. If the planner
restarts, an existing held trace remains as JSONL evidence but is no longer an
active run that Studio can approve or resume. Submit a new intent and review its
new digest. This is not production persistence or crash-idempotent workflow
recovery.

## Internals

The backend (`studio.py`) is a thin FastAPI proxy:

- subscribes to `registry/stream` and `planner/events`, then re-emits one SSE
  stream on `/events`;
- persists submitted text/files to `system/inbox/` and forwards intent paths to
  the planner;
- proxies active-run reads and exact-digest approval requests;
- serves `templates/index.html` and `static/`.

The frontend is plain HTML and ES modules with no build step. The responsibility
walk includes governance invocation/decision, hold, approval, resume,
automatic release, application AU/tool boundaries, and completion. The backend
may retain additional compatibility routes, but Session 4 presents only its
three learner-facing modes.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET` | `/` | Studio page |
| `GET` | `/events` | merged registry and planner SSE stream |
| `POST` | `/api/intent` | proxied planner result after input persistence |
| `GET` | `/api/runs/{trace_id}` | active in-memory planner run |
| `POST` | `/api/runs/{trace_id}/approval` | proxied exact-digest approval/rejection result |
| `GET` | `/api/capabilities` | initial registry snapshot |
| `GET` | `/api/capabilities/{capability_id}` | one capability card |
| `GET` | `/api/wiki/graph` | read-only wiki graph projection |
| `POST` | `/api/wiki/reset` | clear local wiki state for replay |
| `GET` | `/healthz` | `{ "ok": true }` |

## Running locally

Studio runs on port `8080` and expects:

```text
REGISTRY_URL=http://registry:7100
PLANNER_URL=http://planner:7200
STUDIO_WORKFLOWS=agent-card-check,cv-fit,flow-audit
```

Start and seed Session 4 from the repository root.

macOS or Linux:

```bash
./scripts/session4-up.sh
./scripts/session4-seed.sh
```

Windows Command Prompt:

```bat
scripts\session4-up.bat
scripts\session4-seed.bat
```
