# decision

A typed-decision service the planner uses to allocate each task to a registered capability.

It serves the TypeSafe "System One" contract, `POST /v1/systemone`: send a `state` (the goal and the task)
and typed `questions` (a `choice` over candidate capabilities, a `noul` yes/no), receive a probability for
every option and a confidence. The answer is always one of the options you supplied, or `none_of_these`.

Why a separate service and not the planner model: a generative model asked for a plan writes prose that
has to be parsed, can name capabilities that do not exist, and gives no calibrated probability. A decision
model reads the candidates and returns a distribution over them in one forward pass, so the planner can
apply thresholds: abstain (gap), flag for review, or proceed.

Model: a [Kev](https://github.com/jaredpalmer/kev) checkpoint (Apache-2.0; Qwen3 base, Apache-2.0) fine-tuned
on this course's task→capability examples. Mount the run directory at `/models/run`; without it the
service falls back to the released `jaredpalmer/kev-0.8b`, which does not know this registry.

| Env | Default | Meaning |
|---|---|---|
| `DECISION_MODEL_RUN` | `jaredpalmer/kev-0.8b` | run dir or Hub id; `/models/run` wins when mounted |
| `DECISION_DEVICE` | `cpu` | `cpu` or `cuda` |
| `DECISION_PORT` | `7500` | |

Endpoints: `POST /v1/systemone`, `GET /v1/models`.

## The course allocator checkpoint

Published as [`lewisdog/aoa-course-decision-0.6b`](https://huggingface.co/lewisdog/aoa-course-decision-0.6b)
(Apache-2.0; 52 MB adapter + head on `Qwen/Qwen3-0.6B-Base`, warm-started from `jaredpalmer/kev-0.6b`). It is
trained for 7 minutes on this repo's own examples: the 18 task→capability pairs in the planner's `WORKFLOWS`,
hand-written goal phrasings per workflow (also the workflow-choice labels), local paraphrases of goals and task
purposes, `none_of_these` records (gold card removed, or candidates restricted to the Session 1 allowlist),
wrong-card fit negatives, and off-topic requests labelled `none_of_these`. Held-out test, v0.3 (453 questions,
human-written originals never trained on):

| question | accuracy | notes |
|---|---|---|
| workflow (Choice, 6 workflows + none) | 100% originals, 98.3% paraphrases | 100% refusal on 22 off-topic requests |
| agent (Choice, 16 cards + none) | 99% | 97.4% abstention when the gold card is absent, 100% under the Session 1 allowlist |
| fits (Noul) | 98-99% | |
| overall | 98.7%, ECE 0.006, 0.2% confident errors | ~23 ms per question on a GB10 GPU; 1-2.5 s per question on CPU in this container |

Live in the Session 1 stack: a free-text "Is Jordan a good fit for the senior data engineer role?" is classified
`cv-fit` at 1.0 and each task bound at 1.0; "Book me a flight to Lisbon" is refused at classification with a
trace. Mount a run at `models/run` to override, or set `DECISION_MODEL_RUN` to a Hub id. The training harness
(dataset builder, Kev training, benchmark, GGUF export) lives in the `aoa-decide` repository.
