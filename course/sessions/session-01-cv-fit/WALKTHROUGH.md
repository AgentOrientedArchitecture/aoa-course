# Session 1 walkthrough — build, inspect, then change a live agent

The CV-fit workflow: three governed agents (`parser-cv` → `evaluator-cv` →
`reporter-cv-fit`) co-operating through the registry, planner, and studio.
This walkthrough is self-contained; ~25 minutes at an unhurried pace.

## 1. Start the stack

```bash
./scripts/session1-up.sh
```

Open [http://localhost:8080](http://localhost:8080). Before running anything,
read the **Registry pane**: three `kind: au` capabilities and one
`kind: tool` (`tool-document-text`), each with an Agent ID, a version, a
`skills_hash`, and lifecycle fields (`published_by`, `approved_by`, `status`).
Nothing here is a description of the system — it *is* the system's public
surface.

## 2. Run the workflow

In the **CV fit** tab, drop or paste a CV and a job description:

- CV: `course/sessions/session-01-cv-fit/cv-examples/jordan-okafor.txt`
- JD: `course/sessions/session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt`

Submit, and watch the **trace timeline** fill in: the planner proposes a route,
validates it against the capability cards, then each AU is looked up, invoked
over A2A, calls its declared tools, and returns outputs plus **signals**.

Things worth pointing at in the trace:

- The planner selected capabilities by **card**, not by name in code.
- `parser-cv` reached for `tool-document-text` — a declared, traced boundary.
- Every step carries the same `trace_id`: the whole run is reconstructable.
- The signals block on each response (schema validity, latency) is the
  "observed, not asserted" surface in miniature.

Try the other pairings (`sam-everett.txt`, `frontend-engineer-design-systems.txt`)
— the expected verdicts are in [`README.md`](README.md).

## 3. The lab: modify your agent

Behaviour lives in a governed file, not in the code. Change it and watch the
public surface move.

1. **Baseline.** Note `evaluator-cv`'s current `skills_hash` in the Registry
   pane, and keep your last verdict visible.
2. **Change the behaviour.** Edit
   `system/agents/evaluator/capabilities/cv/instructions.md` — one line is
   enough. For example: make seniority scoring stricter, or require named
   evidence for every gap.
3. **Watch the Registry pane.** On save, the file watcher recomputes the hash
   and re-registers the card: the `skills_hash` chip changes, **with no
   restart**, while the Agent ID stays fixed. The governed behaviour version
   changed, and every consumer of the registry can see that it changed.
4. **Observe the change.** Re-run the same CV + JD. Same workflow shape,
   different behaviour, shifted signals — and the hash records which behaviour
   version produced which result.

The same applies to the **capability card** itself: edit
`capabilities/cv/capability-card.yaml` (say, add a constraint) and the card
re-registers too — a card edit is a governance event.

## 4. Stretch: swap the model provider

The model sits *behind* the capability, so replacing it is configuration:

```bash
# edit .env - e.g. switch PROVIDER/MODEL between ollama and a hosted endpoint
./scripts/down.sh && ./scripts/session1-up.sh
```

The Registry pane's `provenance.model` chip updates; Agent ID, capability ID,
and the workflow stay put. Compare latency in the trace before and after —
that is "replacement is registration" at the model layer.

## What to take away

- The **card** is the public promise; `instructions.md` is governed behaviour;
  tools are declared dependencies; the model is an implementation detail.
- Change behind the boundary is safe **because** the public surfaces
  (`skills_hash`, `provenance.model`, signals) show it moving.
- The question this sets up: the registry accepted your change without asking
  anyone. Should it have? (Session 4's estate check has an opinion.)
