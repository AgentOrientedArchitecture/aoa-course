# Architecture

This document describes the AOA system inside `system/`. It exists before the code so the architectural story is in prose first; the code is the implementation of this document, not the other way round.

## What this system is

A small, container-shaped, deliberately readable AOA system. Three workflows, five agent codebases, eight registered capabilities, one MCP tool, four plumbing services. Roughly 2,200 lines of Python all-in by Session 4 end.

The audience builds this system across two course sessions:

- **Session 2** ends at three agents (parser, evaluator, reporter) producing a CV-vs-JD fit verdict — three registered capabilities, one workflow.
- **Session 4** ends at five agents and eight registered capabilities, threading three workflows: ingest, promote, query.

The S2 system is a literal subset of the S4 system. Nothing built in S2 is deleted or rewritten.

## The architectural claims this system demonstrates

Six claims, each tied to a moment the audience sees on screen:

1. **An AU is `model + capability + skills.md + maybe tools`.** Some AUs have no tools. The reporter is the example. Read any agent folder to see all four parts.
2. **Tools can be registered capabilities without being AUs.** The MCP filesystem server in `tools/` registers in the same registry as the agents. The registry is a _capability_ registry, not an agent registry.
3. **Registered capability ≠ physical agent.** The evaluator codebase backs three registered capabilities by S4 end (`evaluator-cv`, `evaluator-ingest`, `evaluator-query`). The studio shows them as three rows.
4. **`skills.md` gives a capability its identity.** Same model, same code, same tools — different `skills.md` makes a different capability. Made loud when we live-edit `evaluator-query/skills.md` and the studio's registry pane shows that one entry's `skills_hash` change while everything else holds.
5. **The architecture is indifferent to where reasoning happens.** Live-swap the model from API to Ollama; nothing else changes.
6. **Intent is a first-class surface.** The studio is how humans hand intents into the system. AOA isn't only agents-talking-to-agents; it's a layered handover from intent through plan through capability through tool.

## The three workflows

**S2 ships one workflow:**

```
parser-cv → evaluator-cv → reporter-cv-fit
```

The audience submits a CV and a JD through the studio. The planner queries the registry for `parser-cv`, gets a handle, calls it. The parser returns structured CV data. The planner queries for `evaluator-cv`, calls it with the parsed CV and the JD. The evaluator returns scores and a verdict. The planner queries for `reporter-cv-fit`, calls it with the evaluation. The reporter returns a structured fit-verdict report. The studio shows every step in the trace pane.

**S4 adds two more workflows, and reuses the S2 chain in a third form:**

```
ingest:  parser-notes → evaluator-ingest → (gate)         → raw/
promote: promoter                                          → wiki/
query:   searcher → evaluator-query → reporter-answer      → answer
```

The query workflow is structurally identical to the S2 workflow. Three agents in a chain, the middle one is the evaluator. The audience already built this chain in S2; in S4 they discover it's general.

## The agent set

Five codebases. Eight registered capabilities. One tool.

| Codebase | S2 capabilities | S4 capabilities |
|---|---|---|
| `parser` | `parser-cv` | `parser-cv`, `parser-notes` |
| `evaluator` | `evaluator-cv` | `evaluator-cv`, `evaluator-ingest`, `evaluator-query` |
| `reporter` | `reporter-cv-fit` | `reporter-cv-fit`, `reporter-answer` |
| `promoter` | — | `promoter` |
| `searcher` | — | `searcher` |

Plus, in `tools/`:

| Tool | Registered as | Type |
|---|---|---|
| filesystem MCP server | `tool-filesystem` | Pure tool, not an AU |

S2 ends at 3 agents, 3 capabilities, 1 tool, 1 workflow. S4 ends at 5 agents, 8 capabilities, 1 tool, 3 workflows.

## The four-part AU anatomy

Every AU in this repo has four addressable parts:

1. **Capability card** (`capability-card.yaml`) — the contract. Public. Mounted read-only in the container, exposed at `/cards/<id>`.
2. **`skills.md`** — the unit's practical know-how for its job. Prompt structure, rubric, judgement criteria, examples. Mounted read-only and **hot-reloaded**: editing `skills.md` on the host changes capability behaviour without a container restart.
3. **`tools.yaml`** — capability ids the agent will call. Read at boot. May be empty.
4. **`agent.py`** — wiring between the three above and a model. Framework-agnostic. Built on a ~50-line shared FastAPI scaffold in `agents/_base/`.

When a single codebase backs more than one capability, capability-specific files live in a `capabilities/<name>/` subfolder; the code lives at the agent root. Every agent uses this pattern even when it currently has only one capability — it sets the expectation that any agent might gain a second.

## Plumbing services

| Service | Job | Lines budget |
|---|---|---|
| **registry** | Loads capability cards on startup. Watches `cards.json` for changes. Exposes `find_capability(intent)` and `list_capabilities()` over HTTP. | ~150 |
| **planner** | Receives intents from the studio. Queries the registry. Sequences agent invocations. Records each step to `traces/<event-id>.jsonl`. | ~200 |
| **studio** | Browser surface at `localhost:8080`. Three observation panes (registry, trace, capability card) plus an intent submission box and file drop. Subscribes to traces and registry changes via SSE. | ~250 |
| **watcher** _(S4 only)_ | Watches `inbox/` for new files. Posts ingest events to the planner. | ~50 |

## Container topology

Each agent and each service in its own container. Compose orchestrates.

