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
