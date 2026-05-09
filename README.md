# aoa-course

Materials and a runnable system for the **Agent-Oriented Architecture** live course on O'Reilly.
The system is a reference implementation for learning the architecture shape,
not a production deployment platform.

This repo holds two things:

- **`course/`** — pre-work and example data.
- **`system/`** — a small, container-shaped AOA system you build across the course.

## What you'll build

Across two hands-on sessions you'll build an AOA system, starting from a single model call and ending with a small multi-capability platform.

In **Session 2** you build a system that evaluates a CV against a job
description. By the end of the session you have three governed agent runtimes
— CV parser, evaluator, reporter — co-operating through a small browser studio
to produce a structured fit verdict.

In **Session 4** you open the same repo and discover the pattern is general. A
new wiki parser container runs the same parser code, model, and document-text
tool as the CV parser, but with a different capability contract, `skills.md`,
and Agent ID. The system becomes a cut-down knowledge-management workflow that
parses research notes, ranks passages against a question, and writes a grounded
answer.

The point of the course is in that move: the same codebase can become a
different governed agent when it is deployed with a different Agent ID,
capability card, and `skills.md`. The architecture changes shape without
rewriting the parser.

## Run it

You'll need [Docker](https://docs.docker.com/get-docker/) and either a local
[Ollama](https://ollama.com) install or an API key for a model provider. The
course is designed around smaller, swappable models such as `gpt-oss:120b` or
Qwen-family models, whether you run them locally or through an
OpenAI-compatible hosted endpoint.

```bash
git clone https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
cp .env.example .env
# edit .env — set PROVIDER and MODEL
```

Session 2 only needs the CV-fit workflow:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  -f system/docker-compose.session2.yml \
  --profile session2 \
  up --build -d --remove-orphans
```

Session 4 starts the full knowledge-management workflow:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  --profile session4 \
  up --build -d --remove-orphans
```

If you want Compose to start the included Ollama container as well, add
`--profile local` to either command.

There are also thin helper scripts for the common paths:

```bash
./scripts/session2-up.sh
./scripts/session4-up.sh
./scripts/logs.sh
./scripts/down.sh
```

On Windows Command Prompt, use the matching batch files:

```bat
scripts\session2-up.bat
scripts\session4-up.bat
scripts\logs.bat
scripts\down.bat
```

For the included Ollama container with a helper script, prefix it with
`AOA_LOCAL=1` on macOS/Linux, or run `set AOA_LOCAL=1` first on Windows.

Then open [http://localhost:8080](http://localhost:8080) for the studio.
Session 2 shows only the CV intent. Session 4 shows CV fit, ingest, graph, and
ask modes.

## Repo layout

```
course/
  pre-work/
  data/
system/
  agents/
  services/
  tools/
  inbox/
  docker-compose.yml
  docker-compose.session2.yml
.env.example
scripts/
```

For the architectural story, see [`system/ARCHITECTURE.md`](system/ARCHITECTURE.md). For how the agents work, see [`system/AGENTS.md`](system/AGENTS.md).

## Sessions

- **Session 2 — Anatomy of AOA** — CV-fit data in [`course/data/session-02-cv-fit/`](course/data/session-02-cv-fit/)
- **Session 4 — Let's build** — wiki seed data in [`course/data/session-04-wiki/`](course/data/session-04-wiki/)

## License

[MIT](LICENSE).
