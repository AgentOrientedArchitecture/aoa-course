# Architecture

A small, container-shaped, readable AOA system. Three workflows, five agents, eight registered capabilities, one MCP tool, four services. Around 2,200 lines of Python including tests.

## What the system does

Three workflows run through one registry:

**CV evaluation** (Session 2):

```
parser-cv → evaluator-cv → reporter-cv-fit
```

You submit a CV and a job description through the studio. The planner queries the registry for `parser-cv` and calls it; the parser returns structured CV data. The planner then calls `evaluator-cv` with the parsed CV and the job description; the evaluator returns scores and a verdict. Finally the planner calls `reporter-cv-fit`, which produces a structured fit-verdict report. Every step is visible in the studio's trace pane.

**Knowledge management** (Session 4) adds two more workflows on the same agents:

```
ingest:   parser-notes → evaluator-ingest → (gate)         → raw/
promote:  promoter                                          → wiki/
query:    searcher → evaluator-query → reporter-answer      → answer
```

Notice that the query workflow has the same shape as the CV workflow: three agents in a chain, the middle one is the evaluator. The chain you build in Session 2 turns out to be general.

## Six things this system demonstrates

Each is something you can see on screen as you build:

1. **An Agentic Unit is `model + capability + skills.md + maybe tools`.** Some AUs have no tools — the reporter is the example. Read any agent folder to see all four parts.
2. **A registered capability isn't always an AU.** The MCP filesystem server in `tools/` registers in the same registry the agents use. The registry holds capabilities; whether they're fulfilled by an AU or by a deterministic tool is a property of the entry, not of the registry.
3. **One agent can back many capabilities.** The evaluator codebase backs three registered capabilities by the end of Session 4 (`evaluator-cv`, `evaluator-ingest`, `evaluator-query`). The studio shows them as three rows.
4. **`skills.md` gives a capability its identity.** Same model, same code, same tools — different `skills.md`, different capability. Edit `evaluator-query/skills.md` while the system is running and you'll see that one entry's `skills_hash` change in the registry pane while everything else holds.
5. **The architecture is indifferent to where reasoning happens.** Switch the model from a hosted API to local Ollama through `.env`; nothing else changes.
6. **Intent is a first-class surface.** The studio is how a human hands intent into the system. The architecture is a layered handover: intent → plan → capability → tool.

## The agent set

Five agent codebases:

| Codebase | Session 2 capabilities | Session 4 capabilities |
|---|---|---|
| `parser` | `parser-cv` | `parser-cv`, `parser-notes` |
| `evaluator` | `evaluator-cv` | `evaluator-cv`, `evaluator-ingest`, `evaluator-query` |
| `reporter` | `reporter-cv-fit` | `reporter-cv-fit`, `reporter-answer` |
| `promoter` | — | `promoter` |
| `searcher` | — | `searcher` |

Plus, in `tools/`:

| Tool | Registered as | Type |
|---|---|---|
| filesystem MCP server | `tool-filesystem` | non-AU registered capability |

## The four parts of an AU

Every AU has four addressable parts:

1. **Capability card** (`capability-card.yaml`) — the contract. Public. Mounted read-only and exposed at `/cards/<id>`.
2. **`skills.md`** — practical know-how for fulfilling the capability: prompt structure, judgement rubric, examples, edge cases. Mounted read-only and **hot-reloaded** — editing it on disk changes the capability's behaviour without a restart.
3. **`tools.yaml`** — the capability ids this agent will call. May reference other AUs or pure tools. May be empty.
4. **`agent.py`** — the wiring. Built on the shared FastAPI scaffold in `agents/_base/`.

When a single codebase backs more than one capability, the capability-specific files live in `capabilities/<name>/` subfolders; the code lives at the agent root. Every agent uses this pattern even when it has only one capability.

## Plumbing services

| Service | Job |
|---|---|
| **registry** | Loads capability cards on startup. Watches `cards.json` for changes. Exposes `find_capability(intent)` and `list_capabilities()` over HTTP. |
| **planner** | Receives intents from the studio. Queries the registry. Sequences agent invocations. Records each step to `traces/<event-id>.jsonl`. |
| **studio** | Browser surface at `localhost:8080`. Three panes — registry, trace, capability card — plus an intent submission box and file drop. Subscribes to traces and registry changes via SSE. |
| **watcher** | Watches `inbox/` for new files. Posts ingest events to the planner. (Session 4 only.) |

## Container topology

Each agent and each service runs in its own container. Compose orchestrates.

```
docker-compose.yml services:

  registry             FastAPI    7100
  planner              FastAPI    7200
  studio               FastAPI    8080
  watcher              (S4)       no port
  parser               FastAPI    7301
  evaluator            FastAPI    7302
  reporter             FastAPI    7303
  promoter             (S4)       7304
  searcher             (S4)       7305
  tool-filesystem      MCP        7401
  ollama               profile: local, optional
```

Eight containers at the end of Session 2; eleven at the end of Session 4.

Every agent container has the same shape: a FastAPI app that mounts its `capabilities/` folder as a volume, registers itself with the registry on boot, exposes `/invoke` and `/cards/<id>`, and watches mounted `skills.md` files for hot reload. Read one agent and you've read them all.

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

The three evaluator capability cards differ in `purpose`, `inputs`, `outputs`, `constraints`, `evaluation_signals`, `skills.md`, and the `endpoint` path. They share `agent.py` and `model`. Pure tools have `kind: tool` and `provenance.model: none`; the planner doesn't branch on `kind`.

## The studio

A browser surface at `localhost:8080` with two roles:

**Observation:**

- **Registry pane.** Live listing of every registered capability — id, version, kind (`au` or `tool`), backing agent, current `skills_hash`. Updates as capabilities register, deregister, or change.
- **Trace pane.** The currently-running flow as a vertical timeline. Each row shows planner → registry lookup, agent invocation, response. Rows are collapsible for full payloads. Finished flows persist until the next intent runs.
- **Capability card pane.** Click any registry entry to see its card formatted.

**Intent:**

- **Submit an intent.** Free-form text, sent to the planner.
- **Drop a file.** Drag a CV (Session 2) or a research note (Session 4) onto the page.

The studio is for observing and driving the system. It doesn't browse the wiki — point Obsidian or any markdown viewer at `system/wiki/` for that.

## Running locally

`docker compose up` brings everything alive. Open `http://localhost:8080` and you'll see the registry pane populate as agents come up.

Configure the model via `.env`:

```
PROVIDER=openai|anthropic|ollama
MODEL=…
```

Switching from a hosted API to Ollama is a `.env` change and a `docker compose up` away. The registry, the agents, the capability cards, and the planner all stay still.
