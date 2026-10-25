# AOA course

Build one estate through four examples: **CV assessment → knowledge wiki → an EVE-authored interviewer → governance and compliance evidence**. Inspect the plan, the model's decisions, the discovered capabilities and the state that survives a restart.

Use this page as the entry point for the course on `main`. Each session has one complete walkthrough. Its other documents explain the architecture or offer optional exercises; you do not need to switch guides to finish the session.

## Reading order

1. [Set up model access and launchers](pre-work/SETUP.md).
2. Follow the session walkthroughs below, in order. Each includes its start commands, exercises, evidence checks, review questions and stop command.
3. Use [the architecture diagrams](ARCHITECTURE.md) when you want to see how the components connect. The walkthroughs link to the relevant explanations.

## What learners should be able to explain and demonstrate

1. Separate an intent, a task decomposition, an eligible capability and an accepted executable plan.
2. Use a decision model both to choose an AU and to implement the judgement inside an AU.
3. Measure whether a stable model meets a bounded job, including failures, latency and cost. A new frontier model is an option to evaluate, not a weekly architectural dependency.
4. Adopt an agent built in another framework without rewriting its authored behaviour. Distinguish Directory discovery from local acceptance and permission to execute.
5. Recover an exact held result after a restart, review it once, and inspect the evidence of what happened.

## Four connected live sessions

| Session walkthrough | Question | Visible demonstration | Learner change |
|---|---|---|---|
| [1 · CV fit](sessions/session-01-cv-fit/WALKTHROUGH.md) | Which AU can perform this task? | Proposed tasks, eligible alternatives, model choice, whole-plan validation, actual output | Change the assessment emphasis from data engineering to frontend delivery; compare the binding and result |
| [2 · Wiki](sessions/session-02-wiki/WALKTHROUGH.md) | Does this source belong in the wiki? | TypeSafe returns promote/reject/review; the AU retains parsed passages and controls publication | Compare relevant, irrelevant and uncertain notes; inspect false acceptance and abstention |
| [3 · EVE and AGNTCY](sessions/session-03-eve/WALKTHROUGH.md) | How does an independently built agent become usable here? | Native EVE authoring, publication of all running AUs, AGNTCY discovery, local adoption checks and accepted composition | Find the EVE content ID in the executed plan; stop Directory and observe new discovery fail without fallback |
| [4 · Compliance](sessions/session-04-compliance/WALKTHROUGH.md) | What evidence permits a result to be used? | Card check, held result, restart, exact-result review and flow audit | Reopen the same case after restart, approve or reject its digest, repeat the request and audit the outcome |

For each demonstration: **predict → reveal → inspect → change → compare**. Ask for a prediction before exposing the trace. An output that looks plausible is not sufficient evidence of the intended boundary.

## Model access

[The setup](pre-work/SETUP.md) uses Cerebras `gpt-oss-120b` for generation and TypeSafe `jev-1.13.0` for bounded choices. Ollama remains available. The local constrained-choice baseline is labelled as such; it is not represented as Jev or given invented probabilities.

The CV assessment itself still needs language generation. The wiki promotion AU demonstrates a different product design: a bounded decision is the main model output, while code assembles an evidence-preserving result. This is a separate application of decision models from planner allocation.

## Personal agents and enterprise constraints

Use a personal agent as the initiating interface in the discussion: “Assess these documents and prepare the interview.” The same interface must hand work to explicit capabilities, use shared knowledge, preserve case state and observe release policy. Making one person's interface faster does not establish improved throughput across the enterprise. Ask learners which shared resource or approval queue constrains their example and what observation would demonstrate an improvement.

There is no extra personal-agent framework to install for this course. The browser is the initiating interface; the inspectable enterprise execution path is the lesson.

## Evidence and limits

The [architecture guide](ARCHITECTURE.md) links the diagrams to their implementation. The [validation record](VALIDATION.md) separates observed behaviour from checks still outstanding.

- A valid choice and a high model probability do not prove semantic correctness. The default 0.65 gate is a teaching setting, not a calibrated production threshold.
- Composition checks cover this bounded set of course responsibilities, dependencies and contracts. They are not a general-purpose proof of arbitrary DAG correctness.
- The persistent case is a SQLite-backed teaching implementation. It demonstrates an addressed case, durable state and serialised transitions; it does not run Cloudflare Durable Objects or claim exactly-once external effects.
- The AGNTCY exercise uses an actual local Directory daemon. It does not deploy federation, SLIM, verified identity or an enterprise trust service.
- The compliance exercise retains the existing curated corpus and policy. Green evidence is not certification of legal compliance.

See [instructor runbook](INSTRUCTOR.md) and [validation record](VALIDATION.md) for delivery checks and remaining gaps.
