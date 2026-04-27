# aoa-course

Materials and a runnable system for the **Agent-Oriented Architecture** live course on O'Reilly.

This repo holds two things:

- **`course/`** — session narratives, slides, handouts, and example data.
- **`system/`** — a small, container-shaped AOA system you build across the course.

## What you'll build

Across two hands-on sessions you'll build an AOA system, starting from a single model call and ending with a small multi-capability platform.

In **Session 2** you build a system that evaluates a CV against a job description. By the end of the session you have three agents — parser, evaluator, reporter — co-operating through a small browser studio to produce a structured fit verdict.

In **Session 4** you open the same repo and discover the three-agent chain you built is general. By adding new `skills.md` files to the same agents, you turn it into a cut-down knowledge-management system that parses research notes, ranks passages against a question, and writes a grounded answer.

The point of the course is in that move: the same agents back different capabilities depending on which `skills.md` is mounted. The architecture changes shape without you rewriting the agents.

## Run it

You'll need [Docker](https://docs.docker.com/get-docker/) and either an API key (OpenAI or Anthropic) or a local [Ollama](https://ollama.com) install.

```bash
git clone https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
cp .env.example .env
# edit .env — set PROVIDER and MODEL
make up
```

Then open [http://localhost:8080](http://localhost:8080) for the studio. `make help` lists the rest (`down`, `logs`, `rebuild`, `clean`, `local-up` for Ollama).

## Repo layout

```
course/
  sessions/
    02-anatomy-of-aoa/
    04-lets-build/
  handouts/
  data/
system/
  agents/
  services/
  tools/
  inbox/
  docker-compose.yml
.env.example
Makefile
```

For the architectural story, see [`system/ARCHITECTURE.md`](system/ARCHITECTURE.md). For how the agents work, see [`system/AGENTS.md`](system/AGENTS.md).

## Sessions

- **Session 2 — Anatomy of AOA** — [`course/sessions/02-anatomy-of-aoa/`](course/sessions/02-anatomy-of-aoa/)
- **Session 4 — Let's build** — [`course/sessions/04-lets-build/`](course/sessions/04-lets-build/)

## License

[MIT](LICENSE).
