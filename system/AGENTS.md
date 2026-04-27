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

**1. Capability card** — the contract. Public. Names the capability, declares its inputs and outputs, the constraints any output must satisfy, the evaluation signals the system can check, and provenance. Schema is in [`ARCHITECTURE.md`](ARCHITECTURE.md#capability-card-schema). Mounted read-only and exposed at `/cards/<id>`.

**2. `skills.md`** — practical know-how for fulfilling this capability: prompt structure, judgement rubric, examples, edge-case guidance. This is what gives a capability its identity. Two capabilities backed by the same code differ here.

It's mounted read-only and **hot-reloaded**: a watcher inside the container re-reads `skills.md` when it changes. Editing `skills.md` on disk changes the capability's behaviour without a restart.

**3. `tools.yaml`** — capability ids this agent calls. May reference other AUs (an A2A call to another agent) or pure tools (an MCP call to a registered tool). May be empty for AUs that don't need anything beyond their model — the reporter is the example.

```yaml
needs:
  - tool-document-text
  - parser-cv
```

The agent resolves these at boot through the registry and the resulting handles are passed into `agent.py`.

**4. `agent.py`** — wiring between the three above and a model. Built on the shared FastAPI scaffold in `agents/_base/`. A typical agent file is short — most of the agent is its `skills.md`.

## One codebase, many capabilities

When an agent codebase backs more than one capability, the capability-specific files live in `capabilities/<name>/` subfolders. The `agent.py` at the agent root is shared.

The evaluator at the end of Session 4:

```
agents/evaluator/
  agent.py
  capabilities/
    cv/
      capability-card.yaml      # id: evaluator-cv
      skills.md                 # rubric for CV-vs-JD fit
      tools.yaml
    query/
      capability-card.yaml      # id: evaluator-query
      skills.md                 # rubric for passage relevance
      tools.yaml
```

The container registers two capabilities at boot. The registry lists two rows. The studio shows two cards. One Python process serves both.

Every agent uses the `capabilities/<name>/` pattern even when there's only one capability — it makes adding a second capability a structural copy rather than a refactor.

## Registration

At container boot, `agent.py` (via `_base`) does:

1. Load every `capability-card.yaml` under `capabilities/`.
2. Compute `skills_hash` for each by SHA-ing the matching `skills.md`.
3. Resolve listed `tools.yaml` capabilities through the registry, retrying until they're up.
4. POST each card to the registry's `/register` endpoint with `provenance.skills_hash` filled in.
5. Start the FastAPI server. Expose `/invoke?capability=<id>` and `/cards/<id>`.

The registry stores cards in `cards.json`, watches that file for external edits, and broadcasts changes to subscribers (the studio).

## Hot reload

A file watcher inside each agent container watches every mounted `skills.md`. On change:

1. Re-read `skills.md`.
2. Recompute `skills_hash`.
3. POST the updated card to the registry's `/update` endpoint.
4. Continue serving requests, using the new `skills.md` from the next invocation onwards.

There is no restart. The studio's registry pane updates the `skills_hash` for that one capability while everything else stays still.

## Invocation

The planner asks the registry for a capability, gets back a card (including `endpoint`), and POSTs an invocation:

```
POST http://evaluator:7302/invoke?capability=evaluator-query
Content-Type: application/json

{
  "trace_id": "…",
  "inputs": {
    "question": "Why does observed behaviour matter?",
    "parsed_note": { "passages": [] }
  }
}
```

The agent looks up the capability locally, builds the prompt from `skills.md`, calls the model, validates the response against the capability card's `constraints`, runs the `evaluation_signals` checks, and returns:

```
{
  "trace_id": "…",
  "outputs": { … },
  "signals": {
    "all_passages_have_citation": true,
    "score_distribution_not_degenerate": true,
    "latency_p95_under(8s)": 4.2
  }
}
```

Both the request and response are written to the planner's trace file for that flow. The studio renders them.

## Adding a new capability to an existing agent

1. Create `agents/<name>/capabilities/<new-capability>/`.
2. Write `capability-card.yaml`, `skills.md`, `tools.yaml`.
3. Restart the agent container (or wait for hot reload, depending on your loop).

The registry picks up the new capability. The studio shows it. No code changes elsewhere.

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

Tools register the same way agents do and are looked up the same way. The planner doesn't distinguish between calling an agent and calling a tool — both come back from `find_capability(id)` with an `endpoint`.

The MCP filesystem server and document text extractor are the examples. See
[`tools/filesystem/`](tools/filesystem/) and
[`tools/document-text/`](tools/document-text/).
