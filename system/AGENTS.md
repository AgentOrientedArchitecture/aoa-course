# How agents work in this system

Read [`ARCHITECTURE.md`](ARCHITECTURE.md) first for the system as a whole. This document zooms into one agent.

## The four parts

Every Agentic Unit has four addressable parts:

```
agents/<name>/
  agent.py                 # 4. wiring — model + capabilities + skills + tools
  capabilities/
    <capability>/
      capability-card.yaml # 1. the contract
      skills.md            # 2. practical know-how
      tools.yaml           # 3. tool dependencies (capability ids)
```

**1. Capability card** — the contract. Public. Names the capability, declares its inputs and outputs, the constraints any output must satisfy, the evaluation signals the system can check, and provenance. At runtime the shared scaffold stamps the card with `agent_id`/`identity`; the registry then stamps lifecycle governance actors such as `published_by` and `approved_by`. Schema is in [`ARCHITECTURE.md`](ARCHITECTURE.md#capability-card-schema). Mounted read-only and exposed at `/cards/<id>`.

**2. `skills.md`** — practical know-how for fulfilling this capability: prompt structure, judgement rubric, examples, edge-case guidance. This shapes the capability's working behaviour. Two governed agents can run the same code and tools but behave differently because their capability card and `skills.md` are different. Edits show up as a changed `skills_hash`; the Agent ID stays stable.

It's mounted read-only and **hot-reloaded**: a watcher inside the container re-reads `skills.md` when it changes. Editing `skills.md` on disk changes the capability's behaviour without a restart.

**3. `tools.yaml`** — capability ids this agent calls. In this course system
the examples use pure tools here, exposed as MCP tools behind registered AOA
bridges. The planner is responsible for AU-to-AU A2A orchestration. May be
empty for AUs that don't need anything beyond their model — the reporter is the
example.

```yaml
needs:
  - tool-document-text
  - parser-cv
```

The agent resolves these at boot through the registry and the resulting handles are passed into `agent.py`.

**4. `agent.py`** — wiring between the three above and a model. Built on the shared FastAPI scaffold in `agents/_base/`. A typical agent file is short — most of the agent is its `skills.md`.

## One codebase, many agents

When an agent codebase backs more than one capability, the capability-specific files live in `capabilities/<name>/` subfolders. The `agent.py` at the agent root is shared.

The parser demonstrates the main course pattern. `cv-parser` and `wiki-parser`
are different Docker services with different Agent IDs, but both are built from
the same `agents/parser/Dockerfile`, run the same `agent.py`, use the same
model, and call the same document-text tool for document parsing. Their
different capability cards and `skills.md` files give them different contracts
and behaviour.

The evaluator at the end of Session 4:

```
agents/evaluator/
  agent.py
  capabilities/
    cv/
      capability-card.yaml      # id: evaluator-cv
      skills.md                 # rubric for CV-vs-JD fit
      tools.yaml
    promote/
      capability-card.yaml      # id: evaluator-promote
      skills.md                 # rubric for wiki promotion
      tools.yaml
    wiki-query/
      capability-card.yaml      # id: evaluator-wiki-query
      skills.md                 # rubric for retrieved wiki evidence
      tools.yaml
```

Each container registers the capabilities allowed for that runtime at boot. The
registry lists separate rows. The studio shows separate cards. A single
codebase can therefore produce multiple governed agents when Compose supplies
different `AGENT_ID` and `CAPABILITY_ALLOWLIST` values.

Every agent uses the `capabilities/<name>/` pattern even when there's only one capability — it makes adding a second capability a structural copy rather than a refactor.

## Registration

At container boot, `agent.py` (via `_base`) does:

1. Load every `capability-card.yaml` under `capabilities/`.
2. Compute `skills_hash` for each by SHA-ing the matching `skills.md`.
3. Stamp `agent_id` and `identity` onto each card from the container environment.
4. Resolve listed `tools.yaml` capabilities through the registry, retrying until they're up.
5. POST each card to the registry's `/register` endpoint with `provenance.skills_hash` filled in. The registry adds lifecycle fields for publisher, approver, reviewer, and status.
6. Start the FastAPI server on the standard in-container agent port `8888`.
   Expose A2A at `/a2a`, publish an Agent Card at
   `/.well-known/agent-card.json`, and keep `/invoke?capability=<id>` plus
   `/cards/<id>` for compatibility and inspection.

The registry stores cards in `cards.json`, watches that file for external edits, and broadcasts changes to subscribers (the studio).

## Hot reload

A file watcher inside each agent container watches every mounted `skills.md`. On change:

1. Re-read `skills.md`.
2. Recompute `skills_hash`.
3. POST the updated card to the registry's `/update` endpoint.
4. Continue serving requests, using the new `skills.md` from the next invocation onwards.

There is no restart. The studio's registry pane updates the `skills_hash` for that one capability while everything else stays still.

## Invocation

The planner gives the planner model compact registry context and asks for a
task plan. The runtime validates that plan against capability cards before
executing it, falling back to the deterministic course plan if needed. Once a
task is bound to an AU capability, the selected card includes `a2a_endpoint`,
so the planner sends an A2A JSON-RPC request:

```json
POST http://evaluator:8888/a2a
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "...",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "...",
      "role": "user",
      "parts": [
        {
          "kind": "data",
          "data": {
            "inputs": {
              "question": "Why does observed behaviour matter?",
              "query": { "terms": ["observed behaviour", "registry"] }
            }
          }
        }
      ],
      "metadata": {
        "trace_id": "...",
        "aoa_capability": "evaluator-wiki-query"
      }
    }
  }
}
```

The agent looks up the capability locally, builds the prompt from `skills.md`,
calls the model when that capability needs model judgement, computes the
focused signals implemented in `agent.py`, and returns an A2A message with the
AOA result envelope in a `DataPart`:

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "result": {
    "kind": "message",
    "role": "agent",
    "parts": [
      {
        "kind": "data",
        "data": {
          "outputs": {},
          "signals": {
            "all_passages_have_citation": true,
            "score_distribution_not_degenerate": true,
            "latency_p95_under(8s)": 4.2
          }
        }
      }
    ]
  }
}
```

Both the orchestrator-level request/response and the AU/tool boundary records
are written to the planner's trace file for that flow. The studio renders
those records as the responsibility walk.

`/invoke?capability=<id>` remains available as a simple compatibility endpoint
and is the AOA bridge shape deterministic MCP-backed tools use. The course
point is visible in the registry card: AUs advertise `endpoint`,
`agent_card_url`, and `a2a_endpoint`; tools advertise only `endpoint`.

The Docker-internal Agent Card URLs use service names, for example
`http://cv-parser:8888/.well-known/agent-card.json`. Host ports are mapped only
so you can inspect agents from the laptop, such as `http://localhost:7301/` for
`cv-parser` and `http://localhost:7304/` for `wiki-parser`.

