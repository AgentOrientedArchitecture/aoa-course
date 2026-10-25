# Persistent cases: implementation reference

The complete learner exercise, including restart and exact-result review, is
in [`WALKTHROUGH.md`](WALKTHROUGH.md). This optional reference explains the
storage boundary and how to check repeated review requests. The
[case lifecycle diagram](../../ARCHITECTURE.md#session-4-a-result-that-survives-the-process)
shows execution, persistence and review together.

## What is saved

The standard course configuration enables persistent cases. The planner stores
SQLite data at `/data/traces/cases.sqlite3` inside its container, mounted from
`system/services/planner/traces/cases.sqlite3` in the checkout.

A saved case contains its intent, resolved plan and card snapshots, governance
result, frozen draft, digests, review and final state. Its ordered events are
stored in the same database. The planner writes JSONL trace files as a
regenerable projection for the flow-audit tools; these are not a separate source
of truth for review.

Two transaction boundaries matter:

- **Draft and hold:** the frozen output, result digest, held state and their
  events are saved together.
- **Review and outcome:** reviewer notes, decision, release or quarantine and
  finish events are committed together. A failed transaction must not leave a
  release without its review.

`plan_digest` identifies the resolved composition. `result_digest` binds the
review to the final output and that plan digest. These truncated hashes are
course integrity checks, not signatures, authenticated identities or proof that
the output is correct.

## What restart means

| State when the planner stops | What happens after restart |
| --- | --- |
| Draft held for review | The same draft and digest can be reopened and reviewed. The CV AUs do not run again. |
| Already released or quarantined | The recorded result and review remain inspectable. An identical review retry returns that outcome. |
| Application execution in progress | The case is marked interrupted. The planner does not automatically repeat an invocation whose external outcome may be unknown. |

`docker restart aoa-planner` leaves the host-mounted database in place. Ordinary
course shutdown also retains it. Deleting the checkout or its runtime data is
not a restart-recovery test. If you cannot find the case, check that you are
using the same checkout and Docker host, then inspect the planner health and
saved-case list.

AGNTCY supplies discovery for new plans. A Directory outage can prevent a new
plan, but it does not erase saved cases or require rediscovery to review an
already-held result. Recovery uses that case's frozen plan and cards.

This local single-planner design is not a Cloudflare Durable Objects deployment
or a general distributed workflow engine. It does not automatically retry
arbitrary side effects or provide exactly-once delivery to external systems.
A release here returns the reviewed payload; it does not execute a downstream
hiring action. Quarantine cannot reverse an AU's earlier external action.

## Check a repeated review request

This is optional API inspection after completing a review in Studio. The UI
hides its review buttons once the decision is recorded, so repeating the
request requires the API. No further model call or CV run is needed.

The API accepts:

```text
POST /api/runs/<trace_id>/review
Content-Type: application/json

{
  "decision": "approve",
  "result_digest": "<the reviewed digest>",
  "review_notes": "<the identical notes>"
}
```

Use the recorded decision, which may instead be `reject`. An identical retry
must use the same decision, digest and notes. The server supplies its configured
reviewer ID. Changing any of those fields conflicts with the recorded review.

For a check that works on either laptop, open the browser's developer console
on `http://localhost:8080`, replace `YOUR_TRACE_ID` below and run this after
reading it. It reads the completed case, retries the recorded review, compares
event counts and submits one deliberately mismatched digest, which should fail:

```javascript
(async () => {
  const id = "YOUR_TRACE_ID";
  const base = `/api/runs/${encodeURIComponent(id)}`;
  const read = async url => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status}: ${url}`);
    return response.json();
  };
  const run = await read(base);
  if (!run.review) throw new Error("Review this draft in Studio first.");
  const evidenceUrl = `/api/course-traces/${encodeURIComponent(id)}`;
  const before = await read(evidenceUrl);
  const body = {
    decision: run.review.decision,
    result_digest: run.review.result_digest,
    review_notes: run.review.review_notes,
  };
  const post = payload => fetch(`${base}/review`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const repeated = await post(body);
  const after = await read(evidenceUrl);
  const conflict = await post({...body, result_digest: "wrong-digest"});
  console.table({
    identical_retry_status: repeated.status,
    events_before: before.records.length,
    events_after: after.records.length,
    mismatched_digest_status: conflict.status,
  });
})();
```

Expected: retry status `200`, unchanged event count and mismatched-digest status
`409`. A different decision or different notes also returns a conflict. The
database records one review and one release/quarantine; retrying does not add
another. With a newly held case, missing notes are rejected and a wrong digest
cannot approve the draft.

## Discussion

- Why is remembering a conversation insufficient to recover this business case?
- What must approval refer to if a model can generate a different answer on
  another run?
- What happens when a client retries approval after losing the response?
- If an AU sends an email before the hold, can quarantine undo it?
- Which responsibilities would a production durable-object or workflow platform
  need to supply: authenticated review, recovery, concurrency, retention,
  backups and external-effect handling?

Card declarations, deterministic policy, review records and legal claims remain
separate. This implementation does not certify compliance or establish
effective oversight. The course regulation corpus also needs its own currency
and applicability review before any production use.
