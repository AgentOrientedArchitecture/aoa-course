# How agents in this system work

This document describes the agent shape used inside `system/`. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) first for the system as a whole; this document zooms into one agent.

## The four parts

Every Agentic Unit in this repo has four addressable parts:

```
agents/<name>/
  agent.py                 # 4. wiring — model + capability + skills + tools
  capabilities/
    <capability>/
      capability-card.yaml # 1. the contract
      skills.md            # 2. practical know-how
      tools.yaml           # 3. tool dependencies (capability ids)
```

**1. Capability card** — the contract. Public. Names this capability, declares its inputs and outputs, declares the constraints any output must satisfy, declares the evaluation signals the system can check, declares provenance. Schema is documented in [`ARCHITECTURE.md`](ARCHITECTURE.md#capability-card-schema). Mounted read-only into the container, exposed at `/cards/<id>`.

**2. `skills.md`** — practical know-how for fulfilling this capability. Prompt structure, judgement rubric, examples, edge-case guidance. This is what gives a capability its identity. Two capabilities backed by the same code differ here.

Mounted read-only into the container and **hot-reloaded**: a file watcher inside the container re-reads `skills.md` on change. Editing `skills.md` on the host changes the capability's behaviour without a restart and without any other component being aware.

**3. `tools.yaml`** — capability ids the agent will call. May reference other AUs (calling another agent via A2A) or pure tools (calling an MCP server registered as a tool). May be empty for AUs that don't need anything beyond their model — the reporter is the example.

```yaml
needs:
  - tool-filesystem        # the MCP filesystem server
  - parser-cv              # an A2A call to the parser
```

The agent resolves these at boot through the registry, and the resulting handles are passed into `agent.py`.

**4. `agent.py`** — wiring between the three above and a model. Built on the shared FastAPI scaffold in `agents/_base/`. A typical agent file is short (~50–100 lines) because most of the agent is its `skills.md`.

## How an agent serves multiple capabilities

When an agent codebase backs more than one capability, the capability-specific files live in `capabilities/<name>/` subfolders. The `agent.py` at the agent root is shared.

Example — the evaluator at S4 end:

```
agents/evaluator/
  agent.py
  capabilities/
    cv/
      capability-card.yaml      # id: evaluator-cv
      skills.md                 # rubric for CV-vs-JD fit
      tools.yaml
    ingest/
      capability-card.yaml      # id: evaluator-ingest
      skills.md                 # rubric for raw note quality
      tools.yaml
    query/
      capability-card.yaml      # id: evaluator-query
      skills.md                 # rubric for passage relevance
      tools.yaml
```

The container registers three capabilities at boot. The registry lists three rows. The studio shows three cards. The same Python process serves all three. **The registry is a capability registry, not an agent registry.**

Every agent uses the `capabilities/<name>/` pattern even when it currently has only one capability. This sets the expectation that any agent might gain a second.

## How a capability is registered

At container boot, `agent.py` (via the shared `_base` scaffold) does:

1. Loads every `capability-card.yaml` under its `capabilities/` folder.
2. Computes `skills_hash` for each by SHA-ing the matching `skills.md`.
3. Resolves the listed `tools.yaml` capabilities through the registry, retries until they're all up.
4. POSTs each card to the registry's `/register` endpoint with `provenance.skills_hash` filled in.
5. Starts the FastAPI server and exposes `/invoke?capability=<id>` and `/cards/<id>`.

The registry stores the cards in `cards.json`, watches that file for external edits, and broadcasts changes to subscribers (the studio).

## How `skills.md` hot reload works

A file watcher inside the agent container watches every mounted `skills.md`. On change:

1. Re-read `skills.md`.
2. Recompute `skills_hash`.
3. POST the updated card to the registry's `/update` endpoint.
4. Continue serving requests using the new `skills.md` from the next invocation.

There is no restart. The audience sees the registry pane in the studio update the `skills_hash` for one capability while everything else stays still. Subsequent invocations of that capability behave differently. No other component needs to know.

## How an agent gets called

The planner asks the registry for a capability id, gets back a card (including the `endpoint`), and POSTs an invocation:

```
POST http://evaluator:7302/invoke?capability=evaluator-query
Content-Type: application/json

{
  "trace_id": "…",
  "inputs": { … }
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

## What an agent is not

- **Not a microservice**. It happens to run as a container with an HTTP endpoint, but its identity comes from its capability cards, not from its hostname.
- **Not a workflow**. Agents don't know about workflows. The planner sequences them.
- **Not a shared library**. Code reuse across agents is limited to the `_base` scaffold and the model client. Each agent is independently readable.
- **Not coupled to a model**. Models are configured via `.env` (`PROVIDER` and `MODEL`). Agents see a single `model.complete(prompt)` call.

## How to add a new capability to an existing agent

This is the move S4 makes four times in a row. The path is:

1. Create `agents/<name>/capabilities/<new-capability>/`.
2. Write `capability-card.yaml`, `skills.md`, `tools.yaml`.
3. Restart the agent container (or wait for hot reload, depending on your dev loop).
4. The registry picks up the new capability. The studio shows it.

No code changes. No other agents aware.

## How to add a new agent

This is the move S4 makes twice (`promoter`, `searcher`):

1. Create `agents/<name>/` with `agent.py`, `Dockerfile`, `capabilities/<capability>/{capability-card.yaml, skills.md, tools.yaml}`.
2. Add the agent to `docker-compose.yml`.
3. `docker compose up <name>`.
4. The agent registers on boot. The studio shows the new capability.

The shared `_base/base.py` scaffold means a new agent's `agent.py` is typically less than 100 lines.

## Conventions

- **Capability ids are kebab-case**, namespaced by purpose (`evaluator-cv`, `parser-notes`, `tool-filesystem`).
- **Agent codebase names are singular nouns** (`evaluator`, not `evaluators`).
- **`skills.md` is markdown, not YAML**. It's prose for a reason — capabilities are taught through example.
- **`evaluation_signals` are booleans or numeric thresholds**, never free-form. They have to be machine-checkable.
- **Models are referenced via `${MODEL}` in cards**, never hardcoded.
- **A capability has at most one `skills.md`**. If you find yourself wanting two, you probably want two capabilities.

## Conventions for tools (non-AU registered capabilities)

Tools live under `tools/<name>/` rather than `agents/<name>/`. They follow the same shape, with two differences:

- Their capability card has `kind: tool` and `provenance.model: none`.
- They have no `skills.md`. They are deterministic; their behaviour is in their code.

Tools register the same way agents do. They are looked up the same way. The planner doesn't distinguish between calling an agent and calling a tool — both come back from `find_capability(id)` with an `endpoint`.

The MCP filesystem server is the example.
