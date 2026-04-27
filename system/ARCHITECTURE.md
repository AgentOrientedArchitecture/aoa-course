# Architecture

A small, container-shaped, readable AOA system. Two workflows, three agent
codebases, six AU capabilities, two deterministic tools, and three plumbing
services.

## What the system does

Two workflows run through one registry:

**CV evaluation** (Session 2):

```
parser-cv → evaluator-cv → reporter-cv-fit
```

You submit a CV and a job description through the studio. The planner queries the registry for `parser-cv` and calls it; the parser returns structured CV data. The planner then calls `evaluator-cv` with the parsed CV and the job description; the evaluator returns scores and a verdict. Finally the planner calls `reporter-cv-fit`, which produces a structured fit-verdict report. Every step is visible in the studio's trace pane.

**Knowledge query** (Session 4) reuses the same three-agent shape:

```
parser-notes → evaluator-query → reporter-answer
```

You submit a source note and a question through the studio. The parser reads
the note and extracts citeable passages. The evaluator ranks those passages
against the question. The reporter writes a grounded answer with passage-id
citations and named gaps. The chain you build in Session 2 turns out to be
general.

## Six things this system demonstrates

Each is something you can see on screen as you build:

1. **An Agentic Unit is `model + capability + skills.md + maybe tools`.** Some AUs have no tools — the reporter is the example. Read any agent folder to see all four parts.
2. **A registered capability isn't always an AU.** The tools in `tools/` register in the same registry the agents use. The registry holds capabilities; whether they're fulfilled by an AU or by a deterministic tool is a property of the entry, not of the registry.
3. **One agent can back many capabilities.** Each Session 2 agent gains a second capability in Session 4: `parser-notes`, `evaluator-query`, and `reporter-answer`. The studio shows them as separate rows even though the codebases are reused.
4. **`skills.md` gives a capability its identity.** Same model, same code, same tools — different `skills.md`, different capability. Edit `evaluator-query/skills.md` while the system is running and you'll see that one entry's `skills_hash` change in the registry pane while everything else holds.
5. **The architecture is indifferent to where reasoning happens.** Switch from a local smaller model to a hosted OpenAI-compatible endpoint through `.env`; nothing else changes.
6. **Intent is a first-class surface.** The studio is how a human hands intent into the system. The architecture is a layered handover: intent → plan → capability → tool.

## The agent set

Three agent codebases:

| Codebase | Session 2 capabilities | Session 4 capabilities |
|---|---|---|
| `parser` | `parser-cv` | `parser-cv`, `parser-notes` |
| `evaluator` | `evaluator-cv` | `evaluator-cv`, `evaluator-query` |
| `reporter` | `reporter-cv-fit` | `reporter-cv-fit`, `reporter-answer` |

Plus, in `tools/`:

| Tool | Registered as | Type |
|---|---|---|
| filesystem MCP server | `tool-filesystem` | non-AU registered capability |
| document text extractor | `tool-document-text` | non-AU registered capability |

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

## Container topology

Each agent and each service runs in its own container. Compose orchestrates.

```
docker-compose.yml services:

  registry             FastAPI    7100
  planner              FastAPI    7200
  studio               FastAPI    8080
  parser               FastAPI    7301
  evaluator            FastAPI    7302
  reporter             FastAPI    7303
  tool-filesystem      MCP        7401
  tool-document-text   FastAPI    7402
  ollama               profile: local, optional
```

Eight containers run for both sessions, plus optional Ollama under the local
profile.

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
- **Choose a workflow.** CV fit for Session 2, knowledge query for Session 4.
- **Drop a file.** Drag a CV, job description, or research note into the relevant field.

The studio is for observing and driving the system. In the cut-down knowledge-management workflow, the grounded answer appears as the final trace output.

## Running locally

`docker compose up` brings everything alive. Open `http://localhost:8080` and you'll see the registry pane populate as agents come up.

Configure the model via `.env`:

```
PROVIDER=ollama|openai|anthropic
MODEL=...
OPENAI_BASE_URL=...   # optional for OpenAI-compatible hosted providers
```

The intended baseline is a smaller model, for example `gpt-oss:120b` or a
Qwen-family model, run locally through Ollama or through a service provider.
Switching model, provider, or hosting location is a `.env` change and a
`docker compose up` away. The registry, the agents, the capability cards, and
the planner all stay still.
