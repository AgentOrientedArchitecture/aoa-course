# Session 4 walkthrough — card check, held result, and flow audit

Session 4 has exactly three core governance learning stages: **Agent card
check**, **CV fit**, and **Flow audit**. Studio also provides optional **Graph**
and **Ask** evidence-exploration utilities; they are not extra stages.

## Start and seed

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

The seed script loads the curated EU AI Act corpus, then verifies the wiki with
searches for `Annex III employment` and `Article 14 human oversight`. Open
`http://localhost:8080` when both searches print a top passage ID and source.
Wiki reset is disabled in Session 4 to protect this governance corpus. If its
evidence is missing, rerun the seed script.

## 1. Start red: inspect the Agent card

Run **Agent card check**:

```text
parser-estate → evaluator-agent-evidence → reporter-agent-evidence
```

`evaluator-cv` starts red for Article 14. In the trace and report, confirm that
`evaluator-agent-evidence` visibly calls `tool-wiki-store` and shows the exact
query, passage ID, source, and complete verbatim quote.

The wiki is an explicit, inspectable governance/evidence knowledge plane. The
deterministic policy makes decisions; the wiki supplies cited rationale and
evidence rather than uncited model knowledge.

Optional: run **CV fit** now. Employment eligibility is rejected before any
application AU `lookup` or `invoke` because the selected `evaluator-cv` card is
missing the required declaration.

## 2. Declare review, then review the actual result

In
`system/agents/evaluator/capabilities/cv/capability-card.yaml`, add exactly this
item under `constraints`:

```yaml
- Every verdict is a draft and must be approved by a human reviewer before it informs candidate screening, interview, or employment action.
```

Watch the registry hot-reload, then rerun **Agent card check**. Green means only
that the declaration was observed. It does not prove implementation,
effectiveness, legal compliance, or legal permission.

Run **CV fit** again. The deterministic eligibility check now proceeds only if
the card declaration and result-release control are present and the wiki has
citeable Annex III employment and Article 14 passages. Missing either passage
fails employment eligibility closed.

The application AUs then run and produce an immutable held draft with a
`result_digest`. Inspect the actual draft, add reviewer notes, and approve or
reject that exact digest:

- **Approve** releases a payload identical to the reviewed draft.
- **Reject** quarantines the draft and releases no employment result.
- Missing notes or a different digest is rejected.

Current CV application AUs are read/compute/draft only. A result hold cannot
undo an email, database write, external action, or other side effect that has
already happened.

## 3. Audit the observed flow

After approving or rejecting, run **Flow audit**:

```text
parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

Check the evidence for:

- employment eligibility before application invocation;
- application completion before `result-draft` and `result-hold`;
- human review of the exact `result_digest`, with notes;
- approval before release or rejection before quarantine;
- released-payload equality with the immutable draft; and
- a complete Article 14 citation retrieved from the wiki.

By default, the Flow audit panel includes only employment traces carrying the
current `human-review-before-release` result-governance model. Older employment
traces remain persisted but are hidden. Select the **Show legacy history**
checkbox to include them; the panel reports the included count. Red legacy
rows mean evidence required by the current model is absent, not necessarily
that the older
execution failed. Legacy `hold`, `plan-approval`, and `resume` events remain
parseable, but they do not satisfy exact-result review.

## Optional evidence exploration

Use **Graph** to visualize the seeded EU AI Act wiki. Use **Ask** to run the
grounded knowledge-query workflow, ask about the EU AI Act, and inspect passage
citations and tool retrieval. These utilities support evidence exploration; they
are not governance stages.

Trace JSONL persists on disk, while active held drafts and locks live in planner
memory. If the planner restarts, submit a new CV-fit intent and review its new
draft. This course control is not production persistence or proof of effective
human oversight.
