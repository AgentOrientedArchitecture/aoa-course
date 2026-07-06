# Session 3 — Authoring Agentic Units with Vercel EVE

Read [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`AGENTS.md`](AGENTS.md) first. This
document is about Session 3: introducing [Vercel EVE](https://github.com/vercel/eve)
— a filesystem-first framework for building agents — as another way to author an
Agentic Unit, and governing that EVE agent with the same AOA registry, planner,
and studio the Python agents use.

## Why EVE fits AOA (and where it doesn't)

EVE and AOA are close cousins. An EVE agent is a directory of files, and those
files map almost one-to-one onto the four parts of an AOA Agentic Unit:

| AOA (Python scaffold) | EVE (TypeScript) |
|---|---|
| `instructions.md` — behaviour, hot-reloaded | `agent/instructions.md` — always-on system prompt |
| `agent.py` wiring + `provenance.model` | `agent/agent.ts` — `defineAgent({ model })` |
| `tools.yaml` + MCP tool bridges | `agent/tools/*.ts` — `defineTool` (+ Zod) |
| planner + A2A `message/send` orchestration | built-in subagents / the `agent` tool |
| **`capability-card.yaml` — the contract** | **— nothing —** |
| **the registry — discovery + lifecycle** | **— nothing —** |
| **`agent_id` / A2A Agent Card — governed identity** | **— nothing —** |

The bottom three rows are the point of Session 3. EVE gives you a great authoring
and runtime model, but it has **no capability card, no registry, and no governed
agent identity**. AOA has exactly those. So "introducing EVE" means wrapping
EVE with AOA's governance layer — which is what the **aoa-eve adapter** does.

## The eve-interviewer agent

Session 3 adds one new capability to the CV-fit workflow:

```
parse-cv → evaluate-cv-fit → interviewer-questions
```

`interviewer-questions` is a genuine EVE agent (`system/agents-eve/interviewer/`).
It takes the evaluator's fit verdict and writes targeted interview questions that
probe the flagged gaps. The planner discovers it in the registry and calls it over
A2A — it cannot tell that this AU runs on Node/EVE instead of Python/FastAPI. That
is the teaching point: **the registry is indifferent to the runtime that fulfils a
capability.** A CV parser in Python and an interviewer in EVE are governed the same
way.

### Layout

```
system/agents-eve/interviewer/
  capability-card.yaml       # the AOA contract EVE lacks
  agent/                     # the EVE agent (filesystem-first)
    agent.ts                 # defineAgent — env-driven model (see below)
    instructions.md          # behaviour; edited to change the agent, hot-reloaded
    channels/eve.ts          # EVE's internal HTTP channel (loopback only)
    tools/*.ts               # disableTool() sentinels — see "Provider support"
  adapter/                   # the reusable aoa-eve bridge (plain ESM)
    boot.mjs                 # entry point + the agent-specific message/parse/signals
    serve.mjs                # AOA HTTP + A2A surface, registration, trace, hot reload
    card.mjs                 # loads + stamps capability-card.yaml like base.py does
    registry.mjs             # AOA registry client (register/update)
    eve.mjs                  # runs `eve dev` and drives one turn to completion
  Dockerfile                 # node:24-slim; runs adapter/boot.mjs
```

### What the adapter adds (the governance EVE lacks)

`adapter/` is the AOA counterpart of `system/agents/_base/base.py`, in JavaScript:

1. **Card stamping** (`card.mjs`) — reads `capability-card.yaml` and stamps
   `agent_id`, `identity`, `endpoint`, `a2a_endpoint`, `provenance.model`, and
   `provenance.skills_hash` (SHA-256 of `instructions.md`), exactly like the Python
   scaffold.
2. **Registration** (`registry.mjs`) — POSTs the card to the registry on boot, with
   the same retry-until-ready behaviour as `registry_client.py`.
3. **The AOA surface** (`serve.mjs`) — serves `/healthz`,
   `/.well-known/agent-card.json`, `/cards/<id>`, `/invoke`, and `/a2a` with the
   identical A2A request/response envelope the planner already speaks.
4. **Trace** — emits `au-start` / `au-finish` events to the planner so the studio's
   responsibility walk shows this agent like any other.
5. **Hot reload** — watches `instructions.md`; on edit it re-stamps `skills_hash`
   and re-registers, so the studio's registry pane updates live.

Inside, the adapter runs the EVE runtime (`eve dev`) on a loopback port and drives
each A2A call as one EVE session, then reads the model's reply. The `agent_id`
stays stable while `skills_hash` tracks the behaviour version — the same
identity/behaviour split the Python agents demonstrate.

## Model access — same `.env`, same providers

The EVE agent reads the **same** `PROVIDER` / `MODEL` / `OPENAI_BASE_URL` the rest
of the course uses (see `agent/agent.ts`): it configures an OpenAI-compatible AI SDK
provider with `createOpenAI({ baseURL, apiKey })`, and reaches Ollama through its
`/v1` shim. Switching model or provider is still a `.env` change — nothing about
EVE ties you to Vercel's cloud, AI Gateway, or OIDC. (`modelContextWindowTokens`
is set because local/unlisted model ids have no gateway metadata for EVE's
compaction.)

