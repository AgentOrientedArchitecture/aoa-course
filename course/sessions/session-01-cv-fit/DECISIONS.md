# CV fit: choosing the AU

Start with `./scripts/revised-up.sh 1`. Follow the original [CV walkthrough](WALKTHROUGH.md) for synthetic inputs, contract inspection and hot reload. The revised Studio adds **Plan and decisions** and an **Assessment emphasis** field.

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

## Review questions

- All three evaluators accept the same inputs. What establishes eligibility, and what remains a judgement?
- A selected AU returns the correct JSON shape but a poor assessment. Which evidence should affect future selection?
- The model proposes a new edge that bypasses the evaluation. Why is checking each AU separately insufficient?
- If the bottleneck is the human review queue, what would faster inference change about overall throughput?

Record results on the same examples before changing models. The lesson is sufficient utility from a stable model, with replaceable components and observed quality.
