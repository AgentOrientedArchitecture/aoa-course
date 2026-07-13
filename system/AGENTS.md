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
      instructions.md            # 2. practical know-how
      tools.yaml           # 3. tool dependencies (capability ids)
```

**1. Capability card** — the contract. Public. Names the capability, declares its inputs and outputs, the constraints any output must satisfy, the evaluation signals the system can check, and provenance. At runtime the shared scaffold stamps the card with `agent_id`/`identity`; the registry then stamps lifecycle governance actors such as `published_by` and `approved_by`. Schema is in [`ARCHITECTURE.md`](ARCHITECTURE.md#capability-card-schema). Mounted read-only in the container, exposed at `/cards/<id>`, and hot-reloaded when its host file changes.

**2. `instructions.md`** — practical know-how for fulfilling this capability: prompt structure, judgement rubric, examples, edge-case guidance. This shapes the capability's working behaviour. Two governed agents can run the same code and tools but behave differently because their capability card and `instructions.md` are different. Edits show up as a changed `skills_hash`; the Agent ID stays stable.

It's mounted read-only and **hot-reloaded**: a watcher inside the container re-reads `instructions.md` when it changes. Editing `instructions.md` on disk changes the capability's behaviour without a restart.

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

**4. `agent.py`** — wiring between the three above and a model. Built on the shared FastAPI scaffold in `agents/_base/`. A typical agent file is short — most of the agent is its `instructions.md`.

## One codebase, many agents

When an agent codebase backs more than one capability, the capability-specific files live in `capabilities/<name>/` subfolders. The `agent.py` at the agent root is shared.

The parser demonstrates the main course pattern. `cv-parser` and `wiki-parser`
are different Docker services with different Agent IDs, but both are built from
the same `agents/parser/Dockerfile`, run the same `agent.py`, use the same
model, and call the same document-text tool for document parsing. Their
different capability cards and `instructions.md` files give them different contracts
and behaviour.

The evaluator grows across the course:

```
agents/evaluator/
  agent.py
  capabilities/
    cv/                 # evaluator-cv: CV-vs-JD fit
    promote/            # evaluator-promote: wiki promotion
    wiki-query/         # evaluator-wiki-query: retrieved wiki evidence
    plan-governance/    # evaluator-plan-governance: deterministic composition gate
    agent-evidence/     # evaluator-agent-evidence: declared card evidence
    flow-evidence/      # evaluator-flow-evidence: post-execution flow evidence
