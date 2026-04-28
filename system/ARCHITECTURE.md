# Architecture

A small, container-shaped, readable AOA system. Three workflows, three agent
codebases, ten AU capabilities, three deterministic tools, and three plumbing
services. AU-to-AU orchestration uses A2A Agent Cards and JSON-RPC
`message/send`; deterministic tools expose MCP tools behind small registered
AOA bridges.

## What the system does

Two workflows run through one registry:

**CV evaluation** (Session 2):

```
parser-cv → evaluator-cv → reporter-cv-fit
```

You submit a CV and a job description through the studio. The planner queries
the registry for `parser-cv` and starts it with A2A `message/send`; the parser
returns structured CV data. The planner then starts `evaluator-cv` with the
parsed CV and the job description; the evaluator returns scores and a verdict.
Finally the planner starts `reporter-cv-fit`, which produces a structured
fit-verdict report. Every step is visible in the studio's trace pane.

**Knowledge ingest** (Session 4) starts the wiki-management loop:

```
parser-notes → evaluator-promote → reporter-ingest-summary
```

You submit source material through the studio. The parser extracts citeable
passages and concepts. The evaluator decides which material should be promoted
into the course wiki. The reporter writes the promoted layer through
`tool-wiki-store` and returns a Markdown ingest summary.

**Knowledge query** (Session 4) then uses the stored wiki:

```
parser-query → evaluator-wiki-query → reporter-answer
```

You submit a question through the studio. The parser turns it into a compact
retrieval query. The evaluator searches the wiki store, ranks retrieved
passages, and names gaps. The reporter writes a grounded answer with passage-id
citations. The chain you build in Session 2 turns out to be general, but now
it supports both ingest and access.

## Six things this system demonstrates

Each is something you can see on screen as you build:

1. **An Agentic Unit is `model + capability + skills.md + maybe tools`.** Some AUs have no tools — the reporter is the example. Read any agent folder to see all four parts.
2. **A registered capability isn't always an AU.** The tools in `tools/` register in the same registry the agents use. The registry holds capabilities; whether they're fulfilled by an AU over A2A or by a deterministic tool exposed through MCP is a property of the entry, not of the registry.
3. **One agent can back many capabilities.** Each Session 2 agent gains extra Session 4 capabilities: `parser-notes`, `parser-query`, `evaluator-promote`, `evaluator-wiki-query`, `reporter-ingest-summary`, and `reporter-answer`. The studio shows them as separate rows even though the codebases are reused.
4. **`skills.md` gives a capability its identity.** Same model, same code, same tools — different `skills.md`, different capability. Edit `evaluator-query/skills.md` while the system is running and you'll see that one entry's `skills_hash` change in the registry pane while everything else holds.
5. **The architecture is indifferent to where reasoning happens.** Switch from a local smaller model to a hosted OpenAI-compatible endpoint through `.env`; nothing else changes.
6. **Intent is a first-class surface.** The studio is how a human hands intent into the system. The architecture is a layered handover: intent → capability-aware planning → validation → discovery/selection → A2A orchestration → tool.

## The agent set

Three agent codebases:

| Codebase | Session 2 capabilities | Session 4 capabilities |
|---|---|---|
| `parser` | `parser-cv` | `parser-notes`, `parser-query` |
| `evaluator` | `evaluator-cv` | `evaluator-query`, `evaluator-promote`, `evaluator-wiki-query` |
| `reporter` | `reporter-cv-fit` | `reporter-answer`, `reporter-ingest-summary` |

Plus, in `tools/`:

| Tool | Registered as | Type |
|---|---|---|
| filesystem MCP server | `tool-filesystem` | non-AU registered capability |
| document text MCP server | `tool-document-text` | non-AU registered capability |
| wiki store MCP server | `tool-wiki-store` | non-AU registered capability |

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
| **registry** | Loads capability cards on startup. Watches `cards.json` for changes. Exposes direct lookup, listing, and deterministic capability discovery over HTTP. |
| **planner** | Receives intents from the studio. Gives the planner model compact registry context, validates the proposed plan, falls back if needed, sequences AU invocations with A2A `message/send`, and calls registered tool bridges for deterministic MCP-backed tools. Records each step to `traces/<event-id>.jsonl`. |
| **studio** | Browser surface at `localhost:8080`. Three panes — registry, trace, capability card — plus an intent submission box and file drop. Subscribes to traces and registry changes via SSE. |

## Container topology

Each agent and each service runs in its own container. Compose orchestrates.

