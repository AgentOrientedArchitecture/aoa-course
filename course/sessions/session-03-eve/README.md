# Session 3 — Authoring AUs with EVE

Session 3 uses [Vercel EVE](https://github.com/vercel/eve) to author and accept
an agent natively before adopting it into the same registry, planner, and Studio
used by the Python agents. The complete guided lab is in
[`WALKTHROUGH.md`](WALKTHROUGH.md); the full technical write-up is in
[`system/EVE.md`](../../../system/EVE.md).

## Data

The adopted agent adds one step to the CV-fit workflow:

```text
parse-cv → evaluate-cv-fit → interviewer-questions
```

Reuse the Session 1 CV and job-description examples in
[`../session-01-cv-fit/`](../session-01-cv-fit/). For example, submit
`session-01-cv-fit/cv-examples/jordan-okafor.txt` with
`session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt` in Studio's
**CV fit + interview** mode.

## Overview

The learner starts with a blank authored surface under
`system/agents-eve/workshop/`. The Session 3 public commands are:

1. `session3-build` — pre-build the pinned
   `aoa-course/eve-workshop:0.17.1` image.
2. `session3-up` — run native EVE only; inside it, run `eve init .`, `eve info`,
   and `eve dev`.
3. `session3-adopt` — create `capability-card.yaml` automatically when missing,
   start AOA, and publish the accepted agent.

Use `eve dev` to complete the native acceptance tests before adoption. The
agent must return JSON only, exactly five bounded interview questions, and no
more than 1200 tokens. If you later edit the generated capability card, rerun
`session3-adopt` to revalidate and republish it.

Course-owned EVE infrastructure lives under `system/agents-eve/runtime/`.
Learner-authored files and the generated capability card stay under
`system/agents-eve/workshop/`.

Node, npm, EVE, and package dependencies remain in Docker; no host JavaScript
toolchain is required.
