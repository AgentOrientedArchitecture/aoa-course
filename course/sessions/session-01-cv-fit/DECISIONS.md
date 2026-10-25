# CV allocation reference

Optional background for [Session 1](WALKTHROUGH.md). The walkthrough includes
all the practical steps, provider comparison and review questions.

## Two different model responsibilities

The planner's generation model proposes a bounded task plan. The course
already defines its required responsibilities and reference contracts; failed
or invalid proposals use a recorded fallback. This service is real executable
planning and orchestration code, but is not itself a registered Planner AU.

Allocation then asks **which eligible AU should perform this task?** The
general, data-engineering and frontend evaluators are separate runtimes. They
have compatible contracts and different declared purposes and instructions.
The decision model selects among those declarations plus
`no_suitable_capability`. Its input is task purpose, assessment emphasis and
use context, not the CV and job contents. The selected AU performs the actual
document assessment afterwards.

![Task proposal, eligibility, choice and composition validation](../../diagrams/cv-selection.svg)

## What code guarantees here

| Boundary | Implemented check | What it does not establish |
|---|---|---|
| Contract eligibility | Approved AU lifecycle, compatible inputs and outputs, no extra required input. | Whether declared specialisation is useful on this case. |
| Choice acceptance | An eligible returned option and the configured probability policy. | Semantic correctness or measured output quality. |
| Composition validation | Required responsibilities and evidence dependencies, input types and references. | Correctness of every claim inside an AU's output. |
| Recorded binding | Selection is accepted only after composition validation. | That future runs must choose the same AU. |

With one eligible capability the code binds it without a model call. No fit,
insufficient probability, a provider failure or an invalid response prevents
allocation from proceeding to application execution. **AU selection** separates
the returned choice, composition check and accepted binding.

## Probability and evaluation

`DECISION_MIN_PROBABILITY` is an illustrative course policy, not a threshold
calibrated against measured accuracy. The local Ollama baseline uses constrained
JSON and returns no probability; `DECISION_ALLOW_UNSCORED=true` explicitly
permits it. It is not equivalent to the hosted TypeSafe decision model.

Compare candidate results on the same examples before changing providers.
Keep the selected AU, its `skills_hash`, model, input, output and observed
signals together. If allocation changes when rerunning an instruction edit,
that is no longer a controlled comparison of one AU's behaviour. Editing an
unselected evaluator can change its card without changing the result.

A production selector would need evidence about failures, relative quality,
cost and abstentions on representative held-out tasks. The course records
observations; it does not automatically train a selector or maintain a
measured-quality marketplace. Faster inference alone does not remove a human
review or downstream capacity constraint.

The [course architecture guide](../../ARCHITECTURE.md#session-1-proposing-work-and-choosing-an-au)
provides the wider component view.
