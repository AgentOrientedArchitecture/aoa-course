# Session 3 — Authoring AUs with EVE

Session 3 introduces [Vercel EVE](https://github.com/vercel/eve) as another way to
author an Agentic Unit, governed by the same registry, planner, and studio as the
Python agents. The full write-up is in [`system/EVE.md`](../../../system/EVE.md).

## Data

Session 3 runs the CV-fit workflow with one extra step — an EVE-authored
interviewer agent that turns the fit verdict into interview questions:

```
parse-cv → evaluate-cv-fit → interviewer-questions
```

So it reuses the **Session 1** CV and job-description examples in
[`../session-01-cv-fit/`](../session-01-cv-fit/). In the studio, choose the
**CV fit + interview** mode and drop in a CV and a job description (for example
`session-01-cv-fit/cv-examples/jordan-okafor.txt` with
`session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt`).

The trace ends in a set of interview questions grouped by area, produced by the
`interviewer-questions` capability — which, in the registry, looks exactly like a
Python AU (an `agent_id`, an `a2a_endpoint`, a `skills_hash`) even though it runs
on Node/EVE.

## Exercises

1. **Modify** — edit `system/agents-eve/interviewer/agent/instructions.md` and
   watch the registry `skills_hash` change live in the studio.
2. **Boundary (capstone)** — run the red-flags agent through EVE's native
   runtime, observe that it is absent from the AOA registry, add a local
   contract constraint, then expose the same behaviour through the generic
   adapter. Docker owns Node, EVE and package dependencies. Full guided lab:
   [`system/agents-eve/EXERCISE.md`](../../../system/agents-eve/EXERCISE.md).

Both are described in [`system/EVE.md`](../../../system/EVE.md).
