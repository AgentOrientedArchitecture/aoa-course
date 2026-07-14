# aoa-course

Materials and a runnable system for the **Agent-Oriented Architecture** live course on O'Reilly.
The system is a reference implementation for learning the architecture shape,
not a production deployment platform.

This repo holds two things:

- **`course/`** — pre-work, plus a folder per session with its walkthrough and example data.
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

In **Session 4** learners follow exactly three core governance stages. **Agent
card check** starts `evaluator-cv` Article 14 red and visibly retrieves the exact
query, passage ID, source, and complete quote from `tool-wiki-store`. A CV-fit
attempt is rejected before application lookup or invocation. The learner adds
the required review-before-use declaration, watches it hot-reload, and reruns
the card check; green means declaration observed only. **CV fit** then passes
deterministic eligibility, runs the application AUs to an immutable held draft,
and requires a human to review the actual output, add notes, and approve or
reject its exact `result_digest`. Approval releases the identical draft;
rejection quarantines it. **Flow audit** checks eligibility, event order,
exact-result review, release/quarantine, payload equality, and an Article 14
wiki citation. It defaults to traces carrying the current
`human-review-before-release` result-governance model. Older employment traces
remain persisted but hidden unless the **Show legacy history** checkbox is
selected; the panel reports how many are included. A red legacy row means current evidence is
absent, not necessarily that the old execution failed. Legacy plan approval is
not result-review evidence. See
[`course/sessions/session-04-compliance/WALKTHROUGH.md`](course/sessions/session-04-compliance/WALKTHROUGH.md).

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

Session 3 starts with a native EVE workshop, then adopts the tested agent into
the CV-fit workflow:

```bash
./scripts/session3-up.sh       # run eve init, eve info, and eve dev
./scripts/session3-adopt.sh    # create the AOA card and start the estate
```

Session 4 starts Studio with three core stages — Agent card check, CV fit, and
Flow audit — plus optional Graph and Ask evidence exploration and deterministic
planner routing, then seeds and verifies the inspectable regulations corpus
used for governance evidence:

```bash
./scripts/session4-up.sh
./scripts/session4-seed.sh
```

Session 3's agent is created and run entirely inside containers. A pinned EVE
workshop image exposes the real `eve init`, `eve info`, and `eve dev` CLI against
a bind-mounted learner workspace. Participants need Docker, not host Node/npm
or a venue-time package install. They build the agent natively first; the
adoption script then creates its capability card and runs the same files through
the generic AOA bridge.

The provided `.env.ollama` example assumes Ollama is already running on your
host machine. If you want Compose to start the included Ollama container
instead, add `--profile local` to either command and set
`OLLAMA_HOST=http://ollama:11434`.

There are also thin helper scripts for the common paths:

```bash
./scripts/session1-up.sh
./scripts/session2-up.sh
./scripts/session3-build.sh    # pre-work: images only, no agent created
./scripts/session3-up.sh       # enter the interactive EVE workshop
./scripts/session3-adopt.sh    # publish the tested agent into AOA
./scripts/session4-up.sh       # then session4-seed.sh
./scripts/logs.sh
./scripts/down.sh
```

On Windows Command Prompt, use the matching batch files:

```bat
scripts\session1-up.bat
scripts\session2-up.bat
scripts\session3-build.bat    rem pre-work: images only
scripts\session3-up.bat       rem interactive native EVE workshop
scripts\session3-adopt.bat    rem create the AOA card and start the estate
scripts\session4-up.bat
scripts\session4-seed.bat
scripts\logs.bat
scripts\down.bat
```

For the included Ollama container with a helper script, prefix it with
`AOA_LOCAL=1` on macOS/Linux, or run `set AOA_LOCAL=1` first on Windows. The
host-machine Ollama path does not need `AOA_LOCAL=1`.

Then open [http://localhost:8080](http://localhost:8080) for the studio.
Session 1 shows only the CV intent. Session 2 shows CV fit, ingest, graph, and
ask modes. Session 3 shows CV fit plus a "CV fit + interview" mode that runs the
EVE-authored interviewer agent. Session 4 presents exactly three core governance
stages — **Agent card check**, **CV fit**, and **Flow audit** — plus optional
**Graph** and **Ask** evidence-exploration utilities. Graph visualizes the seeded
EU AI Act wiki. Ask runs the grounded knowledge-query workflow so learners can
inspect passage citations and tool retrieval; neither utility is another
governance stage. Wiki reset is disabled in Session 4 to protect the governance
corpus, so rerun the Session 4 seed script if evidence is missing. The wiki is
an explicit governance/evidence knowledge plane: deterministic policy decides,
while visible wiki queries and citations supply rationale. Missing Annex III
employment or Article 14 evidence fails employment eligibility closed. Eligible
CV fit runs only to a held draft until a human reviews the actual output and
decides its exact `result_digest`.

If something misbehaves, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Repo layout

```
course/
  pre-work/
  sessions/     # one folder per session: WALKTHROUGH.md + example data
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

Each session folder under [`course/sessions/`](course/sessions/) has a
`WALKTHROUGH.md` with the learner instructions and a `README.md` describing its
example data.

| Repo profile | What you do | Walkthrough | Used by course session |
|---|---|---|---|
| `session1` (CV fit) | Build and inspect the three-AU CV-fit workflow, then modify a live agent and watch it re-register | [`course/sessions/session-01-cv-fit/WALKTHROUGH.md`](course/sessions/session-01-cv-fit/WALKTHROUGH.md) | Course Sessions 1–2 — "See" (demo) and "Name" (lab: modify your agent) |
| `session2` (wiki) | The same shape becomes a knowledge-management workflow: ingest, promote, graph, ask | [`course/sessions/session-02-wiki/WALKTHROUGH.md`](course/sessions/session-02-wiki/WALKTHROUGH.md) | Self-study / optional deep dive — the same pipeline holds Session 4's regulations corpus |
| `session3` (EVE) | Run an EVE-authored agent natively, then expose the same behaviour through an AOA card, identity, registry and trace | [`course/sessions/session-03-eve/WALKTHROUGH.md`](course/sessions/session-03-eve/WALKTHROUGH.md) | Course Session 3 — "Recognise the shape" (lab: framework inside, contract outside) |
| `session4` (card evidence + result review + flow audit) | Improve declared Agent card evidence, run eligible CV fit to a held draft, review its exact result digest, then audit release or quarantine evidence | [`course/sessions/session-04-compliance/WALKTHROUGH.md`](course/sessions/session-04-compliance/WALKTHROUGH.md) | Course Session 4 — "Apply the shape" (lab: separate declarations, deterministic eligibility, result review, execution evidence, and legal claims) |

## License

[MIT](LICENSE).