```
docker-compose.yml services:

  registry             FastAPI    7100
  planner              FastAPI    7200
  studio               FastAPI    8080  (the page lives here)
  watcher              S4 only,   no port
  parser               FastAPI    7301
  evaluator            FastAPI    7302
  reporter             FastAPI    7303
  promoter             S4 only    7304
  searcher             S4 only    7305
  tool-filesystem      MCP        7401
  ollama               profile: local, optional
```

Eleven containers at S4 end (eight at S2 end).

Each agent container has the same shape: FastAPI app, mounts its `capabilities/` folder as a volume, registers itself with the registry on boot, exposes `/invoke`, exposes `/cards/<id>`, watches mounted `skills.md` files for hot reload. The audience reads one agent and has read them all.

## Capability card schema

```yaml
id: evaluator-query
version: 0.1.0
kind: au                            # or "tool" for non-AU registered capabilities
purpose: |
  Rank candidate passages against a question and return a scored shortlist
  with reasons.
inputs:
  - name: question
    type: string
    required: true
  - name: candidates
    type: array<passage>
    required: true
outputs:
  - name: ranked
    type: array<scored_passage>
constraints:
  - Each scored passage must include a citation back to its source path.
  - Scores must be in [0, 1].
  - Reasons must be one sentence each.
evaluation_signals:
  - all_passages_have_citation
  - score_distribution_not_degenerate
  - latency_p95_under(8s)
provenance:
  model: ${MODEL}
  skills_hash: <sha of skills.md>
endpoint: http://evaluator:7302/invoke
```

The three evaluator capability cards differ in `purpose`, `inputs`, `outputs`, `constraints`, `evaluation_signals`, `skills.md`, and `endpoint` (path differs per capability). They share `agent.py` and `model`. That's the architectural payoff made concrete in YAML.

Pure tools have `kind: tool` and `provenance.model: none`. The registry uses `kind` for studio display only — the planner doesn't branch on it.

## The studio

A browser-based surface at `localhost:8080`. Two roles:

**Observation:**

- **Registry pane.** Live listing of every registered capability with id, version, kind (`au` or `tool`), backing agent codebase, and current `skills_hash`. Updates when capabilities register, deregister, or change.
- **Trace pane.** Currently-running flow as a vertical timeline. Each step is a row showing planner → registry lookup, agent invocation, response. Rows collapsible for full payloads. Finished flows persist until the next intent runs.
- **Capability card pane.** Click any registry entry, see its card formatted.

**Intent:**

- **Submit an intent.** Free-form text box. Sent to the planner; planner routes to the right capability; trace pane fills in real time.
- **Drop a file.** Drag a CV onto the page in S2, or a research note in S4.

The studio does not browse the wiki. The wiki has its own viewers (Obsidian primary). A future v0.2 portal app may serve as a wiki front end; that's deliberately out of scope for the May 14 build.

The studio's visual vocabulary echoes [`aoa-a2a-intent-studio`](https://github.com/AgentOrientedArchitecture/aoa-a2a-intent-studio) — the production AOA studio — but no code is shared. This is a course-shaped equivalent built fresh in ~250 lines.

## What this repo is not

- Not a framework. No abstractions beyond what the workflows need.
- Not production-grade. The registry is a JSON file. The planner is procedural. There's no auth, no retries beyond a basic one, no rate limiting.
- Not a content product. The seeded wiki is a starting point.
- Not a wiki viewer. The studio observes and initiates; reading wiki content is a job for Obsidian, mkdocs, or a separate v0.2 app.
- Not the same thing as `aoa-knowledge`.

## Reuse from sibling repos

We use almost nothing from existing repos as code. Reuse here means **reuse of agents across workflows** within this repo.

| Source | What we take | What we re-do |
|---|---|---|
| `aoa-a2a-core` | Capability card schema (kept aligned, not imported). A2A request/response shape (mimicked). | Registry, planner, A2A boundary — reimplemented small. |
| `aoa-a2a-agents` | The four-part AU anatomy. | The agents themselves; workflows differ. |
| `aoa-a2a-cv-fit-for-job` | Prompt scaffolding for `evaluator-cv` and `parser-cv`. CVs and JDs are synthetic, authored fresh for the course. | Agent code; reshaped to fit the AU anatomy used here. |
| `aoa-a2a-intent-studio` | Visual vocabulary for the studio. | Code; built fresh. |
| `aoa-knowledge/wiki/` | Six concept pages, vendored into `system/seed-wiki/`. | Course wiki _grows_ from those six during S4. |

## Build order

1. ~~Repo created, this document and `AGENTS.md` written.~~
2. `agents/_base/base.py` — the shared FastAPI scaffold. Boot-time registration. `skills.md` hot reload.
3. `services/registry/` — capability card loading, `cards.json` watching, lookup endpoint.
4. `services/planner/` — registry lookup, agent invocation, trace recording.
5. `services/studio/` — registry pane, trace pane, capability card pane, intent submission. Get it lighting up while the agents are still stubbed.
6. `tools/filesystem/` — the MCP filesystem server, registered as `tool-filesystem`.
7. `agents/parser/`, `agents/evaluator/`, `agents/reporter/` with their S2 capabilities. End of S2 buildable subset.
8. `services/watcher/` and S4 capability additions.
9. `agents/promoter/`, `agents/searcher/` — the new S4 codebases.
10. End-to-end verify, pin SHA by 11 May 2026.
