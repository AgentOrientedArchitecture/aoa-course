# Session 4: card evidence, result review and flow audit

Follow this page for the whole session. You will check what an AU declares,
review the actual CV assessment after a planner restart, and audit the recorded
control. The three core stages are **Agent card check**, **CV fit** and
**Flow audit**. **Graph** and **Ask** remain optional evidence-exploration
utilities.

## Start and seed

Run these commands from the repository root, with Docker running and your
repository-root `.env` configured as described in [setup](../../pre-work/SETUP.md).
You can start Session 4 directly; it does not require a completed EVE workshop.
Stop a previous course session with the normal `down` script first if it is
still running.

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

The launcher starts AGNTCY and publishes the active AUs, including the governance
and evidence evaluators. Every new plan needs current Directory records and
matching approved local contracts. Studio's **AU selection** view shows the
discovery evidence and content IDs. The task sequence is fixed in this session;
AU allocation can still select a general, data or frontend evaluator.

The seed script loads the curated EU AI Act notes without a model call. It then
checks the Annex III employment and Article 14 human-oversight queries. Both
must print a top passage ID and source. Open [Studio](http://localhost:8080) and
use **Studio · all controls** for workflow inputs. On macOS/Linux the seed
script needs `python3`; Windows uses its built-in PowerShell.

Wiki reset is disabled in this session. If evidence is missing, rerun the seed
script. Do not use `session4-reset` as a restart command: it clears teaching
state and removes the general evaluator's added constraint.

## 1. Inspect declared card evidence

Select **Agent card check** and submit:

```text
parser-estate → evaluator-agent-evidence → reporter-agent-evidence
```

On a fresh checkout, the CV evaluator cards lack the required review-before-use
declaration and show red for Article 14. If you have already edited a card, it
may be green; keep that history rather than deleting the declaration to
manufacture a failure.

In the trace and report, confirm that `evaluator-agent-evidence` calls
`tool-wiki-store`. Inspect the exact query, passage ID, source and complete quote.
The wiki supplies inspectable evidence and rationale; the course's deterministic
policy makes the eligibility decision.

Now select **CV fit**, drop or paste a synthetic CV and job description from
Session 1, and submit. For example, use
[`jordan-okafor.txt`](../session-01-cv-fit/cv-examples/jordan-okafor.txt) and
[`senior-data-engineer-fintech.txt`](../session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt).
Use **AU selection** to inspect the accepted evaluator binding. Before its
declaration is added, governance rejects the plan before any application AU
`lookup` or `invoke`; there is no CV assessment draft to review.

If AU allocation itself is held, resolve that first using its recorded reason.
A missing Directory publication or an unavailable decision provider is not the
same outcome as governance rejecting the selected card.

### Add the declaration to the selected card

Use the binding recorded for this run, not an assumed evaluator:

| Accepted evaluator | File under `system/agents/evaluator/capabilities/` |
| --- | --- |
| `evaluator-cv` | `cv/capability-card.yaml` |
| `evaluator-cv-data` | `cv-data/capability-card.yaml` |
| `evaluator-cv-frontend` | `cv-frontend/capability-card.yaml` |

In that file, add this item under `constraints`, matching the existing list's
indentation:

```yaml
- Every verdict is a draft and must be approved by a human reviewer before it informs candidate screening, interview, or employment action.
```

The card hot-reloads into the local registry. Republish and verify the changed
binding before submitting another plan:

macOS or Linux:

```bash
./scripts/directory.sh sync --wait 120
```

Windows Command Prompt:

```bat
scripts\directory.bat sync --wait 120
```

Return to **Studio · all controls**, rerun **Agent card check** and inspect that
card's Article 14 result. Green means
the required declaration was observed. It does not prove that the control works
or that the system is legally compliant. Recheck the accepted binding on each
CV run: if allocation chooses a different evaluator, its own card must carry
the declaration too.

## 2. Recover and review the actual CV result

In **Studio · all controls**, return to **CV fit** with the same inputs. The deterministic
`evaluator-plan-governance` check permits execution only when the selected
card declaration, result-release control and cited Annex III employment and
Article 14 evidence are present. Missing required evidence stops execution.

The application AUs produce a frozen draft. In **Run review**, inspect the
assessment against the actual CV and job description. The state must be
`draft-held`; the trace contains `result-draft` and `result-hold`. Record the
trace ID and displayed `result_digest`. In **Studio · all controls**, expand the
`result-draft` trace record to inspect its `plan_digest` too. Do not approve or
reject yet.

### Restart while the result is held

In another host terminal, restart only the planner. This command is the same
on macOS, Linux and Windows:

```text
docker restart aoa-planner
```

Wait for [planner health](http://localhost:7200/healthz) to respond, then:

1. Refresh Studio and select **AU selection**.
2. Choose **Open a saved case**, then the recorded `cv-fit` trace ID.
3. Open **Run review** and confirm the same result digest. The saved trace in
   **Studio · all controls** also retains the recorded `plan_digest`.
4. Compare the held output with the draft you inspected before the restart.
   Opening the saved case replays evidence; it does not execute the CV AUs again.

The snapshot and ordered events are saved in SQLite on the host. Remembering a
conversation is insufficient here: recovery needs the selected contracts,
eligibility decision, exact draft and review state. The
[case lifecycle diagram](../../ARCHITECTURE.md#session-4-a-result-that-survives-the-process)
shows those boundaries.

### Review that exact draft

Write reviewer notes that explain your decision, then choose:

- **Approve and release**: releases a payload identical to the reviewed draft.
- **Reject and quarantine**: retains the evidence and releases no CV assessment.

Missing notes or a mismatched result digest is rejected. The stored review
refers to this exact output, not permission to generate a different answer later.
Reopen the saved case, or choose **Refresh saved evidence**, to inspect its final
state. To try the other decision, submit a new CV fit run and review its own
draft; you cannot overwrite the earlier review.

The planner commits review and release/quarantine together. Retrying the same
review returns the recorded outcome without a second release; a conflicting
review fails. The optional [persistence reference](DURABLE-CASES.md#check-a-repeated-review-request)
shows how to inspect that API behaviour. No second walkthrough is needed.

Current CV AUs only read, compute and draft. A result hold cannot undo an email,
database write or other external action already performed. If the process stops
during an external invocation, the case is marked interrupted and is not
automatically rerun: its outside effect may be unknown.

## 3. Audit the observed flow

Return to **Studio · all controls**, select **Follow live runs** if a saved case
is still pinned, then run **Flow audit**:

```text
parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

Find the trace you just reviewed. Check evidence for:

- employment eligibility before application invocation;
- application completion before `result-draft` and `result-hold`;
- human review of the exact `result_digest`, with notes;
- approval before release or rejection before quarantine;
- released-payload equality with the frozen draft; and
- a complete Article 14 citation retrieved from the wiki.

The audit reads the JSONL projection of the saved events. By default it includes
only employment traces with the current `human-review-before-release` model.
**Show legacy history** includes preserved older traces and reports their count.
Red legacy rows mean current evidence is absent, not necessarily that the earlier
execution failed. Legacy `hold`, `plan-approval` and `resume` events do not
establish review of the actual result.

## Optional evidence exploration

Use **Graph** to visualise the seeded wiki. Use **Ask** to ask about the EU AI Act
notes and inspect retrieved passages and citations through `tool-wiki-store`.
These support evidence exploration; they are not additional governance stages.

## Review questions

- What changed when the card turned green, and what remained unproven?
- Which evidence allowed the plan to run, and which evidence allowed its result
  to be released?
- Why must review identify the exact output rather than just the plan or model?
- What survived the planner restart? What would happen after an interrupted
  external action instead?
- Why must retrying a review avoid a second release?
- What extra work would establish effective oversight in a real organisation?

The exercise separates declared evidence, implemented controls and observed
events. None alone establishes legal compliance or certification. The regulation
notes are a bounded teaching corpus, and the reviewer ID is a configured
classroom label rather than authenticated identity. Digests detect mismatched
course records; they are not signatures or authorisation credentials.

## Stop

Use `./scripts/down.sh` on macOS/Linux or `scripts\down.bat` on Windows. This
retains the saved cases, wiki, Directory records and your card edits. Keep this
checkout if you want to inspect those cases later; a fresh clone does not copy
its local runtime data.
