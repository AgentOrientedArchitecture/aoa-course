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

`models/run` (git-ignored, mount it or fetch it) is a Qwen3-0.6B-Base + LoRA r16 + pointer head, warm-started
from `jaredpalmer/kev-0.6b` and fine-tuned for 7 minutes on this repo's own task→capability examples: the 18
gold pairs in the planner's `WORKFLOWS`, paraphrased goals and task purposes, `none_of_these` records with the
gold card removed, and Session 1 allowlist records (three cards only). On the held-out test split
(356 questions, human-written originals never trained on):

| question | accuracy | notes |
|---|---|---|
| agent (Choice, 16 cards + none) | 98.1% | 97.3% on the human originals, 94.7% abstention when the gold card is absent, 90% abstention under the Session 1 allowlist |
| fits (Noul) | 99.0% | |
| overall | 98.6%, ECE 0.009, 0.8% confident errors | 74 ms per question on a GB10 GPU; ~1 s on CPU in this container |

Live in the Session 1 stack: `cv-fit` allocates parser-cv, evaluator-cv, reporter-cv-fit at probability 1.0
each; a `knowledge-query` intent against the three-card registry stops with `none_of_these` at 1.0 before any
AU is invoked. The training harness (dataset builder, Kev training, benchmark, GGUF export) lives in the
`aoa-decide` repository; the checkpoint is 52 MB.
