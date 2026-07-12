# Session 4 - Card evidence, plan release, and flow audit

Session 4 has three learner-facing stages, exposed in Studio as exactly
**Agent card check**, **CV fit**, and **Flow audit**:

1. **Agent card check** inspects what Agent cards declare and cites the relevant
   regulation text.
2. **CV fit** demonstrates operational release of one resolved employment
   composition.
3. **Flow audit** inspects post-execution evidence for what actually happened.

The wiki store remains hidden in Session 4. It supplies verbatim regulation
citations to the evidence evaluator; it is not a learner-facing Studio mode.

## Keep the claims separate

- **Card evidence** is a public declaration in a capability card. It does not
  prove that the declared control is implemented or effective.
- **Operational plan release** decides whether this course planner may execute
  one exact resolved plan and digest now.
- **Execution evidence** records whether the gate, digest, event order, resume,
  and completion were observed on a trace after execution.
- **Legal compliance and effective oversight** require contextual legal and
  organisational assessment outside this course system.

Green in Agent card check means *declared evidence is present*. It never means
legal compliance, certification, legal permission, or effective human
oversight. A recorded plan approval is likewise a course control event, not
proof that a real human-oversight process is effective.

## Start and seed Session 4

Session 4 runs the three Studio stages above. Its planner strategy is
`deterministic`, so each workflow uses a fixed course plan before governance
evaluates the resolved composition.

On macOS or Linux:

```bash
./scripts/session4-up.sh
./scripts/session4-seed.sh
```

On Windows Command Prompt:

```bat
scripts\session4-up.bat
scripts\session4-seed.bat
```

The seed command loads the curated EU AI Act corpus through the same
`write_ingest` contract used by the wiki workflow. In Session 4 that wiki store
is a hidden knowledge source for verbatim citations. Then open
`http://localhost:8080`.

## Main learner arc

1. Run **Agent card check**:
   `parser-estate → evaluator-agent-evidence → reporter-agent-evidence`.
2. Inspect the `evaluator-cv` Article 14 evidence and its verbatim wiki citation.
3. Under `constraints` in
   `system/agents/evaluator/capabilities/cv/capability-card.yaml`, add:

   ```yaml
   - A human reviewer must approve every verdict before it informs candidate screening, interview, or employment action.
   ```

4. Watch the card hot-reload in the registry, rerun **Agent card check**, and
   observe the declaration and evidence improve. Green means declared evidence
   only.
5. Run **CV fit** and inspect the resolved employment composition. Confirm that
   `evaluator-plan-governance` returns `require-human-approval` and holds the
   plan before any application `lookup` or `invoke`.
6. Click **Approve this plan and run**. Approval must match the held digest; the
   same trace records `plan-approval`, `resume`, application work, and the final
   result. A wrong digest, or a selected card that changes while the plan is
   held, receives HTTP `409`; submit a new intent and review its new digest.
7. Run **Flow audit**:
   `parser-estate → evaluator-flow-evidence → reporter-flow-audit`. Inspect only
   post-execution evidence for the gate, exact digest, event order, resume, and
   completion.

## What the plan digest binds

The planner derives a 16-character digest from a canonical representation of
the workflow, full intent, resolved tasks and dataflow, and each selected card's
governance snapshot: identity/version, purpose, input/output contracts,
constraints, evaluation signals, lifecycle, provenance, and endpoints. Approval
is therefore bound to the displayed resolved plan rather than to a workflow
name in the abstract.

The digest is a course integrity and correlation mechanism. It is not a digital
signature, authorization token, or production approval protocol.

## Three workflow responsibilities

### Agent card check

```text
parser-estate → evaluator-agent-evidence → reporter-agent-evidence
```

`parser-estate` reads the current card inventory through `tool-filesystem`.
`evaluator-agent-evidence` evaluates declared evidence and retrieves complete,
verbatim regulation passages from the wiki store. `reporter-agent-evidence`
renders those declarations and citations. A silent corpus produces
`unknown`/`corpus_silent` rather than a legal paraphrase from model memory.

Editing the `evaluator-cv` card changes this surface because the public
declaration changed. It does not release a CV-fit plan or prove that a human
reviewer can intervene effectively.

### CV fit operational release

After resolving the concrete CV-fit plan, the planner computes its digest and
invokes `evaluator-plan-governance` before any application-card `lookup` or
`invoke`. The declared employment use context returns
`require-human-approval`, so no `parser-cv`, `evaluator-cv`, or
`reporter-cv-fit` application AU runs while the plan is held.

**Approve this plan and run** submits the exact held digest. Accepted approval
records `plan-approval` and `resume` on the same trace before the frozen plan
executes. Editing the `evaluator-cv` card is not approval for this composition,
and approving this composition is not approval of the card.

### Flow audit

```text
parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

`parser-estate` reconstructs observed planner JSONL records.
`evaluator-flow-evidence` evaluates only post-execution evidence for the gate,
exact digest, event order, resume, and completion. `reporter-flow-audit` renders
that execution evidence without mixing in Agent card declarations. Historical
CV traces from before the gate existed can therefore show missing evidence even
when the current approved run is complete.

## Course-state limitation

Trace JSONL files are bind-mounted and remain available for Flow audit, but held
`PreparedRun` objects and their locks live only in planner memory. If the
planner restarts, an existing held run can no longer be approved or resumed;
submit a new intent and review its new digest.

This is intentionally simple course state. It is not production persistence,
crash recovery, durable workflow orchestration, or proof of idempotent resume.

## Hidden knowledge source

`evaluator-agent-evidence` consumes the registered search contract
`{op: "search", query, limit}` and receives cited passages from the wiki store.
The store remains hidden from the Session 4 Studio while supplying verbatim
citations. Another knowledge engine can replace it behind the same registered
contract without changing the evaluator.