```
docker-compose.yml services:

  registry             FastAPI    7100
  planner              FastAPI    7200
  studio               FastAPI    8080
  parser               FastAPI    8888 (host: 7301)
  evaluator            FastAPI    8888 (host: 7302)
  reporter             FastAPI    8888 (host: 7303)
  tool-filesystem      MCP        7401
  tool-document-text   MCP+bridge 7402
  tool-wiki-store      MCP+bridge 7403
  ollama               profile: local, optional
```

Nine containers run for both sessions, plus optional Ollama under the local
profile.

Every agent container has the same shape: a FastAPI app that mounts its
`capabilities/` folder as a volume, registers itself with the registry on boot,
exposes `/a2a`, `/.well-known/agent-card.json`, `/invoke`, and `/cards/<id>`,
and watches mounted `skills.md` files for hot reload. Read one agent and
you've read them all.

## A2A surface

Each AU process publishes a genuine A2A Agent Card at
`/.well-known/agent-card.json`. Inside the Docker network these resolve to
container-local addresses such as
`http://parser:8888/.well-known/agent-card.json`, and the card's `url` points
at `http://parser:8888/a2a`. The card includes standard A2A fields such as
`protocolVersion`, `url`, `preferredTransport`, default input/output modes, and
`skills`. A2A skills are intentionally lighter than AOA capability cards, so
the full capability-card contracts are also advertised through an A2A
`capabilities.extensions` entry.

The planner still uses the AOA registry to ground concrete capabilities. In
this small course registry it sends compact AU capability summaries to the
planner model and asks for a JSON task plan. The runtime validates that the
plan uses registered capabilities, maps required inputs, references only
available prior outputs, and ends in a markdown-producing result. If validation
fails, the deterministic course plan is used. When a registered card includes
`a2a_endpoint`, the planner sends a JSON-RPC 2.0 request to that endpoint:

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "data",
          "data": {
            "inputs": {}
          }
        }
      ],
      "metadata": {
        "aoa_capability": "parser-cv",
        "trace_id": "..."
      }
    }
  }
}
```

The agent replies with an A2A message. The structured AOA envelope lives in a
`DataPart` so the planner can keep the same trace and workflow code. Reporter
agents may also include a text part containing markdown for inline rendering.
`/invoke` remains available as a compatibility endpoint and as the AOA bridge
surface used by deterministic MCP-backed tools.

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
endpoint: http://evaluator:8888/invoke
agent_card_url: http://evaluator:8888/.well-known/agent-card.json
a2a_endpoint: http://evaluator:8888/a2a
```

The three evaluator capability cards differ in `purpose`, `inputs`, `outputs`,
`constraints`, `evaluation_signals`, `skills.md`, and the registered
endpoints. They share `agent.py` and `model`. Pure tools have `kind: tool` and
`provenance.model: none`; they register `endpoint` only.

## The studio

A browser surface at `localhost:8080` with two roles:

**Observation:**

- **Registry pane.** Live listing of every registered capability — id, version, kind (`au` or `tool`), backing agent, current `skills_hash`. Updates as capabilities register, deregister, or change.
- **Intent Studio pane.** The currently-running flow as a visual lifecycle: intent, available capability context, planner proposal, validation/fallback, task plan, work status, and rendered result. Raw event payloads are still available in an expandable details section.
- **Right detail pane.** Click any registry entry to see its capability card, or
  click a wiki graph node to inspect that document, concept, passage, or open
  question.

**Intent:**

- **Submit an intent.** Free-form text, sent to the planner.
- **Choose a mode.** CV fit for Session 2; ingest, graph, and wiki query for Session 4.
- **Drop a file.** Drag a CV, job description, or research note into the relevant field.
- **Inspect the wiki graph.** The Session 4 wiki store projects its raw,
  promoted, and indexed knowledge into typed graph nodes. Documents, concepts,
  passages, and open questions use different shapes and colours. The graph is
  its own mode, not part of the CV workflow.

The studio is for observing and driving the system. In the cut-down knowledge-management workflows, the ingest summary and grounded answer appear as final trace outputs.

## Running locally

Use Docker Compose profiles to start the part of the system needed for the
session.

Session 2 starts only the CV-fit path:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  -f system/docker-compose.session2.yml \
  --profile session2 \
  up --build -d
```

Session 4 starts the full knowledge-management path:

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  --profile session4 \
  up --build -d
```

Open `http://localhost:8080` and you'll see the registry pane populate as
agents and tools register.

Configure the model via `.env`:

```
PROVIDER=ollama|openai|anthropic
MODEL=...
OPENAI_BASE_URL=...   # optional for OpenAI-compatible hosted providers
```

The intended baseline is a smaller model, for example `gpt-oss:120b` or a
Qwen-family model, run locally through Ollama or through a service provider.
Switching model, provider, or hosting location is a `.env` change and a
Compose restart away. The registry, the agents, the capability cards, and the
planner all stay still.