## Provider support — a real AOA lesson

EVE is a tool-calling framework: its default harness offers the model built-in
tools (`bash`, `read_file`, …) and structured output is implemented as a tool call.
Some OpenAI-compatible endpoints — **SambaNova's, in particular** — do not accept
the `tool` message role, so any tool call fails there.

So this agent deliberately runs **tool-free**: `agent/tools/` holds
`disableTool()` sentinels that remove the built-ins, and the agent produces its
result as a single JSON object in its reply, which the adapter parses. This is the
**same prompt-then-parse pattern every Python AU in this course uses** — which is
why the EVE agent runs on all three tested providers (Ollama, NVIDIA NIM,
SambaNova). It is a nice AOA point in its own right: a capability's contract is the
same regardless of whether the runtime uses native tool-calling underneath.

> **Enrichment (tool-capable providers).** On Ollama, NVIDIA NIM, or a gateway
> model that supports the `tool` role, you can give the agent real EVE tools and
> skills. Delete a sentinel and add, e.g., `agent/tools/read_jd.ts` with
> `defineTool` + a Zod `inputSchema` to let the model read the job description, or
> add `agent/skills/*.md` for on-demand procedures. That is the full EVE authoring
> surface — just not portable to endpoints without tool-role support.

## Run it

```bash
docker compose --env-file .env \
  -f system/docker-compose.yml \
  -f system/docker-compose.session3.yml \
  --profile session3 \
  up --build -d --remove-orphans
# or: ./scripts/session3-up.sh
```

Session 3 starts the CV-fit subset plus `eve-interviewer`. Open the studio at
`http://localhost:8080`; the registry pane shows `interviewer-questions` with
`kind: au`, `agent_id: urn:aoa:agent:eve-interviewer`, an `a2a_endpoint`, and a
`skills_hash` — indistinguishable from a Python AU. Submit a CV + job description in
**CV fit + interview** mode and watch the trace run
`parse-cv → evaluate-cv-fit → interviewer-questions`, ending in the interview
questions.

Inspect the EVE agent directly on its mapped host port:

```bash
curl http://localhost:7305/.well-known/agent-card.json
curl http://localhost:7305/cards/interviewer-questions
```

## The two exercises

**1. Modify an existing agent by editing markdown.**
Edit `system/agents-eve/interviewer/agent/instructions.md` (e.g. ask for
scenario-based questions only). Save. The studio's registry pane shows a new
`skills_hash` for `interviewer-questions` immediately — the governed behaviour
version changed while the Agent ID stayed stable. The next run reflects the new
instructions. (The Python agents hot-reload behaviour the same way — try editing
`system/agents/evaluator/capabilities/cv/instructions.md` in Session 1.)

**2. Create your own agent with EVE — the capstone.**
Build a brand-new EVE agent from scratch, feel what it can do standalone (the
capability), run into what it *can't* do inside a governed AOA system (the
limitations — no card, no registry, no identity, no A2A, no observed-behaviour
provenance), then add the adapter and watch it become a first-class governed AU.
The full guided lab is in [`agents-eve/EXERCISE.md`](agents-eve/EXERCISE.md).

The short version: `npx eve@latest init my-agent` (or `cp -r interviewer my-agent`),
write `agent/instructions.md` + the env-driven `agent/agent.ts`, add a
`capability-card.yaml`, reuse `adapter/`, add a compose service modelled on
`eve-interviewer` with a distinct `AGENT_ID` and port, add the capability id to the
registry allowlist, and `./scripts/session3-up.sh`.

## Notes and fallbacks

- The container runs `eve dev --no-ui` so `instructions.md` edits hot-reload EVE
  behaviour. If you prefer a lighter runtime, build once and serve the compiled
  output instead: change the Dockerfile to `RUN npx eve build` and the boot command
  to run `eve start` (see `adapter/eve.mjs`); the registry `skills_hash` still
  updates live via the adapter's watcher, but EVE behaviour then changes only on
  rebuild.
- EVE's own docs ship inside the installed package under
  `node_modules/eve/docs/` and match the pinned version exactly.
