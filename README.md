# aoa-course

Materials and a runnable system for the **Agent-Oriented Architecture** live course on O'Reilly.
The system is a reference implementation for learning the architecture shape,
not a production deployment platform.

This repo holds two things:

- **`course/`** — pre-work and example data.
- **`system/`** — a small, container-shaped AOA system you build across the course.

## What you'll build

Across four hands-on sessions you'll build an AOA system, starting from a
single model call and ending with a small multi-capability platform that mixes
agent runtimes - and then checks its own governance evidence against a real regulation.

> Note on numbering: the repo's session profiles are the **hands-on** sequence.
> If you are following a live course, the mapping table under
> [Sessions](#sessions) shows which course session uses which profile.

In **Session 1** you build a system that evaluates a CV against a job
description. By the end of the session you have three governed agent runtimes
— CV parser, evaluator, reporter — co-operating through a small browser studio
to produce a structured fit verdict.

In **Session 2** you open the same repo and discover the pattern is general. A
new wiki parser container runs the same parser code, model, and document-text
tool as the CV parser, but with a different capability contract, `instructions.md`,
and Agent ID. The system becomes a cut-down knowledge-management workflow that
parses research notes, ranks passages against a question, and writes a grounded
answer.

The point of the course is in that move: the same codebase can become a
different governed agent when it is deployed with a different Agent ID,
capability card, and `instructions.md`. The architecture changes shape without
rewriting the parser.

In **Session 3** you author an Agentic Unit with [Vercel EVE](https://github.com/vercel/eve),
a filesystem-first agent framework. EVE has instructions, tools, and a model
config — but no capability card, registry, or governed identity. A small
`aoa-eve` adapter supplies exactly those, so an EVE-authored interviewer agent
(TypeScript, on Node) registers and is orchestrated by the same registry,
planner, and studio as the Python agents. The workflow becomes
`parse-cv → evaluate-cv-fit → interviewer-questions`, and the planner cannot tell
that the last step runs on a different runtime. See
[`system/EVE.md`](system/EVE.md).

The reference adapters currently emit the A2A v0.3 JSON-RPC card/message shape.
They demonstrate an outward agent boundary, not A2A v1 conformance.

In **Session 4** the estate checks itself. An `estate-check` workflow scans the
registry's capability cards, governance lifecycle, and planner traces for
evidence hooks related to selected EU AI Act high-risk-system obligations,
citing the regulation verbatim from a corpus loaded through the Session 2 wiki
pipeline. Findings and evidence only - never a classification or compliance
verdict. The synthetic CV-fit agents match the language of Annex III point 4;
a real employment deployment would need a contextual legal assessment. You
add an oversight constraint, approve the card, and re-scan: the evidence hooks
change because the estate changed, but no legal obligation is thereby
satisfied. See
[`course/data/session-04-compliance/README.md`](course/data/session-04-compliance/README.md).

## Run it

You'll need [Docker](https://docs.docker.com/get-docker/) and either a local
[Ollama](https://ollama.com) install or an API key for a model provider. Start
with the setup guide in
[`course/pre-work/00-setup-and-api-access.md`](course/pre-work/00-setup-and-api-access.md);
it covers the tested `.env` paths for SambaNova, NVIDIA NIM, and local Ollama
running on your host.

```bash
git clone https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
cp .env.sambanova .env     # or .env.nvidia / .env.ollama
# edit .env - add your API key if using a hosted provider
```

Session 1 only needs the CV-fit workflow:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  -f system/docker-compose.session1.yml \
  --profile session1 \
  up --build -d --remove-orphans
```

Session 2 starts the full knowledge-management workflow:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  --profile session2 \
  up --build -d --remove-orphans
```

Session 3 starts the CV-fit workflow plus the EVE-authored interviewer agent:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  -f system/docker-compose.session3.yml \
  --profile session3 \
  up --build -d --remove-orphans
```

Session 4 starts the full estate — CV-fit, wiki, and the estate-check scanner —
then seeds the regulations corpus:

```bash
./scripts/session4-up.sh && ./scripts/session4-seed.sh
```

Session 3's agents are built and run entirely inside containers. The capstone
uses one pinned EVE dependency image to show the same authored agent first in
vendor-native mode and then behind the AOA contract. Participants need Docker,
not host Node/npm or a venue-time package install.

The provided `.env.ollama` example assumes Ollama is already running on your
host machine. If you want Compose to start the included Ollama container
instead, add `--profile local` to either command and set
`OLLAMA_HOST=http://ollama:11434`.

There are also thin helper scripts for the common paths:

```bash
./scripts/session1-up.sh
./scripts/session2-up.sh
./scripts/session3-up.sh
./scripts/session3-lab-native.sh  # EVE-native half of the capstone
./scripts/session3-lab-wrap.sh    # same agent behind the AOA boundary
./scripts/session4-up.sh    # + session4-seed.sh / session4-reset.sh / session4-approve.sh
./scripts/logs.sh
./scripts/down.sh
```

On Windows Command Prompt, use the matching batch files:

```bat
scripts\session1-up.bat
scripts\session2-up.bat
scripts\session3-up.bat
scripts\session3-lab-native.bat
scripts\session3-lab-wrap.bat
scripts\logs.bat
scripts\down.bat
```

For the included Ollama container with a helper script, prefix it with
`AOA_LOCAL=1` on macOS/Linux, or run `set AOA_LOCAL=1` first on Windows. The
host-machine Ollama path does not need `AOA_LOCAL=1`.

Then open [http://localhost:8080](http://localhost:8080) for the studio.
Session 1 shows only the CV intent. Session 2 shows CV fit, ingest, graph, and
ask modes. Session 3 shows CV fit plus a "CV fit + interview" mode that runs the
EVE-authored interviewer agent. Session 4 shows everything plus the "Estate
check" mode.

If something misbehaves, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Repo layout

```
course/
  pre-work/
  data/
system/
  agents/       # Python agentic units (parser, evaluator, reporter)
  agents-eve/   # EVE-authored agentic units (Session 3: interviewer)
  services/
  tools/
  inbox/        # Studio uploads and pasted demo inputs
  wiki/         # Generated wiki raw/promoted/index files
  docker-compose.yml
  docker-compose.session1.yml   # session overlays; session 2 uses the base file
  docker-compose.session3.yml
  docker-compose.session4.yml
.env.example
.env.ollama
.env.sambanova
.env.nvidia
scripts/
```

For the architectural story, see [`system/ARCHITECTURE.md`](system/ARCHITECTURE.md). For how the agents work, see [`system/AGENTS.md`](system/AGENTS.md).

## Sessions

| Repo profile | What you do | Walkthrough / data | Used by course session |
|---|---|---|---|
| `session1` (CV fit) | Build and inspect the three-AU CV-fit workflow, then modify a live agent and watch it re-register | [`course/data/session-01-cv-fit/WALKTHROUGH.md`](course/data/session-01-cv-fit/WALKTHROUGH.md) | Course Sessions 1–2 — "See" (demo) and "Name" (lab: modify your agent) |
| `session2` (wiki) | The same shape becomes a knowledge-management workflow: ingest, promote, graph, ask | [`course/data/session-02-wiki/WALKTHROUGH.md`](course/data/session-02-wiki/WALKTHROUGH.md) | Self-study / optional deep dive — the same pipeline holds Session 4's regulations corpus |
| `session3` (EVE) | Run an EVE-authored agent natively, then expose the same behaviour through an AOA card, identity, registry and trace | [`course/data/session-03-eve/README.md`](course/data/session-03-eve/README.md) · capstone: [`system/agents-eve/EXERCISE.md`](system/agents-eve/EXERCISE.md) | Course Session 3 — "Recognise the shape" (lab: framework inside, contract outside) |
| `session4` (estate check) | The estate scans itself against the EU AI Act and you fix findings live; includes the wiki workflows for the corpus and Ask beats | [`course/data/session-04-compliance/README.md`](course/data/session-04-compliance/README.md) | Course Session 4 — "Apply the shape" (demo: the estate checks itself) |

## License

[MIT](LICENSE).
