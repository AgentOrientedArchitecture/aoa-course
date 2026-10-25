# CV fit: choosing the AU

Start with `./scripts/session1-up.sh`, or `scripts\session1-up.bat` in Windows Command Prompt, after creating `.env.revised` through the [setup guide](../../pre-work/01-revised-model-access.md). The explicit `revised-up.sh/.bat 1` path also works. Follow the original [CV walkthrough](WALKTHROUGH.md) for synthetic inputs, contract inspection and hot reload, using the differences below. The revised Studio adds **Plan and decisions** and an **Assessment emphasis** field.

Read the [component and selection diagrams](../../ARCHITECTURE.md#session-1-proposing-work-and-choosing-an-au). Expect **five AU cards and one tool**: parser, general/data/frontend evaluators, reporter and document-text. The decision service is control-plane infrastructure, not another registered AU card.

## Predict the allocation

Use the supplied data-engineer CV/job pair. Before running, predict which evaluator should be chosen and why. The registry contains three separate governed runtimes: the original general evaluator, a data-engineering evaluator and a frontend evaluator. They share an output contract but have different declared purposes and assessment instructions.

Run with emphasis “Assess production data pipelines, SQL, reliability and governance.” Inspect:

1. The task breakdown and whether it came from the LLM or the explicit workflow fallback.
2. Contract eligibility: required inputs, output types and lifecycle status.
3. The model's returned choice among eligible evaluators plus “no suitable capability”.
4. The accepted binding, which appears only after the whole plan passes validation.
5. The selected AU's actual output and evidence. Its declared speciality is not a measured quality score.

The LLM can propose the task decomposition; decision selection binds eligible AUs. The bounded course validator preserves each required responsibility and its evidence dependencies. A schema-valid plan that sends the report the wrong upstream evidence must not execute.

## Change the task

Use the frontend job and corresponding CV. Change emphasis to “Assess accessibility, design systems, UI testing and browser performance.” Compare the selected runtime, rationale, latency and output. Keep the generation model fixed.

Try an out-of-scope request. A model can still confidently select an unsuitable option: inspect this as a failure, rather than treating a typed answer as proof. Raise the probability threshold on the hosted route to observe abstention; the local baseline has no such probability gate.

## Edit the AU that actually ran

The original walkthrough edits the general evaluator. With decision allocation, first inspect the accepted binding and edit the corresponding file:

| Selected capability | Instructions to edit |
|---|---|
| `evaluator-cv` | `system/agents/evaluator/capabilities/cv/instructions.md` |
| `evaluator-cv-data` | `system/agents/evaluator/capabilities/cv-data/instructions.md` |
| `evaluator-cv-frontend` | `system/agents/evaluator/capabilities/cv-frontend/instructions.md` |

Record that card's `skills_hash`, change one instruction, wait for its registration update and rerun the same input. Check the newly accepted binding too: if allocation chooses a different AU, this is no longer a controlled comparison of the same implementation. Editing an unselected evaluator can update its card without changing the observed result.

For the optional provider swap, change `.env.revised` (or the exported setting that takes precedence), not only `.env`. Keep a copy of the observed input/output evidence. A visible hash change provides provenance; it does not itself establish that the new behaviour is correct.

## Review questions

- All three evaluators accept the same inputs. What establishes eligibility, and what remains a judgement?
- A selected AU returns the correct JSON shape but a poor assessment. Which evidence should affect future selection?
- The model proposes a new edge that bypasses the evaluation. Why is checking each AU separately insufficient?
- If the bottleneck is the human review queue, what would faster inference change about overall throughput?

Record results on the same examples before changing models. The lesson is sufficient utility from a stable model, with replaceable components and observed quality.
