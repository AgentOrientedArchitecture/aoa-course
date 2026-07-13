# studio

Studio is the browser surface at `http://localhost:8080`. It submits course
intents, merges registry and planner events, and renders the correlated trace.
Session 4 has exactly three core governance stages: **Agent card check**, **CV
fit**, and **Flow audit**. Optional **Graph** and **Ask** utilities support
evidence exploration; they are not additional governance stages.

## What Studio shows

- **Registry** lists registered capabilities, Agent IDs, lifecycle actors and
  status, version, kind, and current `skills_hash`.
- **Intent Studio** renders intent, capability context, resolved tasks,
  eligibility, application work, held draft, human review, release/quarantine,
  evidence, and final result.
- **Eligibility** displays the deterministic evaluator's decision, selected-card
  evidence, `plan_digest`, and inspectable wiki queries and citations.
- **Result review** displays the actual immutable draft and `result_digest`.
  Approve and Reject remain hidden until the draft exists; reviewer notes are
  required.
- **Details** displays selected cards and raw event payloads.
- **Graph** is an optional Session 4 utility that visualizes the seeded EU AI
  Act wiki.
- **Ask** is an optional Session 4 utility that runs the grounded
  `knowledge-query` workflow and exposes passage citations and tool retrieval.
- **Flow audit history** defaults to employment traces carrying the current
  `human-review-before-release` result-governance model. The **Show legacy
  history** checkbox includes persisted older employment traces and reports the
  included count.
- The wiki remains an explicit governance/evidence knowledge plane visible
  through tool calls, queries, passage IDs, sources, complete quotes, and
  bind-mounted wiki files. Wiki reset is disabled in Session 4 to protect this
  corpus; rerun the Session 4 seed script if evidence is missing.

## Session 4 learner arc

### 1. Agent card check

`parser-estate → evaluator-agent-evidence → reporter-agent-evidence` starts with
`evaluator-cv` Article 14 red. The learner can inspect the visible
`tool-wiki-store` call and the exact query, passage ID, source, and complete
quote. Running CV fit at this point is rejected before application AU `lookup`
or `invoke`.

### 2. CV fit and exact-result review

After the learner adds the required review-before-use constraint to the
`evaluator-cv` card, the registry hot-reloads it. Rerunning Agent card check turns
that declaration green; green means declaration observed only.

CV fit then applies deterministic pre-execution eligibility. The policy decides;
the wiki supplies Annex III employment and Article 14 rationale. Missing either
citeable passage fails closed. If eligible, the application AUs run to a frozen
draft and Studio displays `result-draft` and `result-hold`.

The reviewer must inspect the actual output, add notes, and approve or reject its
exact `result_digest`:

- Approve records `result-review` and `result-release`; the released payload is
  identical to the draft.
- Reject records `result-review` and `result-quarantine`; no employment result is
  released.
- A missing note or different digest is rejected.

Current CV application AUs are read/compute/draft only. Holding a result cannot
reverse side effects already performed by an application AU.

### 3. Flow audit

`parser-estate → evaluator-flow-evidence → reporter-flow-audit` checks observed
eligibility, event order, exact-result review, release or quarantine, and
released-payload equality. Its rationale includes a complete Article 14 wiki
citation.

Older employment traces remain persisted but are hidden by default. Select the
**Show legacy history** checkbox to include them; the panel reports the included
count.
Red legacy rows mean evidence required by the current model is absent, not
necessarily that the old execution failed. Legacy `hold`, `plan-approval`, and
`resume` events do not satisfy result review without `result-draft`,
`result-hold`, and an exact-digest `result-review`.

These are operational course signals, not legal permission, certification, a
legal compliance determination, or proof of effective human oversight.

## Optional evidence exploration

Use **Graph** to inspect the seeded EU AI Act wiki. Use **Ask** to ask questions
about the EU AI Act through the grounded knowledge-query workflow and inspect
its passage citations and tool retrieval. These utilities are not extra stages
in the governance learning arc.

## Course-state limitation

Studio proxies active-run reads and result reviews to planner memory. If the
planner restarts, the trace JSONL remains but an existing held draft can no
longer be reviewed. Submit a new intent and review its new draft. This is not
production persistence or crash-idempotent workflow recovery.

## Internals

The backend (`studio.py`) is a thin FastAPI proxy:

- subscribes to registry and planner event streams, then emits one SSE stream on
  `/events`;
- persists submitted text/files to `system/inbox/` and forwards intent paths to
  the planner;
- proxies active-run reads and exact-result review requests;
- serves `templates/index.html` and `static/`.

The frontend is plain HTML and ES modules with no build step. The responsibility
walk includes eligibility, application AU/tool boundaries, result draft/hold,
human review, release/quarantine, and completion. Compatibility approval routes
may remain, but they submit result-review fields and do not turn legacy plan
approval into result review.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET` | `/` | Studio page |
| `GET` | `/events` | merged registry and planner SSE stream |
| `POST` | `/api/intent` | proxied planner response after input persistence |
| `GET` | `/api/runs/{trace_id}` | active in-memory planner run and held draft |
| `POST` | `/api/runs/{trace_id}/review` | exact-`result_digest` approval/rejection with required notes |
| `POST` | `/api/runs/{trace_id}/approval` | compatibility alias for result review |
| `GET` | `/api/capabilities` | initial registry snapshot |
| `GET` | `/api/capabilities/{capability_id}` | one capability card |
| `GET` | `/api/wiki/graph` | wiki graph projection, including the seeded Session 4 EU AI Act corpus |
| `POST` | `/api/wiki/reset` | clear local wiki state where enabled; disabled in Session 4 |
| `GET` | `/healthz` | `{ "ok": true }` |

## Running locally

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
