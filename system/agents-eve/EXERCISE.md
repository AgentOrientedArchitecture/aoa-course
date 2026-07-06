# Capstone exercise — author your own agent with EVE, then govern it

By the end of Session 3 you have seen an EVE-authored agent
(`interviewer-questions`) running as a first-class AOA Agentic Unit. Now build your
own, from scratch, and feel both sides of the story:

- **The capability** — EVE gets you a working agent in minutes.
- **The limitation (from an AOA perspective)** — that agent is an *island*: nothing
  can discover it, govern it, trust it, or orchestrate it.
- **The resolution** — the small `aoa-eve` adapter supplies exactly the governance
  EVE leaves out, and your island becomes a governed AU.

The arc is the point: **EVE gets you ~80% of the way — a runtime and an authoring
model — and AOA is the last 20% that makes an agent governable.**

You'll build a **CV red-flags reviewer**: it reads a CV-fit evaluation and returns
the risks an interviewer should dig into.

> Prerequisites: Node 20+ and npm on your host, the Session 3 stack from
> [`../EVE.md`](../EVE.md), and a configured `.env`.

---

## Part 1 — Build it with EVE (the 80%)

Scaffold a brand-new EVE agent. This is *pure EVE* — no AOA anything yet.

```bash
cd system/agents-eve
npx eve@latest init red-flags
cd red-flags
```

Make it run on the course's model. Replace `agent/agent.ts` with the env-driven,
OpenAI-compatible provider (copy it from `../interviewer/agent/agent.ts`):

```ts
import { createOpenAI } from "@ai-sdk/openai";
import { defineAgent } from "eve";

const provider = createOpenAI({
  baseURL: process.env.OPENAI_BASE_URL || `${process.env.OLLAMA_HOST || "http://localhost:11434"}/v1`,
  apiKey: process.env.OPENAI_API_KEY || "not-needed-for-local",
});
export default defineAgent({
  model: provider(process.env.MODEL || "gpt-oss:120b"),
  modelContextWindowTokens: Number(process.env.MODEL_CONTEXT_WINDOW_TOKENS || 128000),
});
```

```bash
npm install @ai-sdk/openai
```

Write the behaviour in `agent/instructions.md`:

```md
# Identity
You review a CV-fit evaluation and surface the red flags an interviewer should
probe: thin evidence, over-claims, unexplained gaps, seniority mismatch.

Respond with ONLY a single JSON object:
{ "flags": [ { "severity": "high|medium|low", "area": "...", "concern": "...", "follow_up": "..." } ],
  "report_markdown": "..." }
```

Keep it tool-free so it runs on every provider (EVE offers built-in tools by
default, and some OpenAI-compatible endpoints — SambaNova's — reject the `tool`
role). Copy the `disableTool()` sentinels:

```bash
cp -r ../interviewer/agent/tools ./agent/tools
```

Run it and talk to it directly over EVE's own HTTP API:

```bash
set -a; . ../../../.env; set +a
export OPENAI_API_KEY="${AOA_OPENAI_API_KEY:-$OPENAI_API_KEY}"
npm exec -- eve dev --no-ui --port 3100 &

curl -s -X POST http://127.0.0.1:3100/eve/v1/session \
  -H 'content-type: application/json' \
  -d '{"message":"Evaluation: {\"scores\":{\"seniority_match\":2},\"verdict\":\"fit\",\"gaps\":[\"No production ownership\"]}"}'
# note the x-eve-session-id header, then stream it:
# curl http://127.0.0.1:3100/eve/v1/session/<id>/stream
```

**✅ Checkpoint — the capability.** In a few minutes and a couple of files you have
a working, reasoning agent with a durable session API. That is EVE's 80%. Stop the
dev server (`kill %1`) before moving on.

---

## Part 2 — Try to use it *inside AOA* (the limitations)

Your agent works — but bring it to the governed system and it falls short on every
AOA dimension. With the Session 3 stack up (`./scripts/session3-up.sh`), work
through each and note what's missing.

1. **Discovery — it isn't in the registry.**
   ```bash
   curl -s http://localhost:7100/list | python3 -m json.tool | grep '"id"'
   ```
   Your `red-flags` agent is absent. The planner discovers work by querying the
   registry, so it can never route to an agent that never registered. ⚠️

2. **Contract — there is no capability card.** EVE has instructions and a model, but
   nothing declares your agent's `inputs`, `outputs`, `constraints`, or
   `evaluation_signals`. Nobody — human or planner — can reason about what it
   promises or check whether it kept the promise. ⚠️

3. **Identity & lifecycle — nothing to govern.** There is no stable `agent_id`
   separate from the code, and no `published_by` / `approved_by` / `status`. Ask
   "who approved this to run, and against which contract?" — EVE has no answer. ⚠️

