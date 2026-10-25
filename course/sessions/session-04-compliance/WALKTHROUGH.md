# Session 4: card evidence, result review and flow audit

The lesson is to make governance part of the AOA platform. The wiki supplies
cited policy evidence; governance AUs check the declared contract and recorded
behaviour; the planner holds the actual assessment until a human reviews it.

Follow three stages on this page: **Agent card check → CV fit → Flow audit**.
This session uses just **`evaluator-cv`** for CV assessment, so there is one card
to edit. The specialist-selection exercise remains in Sessions 1–3. Restart
recovery, **Graph** and **Ask** are optional extensions after the core exercise.

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
discovery evidence and content IDs. The task sequence and general CV evaluator
are fixed for this governance exercise. Contract validation still runs; there
is no decision-model call when only one compatible AU is available.

The seed script loads the curated EU AI Act notes without a model call. It then
checks the Annex III employment and Article 14 human-oversight queries. Both
must print a top passage ID and source. Open [Studio](http://localhost:8080) and
use **Studio · all controls** for workflow inputs. On macOS/Linux the seed
script needs `python3`; Windows uses its built-in PowerShell.

Wiki reset is disabled in this session. If evidence is missing, rerun the seed
script. Do not use `session4-reset` as a restart command: it clears teaching
state and removes the general evaluator's added constraint.

## 1. Inspect declared card evidence

Select **1. Agent card check** and click **Run agent card check**. Its workflow is:

```text
parser-estate → evaluator-agent-evidence → reporter-agent-evidence
```

Find **`evaluator-cv`** in the report. On a fresh checkout, its card lacks the
required review-before-use declaration and shows red for Article 14. If you
have already edited the card, it may be green; keep that history rather than
deleting the declaration to
manufacture a failure.

In the trace and report, confirm that `evaluator-agent-evidence` calls
`tool-wiki-store`. Inspect the exact query, passage ID, source and complete quote.
The wiki supplies inspectable evidence and rationale; the course's deterministic
policy makes the eligibility decision.

Now select **CV fit**, drop or paste a synthetic CV and job description from
Session 1, and submit. For example, use
[`jordan-okafor.txt`](../session-01-cv-fit/cv-examples/jordan-okafor.txt) and
[`senior-data-engineer-fintech.txt`](../session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt).
Before the declaration is added, the platform rejects this CV fit run. Inspect
the reason: `evaluator-cv` has not declared review before employment use. The
trace shows the governance check and its wiki evidence, with no CV assessment
AU invoked and no draft produced. This is the first enforcement point.

If the error is about missing Directory records, run Directory sync and retry.
If the wiki evidence is missing, rerun the seed script. Those setup problems
are different from the intended rejection for a missing card declaration.

### Add the declaration to one file

In your text editor, open this file in your checked-out repository:

```text
system/agents/evaluator/capabilities/cv/capability-card.yaml
```

Under the existing `constraints:` list, add the final line shown below. Keep
all existing entries and use **two spaces before the dash**. Save the file.
Use the sentence as written: the teaching policy checks for this explicit
review-before-use declaration.

```yaml
constraints:
  - The output is a single JSON object.
  - scores is an object whose values are integers from 1 to 5.
  - verdict is one of "strong", "fit", "weak", "no".
  - strengths and gaps are arrays of short strings.
  - rationale is one paragraph summarising the verdict.
  - Every verdict is a draft and must be approved by a human reviewer before it informs candidate screening, interview, or employment action.
```

In Studio, open **Capability cards**, select **evaluator-cv** and wait until
**Declared constraints** includes the new sentence. The file reloads
automatically; there is no container restart. Then publish the changed contract
from the repository root:

macOS or Linux:

```bash
./scripts/directory.sh sync --wait 120
```

Windows Command Prompt:

```bat
scripts\directory.bat sync --wait 120
```

Return to **Studio · all controls** and rerun **Agent card check**. That card's
Article 14 declaration should now be green. This means the declaration is
present; it does not prove that review happens. The planner already implements
the hold-and-review control, which you will exercise next.

The earlier rejected run remains as evidence. Submit a new run below.

## 2. Produce and review the CV assessment

In **Studio · all controls**, return to **CV fit** with the same inputs. The deterministic
`evaluator-plan-governance` check permits execution only when the selected
card declaration, result-release control and cited Annex III employment and
Article 14 evidence are present. Missing required evidence stops execution.

Open **Run review** and compare the assessment with the actual CV and job
description. The state must be `draft-held`: the AUs have produced an assessment,
but the platform has not released it. This is the second enforcement point.
Studio displays the result digest and submits it with your review automatically;
you do not need to copy a hash or use the API.

For the Jordan example, check three concrete points before accepting a report:

- The CV explicitly mentions the on-call rota. Has that evidence survived parsing?
- NHS experience and GDPR/DPA practice are **nice to have** in this job description.
  Has the assessment incorrectly treated them as essential?
- Mentoring is stated, but formal team leadership and five years of regulated
  work need verification. Does the report preserve those uncertainties?

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
is still pinned, then select **3. Flow audit** and click **Run flow audit**:

```text
parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

Find the trace you just reviewed. The earlier blocked run remains in the
history; it did not produce an assessment to approve. Check the reviewed run for:

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

## Optional: prove that a held result survives restart

Submit a fresh CV fit run and leave it at `draft-held`. Record its trace ID
and displayed `result_digest` before approving or rejecting it.

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

Continue with the review controls above. The same held draft can be approved or
rejected after recovery. The optional [persistence reference](DURABLE-CASES.md)
explains storage, plan/result digests and repeated review requests in more detail.

## Optional evidence exploration

Use **Graph** to visualise the seeded wiki. Use **Ask** to ask about the EU AI Act
notes and inspect retrieved passages and citations through `tool-wiki-store`.
These support evidence exploration; they are not additional governance stages.

## Review questions

- What changed when the card turned green, and what remained unproven?
- Which evidence allowed the plan to run, and which evidence allowed its result
  to be released?
- Why must review identify the exact output rather than just the plan or model?
- If you tried restart recovery, what survived? What would happen after an
  interrupted external action instead?
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