## Adding a new capability to an existing agent

1. Create `agents/<name>/capabilities/<new-capability>/`.
2. Write `capability-card.yaml`, `skills.md`, `tools.yaml`.
3. Restart the agent container.

Hot reload watches existing `skills.md` files; discovering a new capability
folder is a boot-time operation. After the restart, the registry picks up the
new capability and the studio shows it. No code changes elsewhere.

## Adding a new agent

1. Create `agents/<name>/` with `agent.py`, `Dockerfile`, and at least one capability folder.
2. Add the agent to `docker-compose.yml`.
3. `docker compose up <name>`.

The agent registers on boot. The studio shows the new capability.

The shared scaffold in `_base/base.py` keeps a new `agent.py` typically under 100 lines.

## Conventions

- **Capability ids are kebab-case**, namespaced by purpose: `evaluator-cv`, `parser-notes`, `tool-document-text`.
- **Agent codebase names are singular nouns**: `evaluator`, not `evaluators`.
- **`skills.md` is markdown, not YAML.** Prose and examples — capabilities are taught, not configured.
- **`evaluation_signals` are booleans or numeric thresholds**, never free-form. They have to be machine-checkable.
- **Models are referenced via `${MODEL}` in cards**, never hard-coded.
- **A capability has at most one `skills.md`.** If you find yourself wanting two, you probably want two capabilities.

## Tools (non-AU registered capabilities)

Tools live under `tools/<name>/` rather than `agents/<name>/`. Same shape, with two differences:

- The capability card has `kind: tool` and `provenance.model: none`.
- There's no `skills.md` — tools are deterministic; their behaviour is in their code.

Tools register the same way agents do and are discovered through the same
registry. The selected card tells the caller how to proceed: AUs include an
`a2a_endpoint`; tools expose a registered bridge `endpoint`.

The filesystem, document text extractor, and wiki store are MCP-backed examples. See
[`tools/filesystem/`](tools/filesystem/) and
[`tools/document-text/`](tools/document-text/) plus
[`tools/wiki-store/`](tools/wiki-store/).