4. **Interop — wrong protocol.** Your agent speaks EVE's `/eve/v1/session`; the AOA
   planner speaks A2A `message/send`. They cannot talk. ⚠️

5. **Observed behaviour — no provenance.** Edit `agent/instructions.md` and the
   governed system notices nothing: there's no `skills_hash` in the registry, and no
   boundary in the studio's responsibility walk. You can't tell which behaviour
   version produced a result. ⚠️

> **Reflect.** EVE is an excellent *authoring and runtime* tool. None of the gaps
> above are EVE bugs — they're simply *not what EVE is for*. They are the substance
> of Agent-Oriented Architecture: contract, discovery, governed identity, interop,
> and observed-over-claimed quality.

---

## Part 3 — Close the gap with the aoa-eve adapter (the resolution)

Now add the AOA layer. You do **not** touch your EVE agent's behaviour — you wrap it.

1. **Bring in the adapter and give the agent a contract.**
   ```bash
   cp -r ../interviewer/adapter ./adapter
   cp ../interviewer/package.json ../interviewer/tsconfig.json ../interviewer/Dockerfile ./  # or merge deps
   ```
   Write `capability-card.yaml` next to `agent/` — this is the contract EVE lacked:
   ```yaml
   id: red-flags-review
   version: 0.1.0
   kind: au
   purpose: |
     Surface the red flags in a CV-fit evaluation for an interviewer to probe.
   inputs:
     - { name: evaluation, type: object, required: true }
   outputs:
     - { name: flags, type: array }
     - { name: report_markdown, type: string }
   constraints:
     - The output is a single JSON object.
     - flags is an array; each item has severity, area, concern, and follow_up.
   evaluation_signals:
     - valid_output_shape
     - has_flags
     - latency_p95_under(12s)
   provenance:
     model: ${MODEL}
   ```

2. **Point `adapter/boot.mjs` at your I/O** — change `buildMessage` to pass the
   `evaluation`, and `computeSignals` to report `has_flags`
   (`Array.isArray(outputs.flags) && outputs.flags.length > 0`). The generic
   `serve.mjs`, `card.mjs`, `registry.mjs`, and `eve.mjs` need no changes.

3. **Add a service** to `system/docker-compose.yml`, modelled on `eve-interviewer`,
   with a distinct identity and port:
   ```yaml
   eve-red-flags:
     profiles: ["session3"]
     build: { context: ./agents-eve/red-flags, dockerfile: Dockerfile }
     container_name: aoa-eve-red-flags
     ports: ["7306:8888"]
     volumes:
       - ./agents-eve/red-flags/agent:/app/agent:ro
       - ./agents-eve/red-flags/capability-card.yaml:/app/capability-card.yaml:ro
     environment:
       AGENT_ID: urn:aoa:agent:eve-red-flags
       AGENT_NAME: eve-red-flags
       AGENT_HOST: eve-red-flags
       # ...same REGISTRY_URL / PLANNER_URL / model block as eve-interviewer...
   ```
   Add `red-flags-review` to the registry allowlist in
   `docker-compose.session3.yml`.

4. **Bring it up and watch the gaps close.**
   ```bash
   ./scripts/session3-up.sh
   curl -s "http://localhost:7100/find?id=red-flags-review" | python3 -m json.tool
   ```
   The same agent now has a **capability card**, a stable **`agent_id`**, an
   **`a2a_endpoint`**, lifecycle **status**, and a **`skills_hash`** — and the
   planner can discover and call it over A2A. Edit `agent/instructions.md` and watch
   the registry's `skills_hash` change live while the Agent ID stays put.

   Optional stretch: add a `cv-fit-redflags` workflow to `planner.py` (copy the
   `cv-fit-interview` pattern) and a studio mode, so the planner orchestrates your
   agent end-to-end like the interviewer.

**✅ Checkpoint — the resolution.** Map each ⚠️ from Part 2 to the property the
adapter restored: registration → discovery, `capability-card.yaml` → contract,
`agent_id`/lifecycle → governed identity, `/a2a` → interop, `skills_hash` + trace →
observed-behaviour provenance.

---

## Takeaway

| | EVE gives you | AOA adds |
|---|---|---|
| Author behaviour | `instructions.md`, `agent.ts`, tools | — |
| Run it | durable sessions, sandbox, HTTP API | — |
| **Contract** | — | `capability-card.yaml` |
| **Discovery** | — | registry registration |
| **Governed identity** | — | `agent_id`, lifecycle actors |
| **Interop** | EVE session API | A2A `message/send` |
| **Observed quality** | — | `skills_hash`, signals, trace |

EVE is the 80%: it makes authoring and running an agent fast and pleasant. AOA is
the 20% that makes an agent a *governed participant* in a system of agents. The
`aoa-eve` adapter is the seam between them — and building your own agent is the
fastest way to feel exactly where that seam sits.