```

Each folder contains its capability card, `instructions.md`, and `tools.yaml`.
The three Session 4 evaluator roles are distinct:
`evaluator-agent-evidence` assesses declared card evidence,
`evaluator-plan-governance` deterministically checks whether a resolved plan is
eligible to run to a held draft, and `evaluator-flow-evidence` assesses observed
exact-result review and release/quarantine evidence after a run.

Each container registers the capabilities allowed for that runtime at boot. The
registry lists separate rows. The studio shows separate cards. A single
codebase can therefore produce multiple governed agents when Compose supplies
different `AGENT_ID` and `CAPABILITY_ALLOWLIST` values.

Every agent uses the `capabilities/<name>/` pattern even when there's only one capability — it makes adding a second capability a structural copy rather than a refactor.

## Registration

At container boot, `agent.py` (via `_base`) does:

1. Load every `capability-card.yaml` under `capabilities/`.
2. Compute `skills_hash` for each by SHA-ing the matching `instructions.md`.
3. Stamp `agent_id` and `identity` onto each card from the container environment.
4. Resolve listed `tools.yaml` capabilities through the registry, retrying until they're up.
5. POST each card to the registry's `/register` endpoint with `provenance.skills_hash` filled in. The registry adds lifecycle fields for publisher, approver, reviewer, and status.
6. Start the FastAPI server on the standard in-container agent port `8888`.
   Expose A2A at `/a2a`, publish an Agent Card at
   `/.well-known/agent-card.json`, and keep `/invoke?capability=<id>` plus
   `/cards/<id>` for compatibility and inspection.

The registry stores cards in `cards.json`, watches that file for external edits, and broadcasts changes to subscribers (the studio).

## Hot reload

A file watcher inside each agent container watches every mounted capability
folder. On an `instructions.md` change it re-reads the instructions, recomputes
`skills_hash`, and updates the registry. On a `capability-card.yaml` change it
re-reads the public contract, restores scaffold-owned identity, model, hash, and
endpoint fields, and updates the registry.

There is no restart. Studio's registry pane shows the affected capability
update. Session 4 uses this to make an `evaluator-cv` constraint edit visible
before the learner reruns Agent card check.

## Invocation

The planner gives the planner model compact registry context and asks for a
task plan. The runtime validates that plan against capability cards, falling
back to the deterministic course plan if needed, and binds each task to a
concrete card. When plan governance is enabled, the planner records the
resolved plan and digest and invokes the control-plane
`evaluator-plan-governance` before any application-card lookup or invocation.
An ineligible plan is rejected before application work. An eligible employment
plan runs application AUs only to a frozen draft; release waits for human review
of the actual output and its exact `result_digest`. Once an application task is
eligible to run, its selected card includes `a2a_endpoint`, so the planner sends
an A2A JSON-RPC request:

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

The agent looks up the capability locally, builds the prompt from `instructions.md`,
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
2. Write `capability-card.yaml`, `instructions.md`, `tools.yaml`.
3. Restart the agent container.

Hot reload watches existing `instructions.md` files; discovering a new capability
folder is a boot-time operation. After the restart, the registry picks up the
new capability and the studio shows it. No code changes elsewhere.

## Adding a new agent

1. Create `agents/<name>/` with `agent.py`, `Dockerfile`, and at least one capability folder.
2. Add the agent to `docker-compose.yml`.
3. `docker compose up <name>`.

The agent registers on boot. The studio shows the new capability.

The shared scaffold in `_base/base.py` keeps a new `agent.py` typically under 100 lines.

## Agents authored with EVE (Session 3)

An Agentic Unit does not have to run on the Python scaffold. Session 3 uses
[Vercel EVE](https://github.com/vercel/eve), a filesystem-first TypeScript
framework. Course-owned image and bridge infrastructure lives under
`agents-eve/runtime/`; learner-owned files live under `agents-eve/workshop/`.

The learner starts with a blank authored surface, runs `eve init .`, adds the
provider-neutral `agent.ts` and bounded `instructions.md`, inspects with
`eve info`, and completes native acceptance tests in `eve dev`. `session3-up` runs
that native EVE environment only; no AOA services or governed identity exist at
this stage.

`session3-adopt` creates `workshop/capability-card.yaml` automatically when it
is missing, then starts AOA and the generic bridge. The bridge stamps identity
and `skills_hash`, registers the card, exposes the A2A surface, and emits the
trace boundary. The same learner files then fulfil the
`interviewer-questions` workflow step without agent-specific adoption code.
Card edits require rerunning `session3-adopt` to revalidate and republish the
contract. Changes made during later native acceptance should likewise be
followed by another adoption run before AOA testing. See [`EVE.md`](EVE.md).

## Conventions

- **Capability ids are kebab-case**, namespaced by purpose: `evaluator-cv`, `parser-notes`, `tool-document-text`.
- **Agent codebase names are singular nouns**: `evaluator`, not `evaluators`.
- **`instructions.md` is markdown, not YAML.** Prose and examples — capabilities are taught, not configured.
- **`evaluation_signals` are booleans or numeric thresholds**, never free-form. They have to be machine-checkable.
- **Models are referenced via `${MODEL}` in cards**, never hard-coded.
- **A capability has at most one `instructions.md`.** If you find yourself wanting two, you probably want two capabilities.

## Tools (non-AU registered capabilities)

Tools live under `tools/<name>/` rather than `agents/<name>/`. Same shape, with two differences:

- The capability card has `kind: tool` and `provenance.model: none`.
- There's no `instructions.md` — tools are deterministic; their behaviour is in their code.

Tools register the same way agents do and are discovered through the same
registry. The selected card tells the caller how to proceed: AUs include an
`a2a_endpoint`; tools expose a registered bridge `endpoint`.

The filesystem, document text extractor, and wiki store are MCP-backed examples. See
[`tools/filesystem/`](tools/filesystem/) and
[`tools/document-text/`](tools/document-text/) plus
[`tools/wiki-store/`](tools/wiki-store/).

## Session 4 - card evidence, result review, and flow audit

Session 4 has exactly three core governance learning stages in Studio:

```text
agent-card-check: parser-estate → evaluator-agent-evidence → reporter-agent-evidence
cv-fit:           parser-cv → evaluator-cv → reporter-cv-fit
flow-audit:       parser-estate → evaluator-flow-evidence → reporter-flow-audit
```

Studio also exposes optional **Graph** and **Ask** evidence-exploration
utilities. Graph visualizes the seeded EU AI Act wiki. Ask reuses the grounded
`knowledge-query` workflow so learners can inspect passage citations and
`tool-wiki-store` retrieval. They are not additional governance stages. Wiki
reset is disabled in Session 4 to protect the governance corpus; rerun the
Session 4 seed script if evidence is missing.

**Agent card check** starts with `evaluator-cv` Article 14 red.
`evaluator-agent-evidence` visibly calls `tool-wiki-store`, and the report keeps
the exact query, passage ID, source, and complete quote inspectable. A learner
may try CV fit at this point and observe deterministic rejection before any
application AU `lookup` or `invoke`.

The learner adds exactly this `evaluator-cv` constraint:

```yaml
- Every verdict is a draft and must be approved by a human reviewer before it informs candidate screening, interview, or employment action.
```

The card hot-reloads. Rerunning Agent card check turns the declaration green;
green means observed declaration only, not an implemented or effective control.

For **CV fit**, `evaluator-plan-governance` makes the deterministic
pre-execution eligibility decision. The wiki is an explicit, inspectable
governance/evidence knowledge plane: policy decides, while wiki passages supply
rationale. Missing Annex III employment or Article 14 evidence fails closed.
When eligibility proceeds, application AUs run to an immutable draft and the
planner records `result-draft`, `result-hold`, and `result_digest`. A human must
inspect that actual output, add notes, and approve or reject the exact digest.
Approval releases the identical draft; rejection quarantines it.

Current CV application AUs are intentionally read/compute/draft only. A result
hold cannot undo a side effect already performed by an AU.

**Flow audit** reconstructs planner JSONL and checks eligibility before
application work, application completion before the draft, exact-digest result
review, release or quarantine ordering, and released-payload equality. It cites
Article 14 from the wiki. By default, its panel includes only employment traces
carrying the current `human-review-before-release` result-governance model.
Older employment traces remain persisted but hidden; the **Show legacy
history** checkbox includes them and reports the included count. Red legacy rows mean current
evidence is absent, not necessarily that the old execution failed. Legacy
`hold`, `plan-approval`, and `resume` records remain parseable but do not satisfy
result review.

Card evidence, deterministic eligibility, result review, execution evidence,
and legal claims are separate. None confers legal permission, establishes legal
compliance or certification, or proves effective human oversight.

`plan_digest` correlates eligibility with the resolved composition.
`result_digest` binds human review to the frozen final outputs and plan digest.
Both are course integrity mechanisms, not signatures or authorization
credentials.

Held draft objects live in planner memory. A planner restart leaves trace JSONL
evidence on disk but loses the active draft required for result review; submit a
new intent. This is not production persistence or crash-idempotent
orchestration.
