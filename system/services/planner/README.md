# planner

The planner turns an intent into a concrete plan, resolves registered
capabilities, checks pre-execution eligibility, orchestrates application AUs,
and controls release of the completed result. It owns the correlated JSONL
trace.

The base system uses hybrid model planning with deterministic validation and
fallback. Sessions 3 and 4 set `PLANNER_STRATEGY=deterministic`, so their enabled
workflows use fixed course plans. This service also implements orchestration
and result review; it is not a separately registered Planner AU.

## Revised allocation

With `ALLOCATION_MODE=decision`, the service obtains the registry's `/list`,
filters cards against a task's reference contract and calls the decision
service only when multiple eligible AUs remain. A single eligible AU requires
no model choice. No fit, low probability or a provider error stops allocation
before application execution. `validate_composition` checks required tasks,
input/output compatibility and evidence dependencies before accepted bindings
are recorded. See the [selection diagram](../../../course/ARCHITECTURE.md#session-1-proposing-work-and-choosing-an-au).

Revised Sessions 3–4 set `DISCOVERY_BACKEND=agntcy`. Before planning/allocation,
the service retrieves actual Directory search/pull results from the course
`directory-bridge`, then matches OASF binding hashes and A2A modules against
current approved local AU cards. The registry list is the adoption authority,
not a substitute discovery result. Missing/stale publications or unavailable
Directory stop new runs with no AU invocation and no local discovery fallback.
Trace events retain content IDs, accepted/excluded records and missing bindings.
Tools remain local; they are not AU candidates. Sessions 1–2 and the original
profile retain local discovery. Held-result review requires no new discovery.

Task planning and AU allocation are separate settings: fixed Session 3/4 plans
can still receive decision-model allocation. The workflow catalogue and
reference contracts bound what the model can propose. Execution is sequential.
The workflow diagrams below use the original general CV evaluator; the revised
allocator may select `evaluator-cv-data` or `evaluator-cv-frontend` for that task.

## Workflows

```text
cv-fit:             parser-cv → evaluator-cv → reporter-cv-fit
cv-fit-interview:   parser-cv → evaluator-cv → interviewer-questions
knowledge-ingest:   parser-notes → evaluator-promote → reporter-ingest-summary
knowledge-query:    parser-query → evaluator-wiki-query → reporter-answer
agent-card-check:   parser-estate → evaluator-agent-evidence → reporter-agent-evidence
flow-audit:         parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

## Session 4 Studio surface

Session 4 has exactly three core governance stages: Agent card check, CV fit,
and Flow audit. Studio also exposes optional Graph and Ask evidence-exploration
utilities. Graph visualizes the seeded EU AI Act wiki. Ask invokes the grounded
`knowledge-query` workflow so learners can inspect passage citations and tool
retrieval. Neither utility is another governance stage. Wiki reset is disabled
in Session 4 to protect the governance corpus; rerun the Session 4 seed script
if evidence is missing.

## Session 4 lifecycle

For each Session 4 intent, the planner:

1. Selects the deterministic task plan and resolves each task to a concrete
   capability card.
2. Records the plan, its `plan_digest`, and a release policy. Employment-shaped
   plans use `human-review-before-release`.
3. Invokes `evaluator-plan-governance` before any application AU `lookup` or
   `invoke`. Its deterministic policy checks employment context, the selected
   evaluator's review-before-use declaration, and the result-release control.
   `tool-wiki-store` supplies inspectable Annex III and Article 14 rationale.
4. Fails closed with `reject` if the employment declaration, release control,
   Annex III passage, or Article 14 passage is missing. Rejected plans run no
   application AU. Eligible plans record `governance-release` and proceed.
5. Runs the application AUs. For current CV fit these are read/compute/draft
   operations only; result hold cannot undo an external side effect.
6. Freezes the final AU output, computes `result_digest`, and records
   `result-draft` plus `result-hold`. The draft is not released.
7. Accepts a human `approve` or `reject` only with reviewer notes and the exact
   held `result_digest`. Approval records `result-review`, releases the identical
   draft in `result-release`, and finishes `released`. Rejection records
   `result-review`, then `result-quarantine`, and finishes `quarantined` without
   a released result.

```mermaid
flowchart TD
    A[Resolve plan and cards] --> B[Deterministic eligibility]
    B -->|reject| C[Stop before application lookup]
    B -->|proceed| D[Run read compute draft AUs]
    D --> E[Freeze output and hold result digest]
    E --> F[Human reviews actual draft and adds notes]
    F -->|approve exact digest| G[Release identical draft]
    F -->|reject exact digest| H[Quarantine draft]
```

The wiki is an explicit governance/evidence knowledge plane, not the decision
engine. Deterministic policy makes the eligibility decision; wiki searches make
its Annex III and Article 14 rationale citeable and inspectable. Missing either
employment-governance passage causes a closed rejection.

## Digests

`plan_digest` is the first 16 hexadecimal characters of SHA-256 over canonical
JSON containing the workflow, intent, release policy, resolved tasks/dataflow,
and selected-card governance snapshots. It correlates eligibility with the
resolved composition.

`result_digest` is the first 16 hexadecimal characters of SHA-256 over canonical
JSON containing `plan_digest` and the frozen final outputs. Human review binds
to this digest because the reviewer must see and decide on the actual result,
not merely the plan that produced it.

A wrong result digest receives HTTP `409`. Before release, the planner recomputes
the digest over the frozen draft; approval then copies that same payload to the
released outputs.

These digests are course integrity and correlation mechanisms, not signatures
or authorization credentials.

## Held-run state

Trace files persist under `/data/traces/`, bind-mounted to
`system/services/planner/traces/`. The persistence mode matters:

- Original profile, `DURABLE_CASES=false`: active runs, drafts and locks live in
  memory. Restart leaves JSONL evidence but requires a new intent for review.
- Revised profile, `DURABLE_CASES=true`: `case_store.py` persists snapshots and
  ordered events in SQLite at `CASE_DB_PATH`. Held drafts restore after restart.
  Draft/hold and review/release-or-quarantine transactions are atomic. Identical
  review retries return the stored outcome; conflicts receive HTTP 409. JSONL
  is a projection regenerated for existing audit consumers.

On startup, previously running/preparing cases become `interrupted` and are not
automatically rerun. Request locks are still in-process, and the course runs one
planner process. This is not a distributed workflow service or an exactly-once
guarantee for external effects. See the [case diagram and exercise](../../../course/sessions/session-04-compliance/DURABLE-CASES.md).

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/intent` | `{ "kind": "...", "use_context": {...}, "inputs": {...} }` | trace ID, workflow, status, and outputs or held draft metadata |
| `GET` | `/runs` | — | available run snapshots and whether durable cases are enabled |
| `GET` | `/runs/{trace_id}` | — | run, draft, digest, review and released outputs; includes restored cases in durable mode |
| `POST` | `/runs/{trace_id}/review` | `decision`, exact `result_digest`, required `review_notes` | released or quarantined run snapshot |
| `POST` | `/runs/{trace_id}/approval` | compatibility alias for `/review` using the same result-review body | released or quarantined run snapshot |
| `POST` | `/trace-events` | AU/tool trace record | `{ "ok": true }` |
| `GET` | `/events` | — | SSE stream of trace records |
| `GET` | `/traces` | — | recent persisted trace IDs |
| `GET` | `/traces/{id}` | — | persisted trace as a JSON array |
| `GET` | `/healthz` | — | workflows and planner strategy |

## Trace format

An eligible, approved employment result records this order:

```json
{"step":"plan","plan_digest":"...","release_policy":{"mode":"human-review-before-release"}}
{"step":"governance-invoke","capability":"evaluator-plan-governance","plan_digest":"..."}
{"step":"plan-governance","decision":"proceed","plan_digest":"..."}
{"step":"governance-release","decision":"proceed","plan_digest":"..."}
{"step":"lookup","capability":"parser-cv","card":{}}
{"step":"invoke","capability":"parser-cv","inputs":{}}
{"step":"response","capability":"reporter-cv-fit","outputs":{}}
{"step":"result-draft","plan_digest":"...","result_digest":"...","outputs":{}}
{"step":"result-hold","result_digest":"...","review_required":true}
{"step":"result-review","decision":"approve","result_digest":"...","review_notes":"..."}
{"step":"result-release","result_digest":"...","outputs":{}}
{"step":"finish","outputs":{}}
```

A rejected review records `result-quarantine` instead of `result-release` and
emits no result payload. An ineligible employment plan records `plan-rejected`
before any application `lookup` or `invoke`.

Flow audit reconstructs eligibility, event order, exact-result review,
release/quarantine, and released-payload equality from these records. Its Studio
panel defaults to employment traces carrying the current
`human-review-before-release` result-governance model. Older employment traces
remain persisted but hidden; the **Show legacy history** checkbox includes them
and reports the included count. Red legacy rows mean current evidence is absent, not
necessarily that the old execution failed. Legacy `hold`, `plan-approval`, and
`resume` events remain parseable, but never count as `result-review` evidence.

## Planning configuration

The planner runs on port `7200` and expects
`REGISTRY_URL=http://registry:7100`.

`PLANNER_STRATEGY` controls plan construction:

- `hybrid` — ask the model, validate, and fall back if needed.
- `deterministic` — skip the planning model and use the built-in course plan. Sessions 3 and 4
  use this strategy.
- `llm` — require a valid model-generated plan; fail if validation fails.

`PLAN_GOVERNANCE_CAPABILITY` enables the pre-execution eligibility check. The
configured card must be an approved AU. If the evaluator is unavailable or its
output is invalid, employment execution fails closed with rejection.
