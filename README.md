# aoa-course

Materials and runnable system for the **Agent-Oriented Architecture** live course on O'Reilly, **14 May 2026**.

This repo carries two things at once:

- **`course/`** — session narratives, slides, handouts, and the data the live build runs against.
- **`system/`** — a small, runnable, container-shaped AOA system that the audience builds across the course.

It is _not_ the same thing as [`aoa-knowledge`](https://github.com/AgentOrientedArchitecture/aoa-knowledge). That repo is the working knowledge base for the AOA project. This repo is the teaching artefact.

## What you'll build

In **Session 2** the audience builds a small AOA system that evaluates a CV against a job description. By the end of S2, three agents (parser, evaluator, reporter) work together through a tiny browser-based studio to produce a structured fit verdict.

In **Session 4** the audience opens the same repo and discovers the three-agent chain they built is general — it's also a query pipeline. They add new `skills.md` files against the same agent codebases and two more agents to make it a knowledge-management system: ingest research notes, promote them to a wiki, query the wiki with grounded answers.

The architectural payoff is that the same physical agents back different registered capabilities depending on which `skills.md` is mounted. Almost nothing about the agent _code_ changes between the CV evaluator (S2) and the wiki query system (S4) — what changes is which capabilities are registered.

## Five-minute clone-to-run

You'll need [Docker](https://docs.docker.com/get-docker/) and either an API key for OpenAI/Anthropic or a local [Ollama](https://ollama.com) install.

```bash
git clone https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
cp system/.env.example system/.env
# edit system/.env — set PROVIDER and MODEL
cd system && docker compose up
```

Open `http://localhost:8080` for the studio.

## Repo layout

See [`system/ARCHITECTURE.md`](system/ARCHITECTURE.md) for the architectural story and [`system/AGENTS.md`](system/AGENTS.md) for how agents in this repo work.

```
course/
  sessions/
    02-anatomy-of-aoa/
    04-lets-build/
  handouts/
  data/
system/
  agents/        # five agent codebases, eight capabilities by S4 end
  services/      # registry, planner, studio, watcher
  tools/         # registered capabilities that aren't AUs
  seed-wiki/
  inbox/  raw/  wiki/
  docker-compose.yml
  Makefile
```

## Sessions

- **Session 2 — Anatomy of AOA** — [`course/sessions/02-anatomy-of-aoa/`](course/sessions/02-anatomy-of-aoa/)
- **Session 4 — Let's build** — [`course/sessions/04-lets-build/`](course/sessions/04-lets-build/)

Sessions 1 and 3 don't have folders here — they're talk-and-demo sessions and live in [`aoa-knowledge`](https://github.com/AgentOrientedArchitecture/aoa-knowledge) under `course/2026-05-14-oreilly/`.

## Status

This repo is being built ahead of the May 14 course. Expect breaking changes until the course-day SHA is pinned (target: 11 May 2026).

## License

[MIT](LICENSE).
