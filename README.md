# aoa-course

**Start here:** [Course setup](course/pre-work/01-revised-model-access.md). Use `main`, copy `.env.example` to `.env`, add the two hosted-provider keys or choose the local option in that same file, then use the session scripts. One Compose file defines the current course.

**Course:** [Four connected live demos](course/REVISED-COURSE.md) · [Architecture and diagrams](course/ARCHITECTURE.md) · [EVE and AGNTCY adoption](course/sessions/session-03-eve/ADOPTION.md).

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

Install Git and Docker, then:

```bash
git clone --branch main https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
cp .env.example .env
# Add CEREBRAS_API_KEY and TYPESAFE_API_KEY privately in .env.
./scripts/test_model_provider.sh
./scripts/session1-up.sh
```

On Windows use Command Prompt, `copy .env.example .env`, and the matching `.bat` commands. The [setup guide](course/pre-work/01-revised-model-access.md) covers hosted models, the local Ollama option, and existing checkouts.

```bash
./scripts/session1-up.sh
./scripts/session2-up.sh
./scripts/session3-build.sh    # pre-build images
./scripts/session3-up.sh       # native EVE authoring and acceptance
./scripts/session3-adopt.sh    # adopt into AOA and publish to AGNTCY
./scripts/session4-up.sh
./scripts/session4-seed.sh
./scripts/logs.sh
./scripts/down.sh             # retains authored files and saved data
```

Open [Studio](http://localhost:8080) after starting an AOA session. Native EVE authoring is deliberately separate; follow its [walkthrough](course/sessions/session-03-eve/WALKTHROUGH.md). AGNTCY's [catalogue](http://localhost:8891) becomes available with Session 3 adoption and continues in Session 4.

`system/docker-compose.yml` is the sole current Compose definition. The scripts choose session profiles and settings; students do not assemble overlays or select a course version. Existing private `.env.revised` files remain readable during migration, but fresh setups use only `.env`. Earlier configurations and the previous setup instructions are [preserved in the archive](archive/configuration-before-consolidation/README.md).

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
.env.example                  # the one current configuration example
archive/                      # preserved earlier configurations and instructions
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
