# Session 3 lab — build an EVE agent, then adopt it into AOA

Start with no agent. Use EVE to create one that works on its own. Only after it
is useful will you give it the public contract that lets the AOA estate
discover and compose it.

The learning sequence is deliberate:

1. **Create** — use the real EVE CLI to scaffold a minimal agent.
2. **Make useful** — give it one bounded job and test it through EVE.
3. **Adopt** — add one capability card; the generic `aoa-eve` bridge supplies
   identity, registration, trace, and the outward A2A surface.
4. **Compose** — run the existing CV-fit workflow and watch your agent perform
   its final step.

Node, npm, EVE, and all package dependencies live in the pinned workshop image.
The host needs Docker, a text editor, and the course `.env` only.

## Checkpoint 1 — ask EVE to create an agent

The checked-in `system/agents-eve/workshop/` directory contains a package shell
but deliberately has no `agent/` directory. Run:

```bash
./scripts/session3-lab-init.sh
```

On Windows:

```bat
scripts\session3-lab-init.bat
```

This runs `eve init .` inside `aoa-course/eve-workshop:0.17.1`. EVE creates:

```text
system/agents-eve/workshop/
  agent/
    agent.ts
    instructions.md
    channels/eve.ts
```

At this point the agent is the generic assistant EVE scaffolded. There is no
AOA card or adapter in the workspace.

## Checkpoint 2 — give the standalone agent one useful job

Replace the generated `agent/agent.ts` with the course's provider-neutral model
wiring. It uses the same `.env` as the rest of the system:

```ts
import { createOpenAI } from "@ai-sdk/openai";
import { defineAgent } from "eve";

function baseUrl(): string {
  const explicit = process.env.OPENAI_BASE_URL?.trim();
  if (explicit) return explicit;
  const ollama = process.env.OLLAMA_HOST?.trim();
  if (ollama) return `${ollama.replace(/\/$/, "")}/v1`;
  return "http://localhost:11434/v1";
}

const provider = createOpenAI({
  baseURL: baseUrl(),
  apiKey: process.env.OPENAI_API_KEY || "not-needed-for-local",
});

export default defineAgent({
  model: provider(process.env.MODEL || "gpt-oss:120b"),
  modelContextWindowTokens: Number(
    process.env.MODEL_CONTEXT_WINDOW_TOKENS || 128000,
  ),
});
```

Now ask EVE what it discovered:

```bash
docker compose \
  -f system/docker-compose.yml \
  -f system/docker-compose.session3.yml \
  -f system/docker-compose.session3-lab.yml \
  run --rm --no-deps eve-workshop-native npm exec -- eve info
```

Now rewrite `agent/instructions.md`. Give the agent one bounded job: turn a
CV-fit evaluation into 5–8 evidence-seeking interview questions. Require a
single JSON result with this shape:

```json
{
  "questions": [
    { "area": "...", "question": "...", "why": "..." }
  ],
  "report_markdown": "..."
}
```

Useful constraints to express in the instructions:

- work only from the supplied evaluation and optional CV;
- lead with gaps and weak scores, but treat each gap as a hypothesis;
- ask for concrete situations, decisions, evidence, and trade-offs;
- do not re-score the candidate or make a hiring decision;
- return JSON only.

Start the standalone EVE agent:

```bash
./scripts/session3-lab-native.sh
```

Send it a native EVE message:

```bash
curl -i -X POST http://127.0.0.1:7310/eve/v1/session \
  -H 'content-type: application/json' \
  -d '{"message":"Design interview questions from this evaluation: {\"scores\":{\"seniority_match\":2},\"verdict\":\"fit\",\"strengths\":[\"Strong SQL\"],\"gaps\":[\"No production ownership evidence\"]}"}'
```

The agent now works. EVE owns its files, model wiring, runtime, session, and
behaviour. Open `http://localhost:8080` and notice that the AOA registry still
cannot see it. That is expected: you have built an agent, not yet published an
estate contract.

## Checkpoint 3 — adopt it with one boundary file

Copy the small card template next to the EVE project:

```bash
cp system/agents-eve/adoption-kit/interviewer-questions.yaml \
  system/agents-eve/workshop/capability-card.yaml
```

Read it before continuing. Add one constraint that matters in your employment
context. The important distinction is now visible:

- `agent/instructions.md` tells this implementation how to behave;
- `capability-card.yaml` tells other teams what they may rely on.

Do not alter `agent.ts` or `instructions.md` during adoption. Start the wrapped
service:

```bash
./scripts/session3-lab-wrap.sh
```

The pinned image starts the generic `aoa-eve` bridge. There is no
agent-specific adapter file in your project: for JSON-in/JSON-out agents the
bridge derives the invocation prompt, output parsing, and basic signals from
the card.

Inspect the new public surfaces:

```bash
curl -s 'http://localhost:7100/find?id=interviewer-questions'
curl -s 'http://localhost:7311/.well-known/agent-card.json'
```

The registry row now has a stable Agent ID, lifecycle, endpoint, A2A face, model
provenance, and `skills_hash`. The EVE-authored files are unchanged.

## Checkpoint 4 — use your agent inside the existing ecosystem

In the Studio at `http://localhost:8080`, choose **CV fit + interview**. Submit a
CV and job description from `course/data/session-01-cv-fit/`.

The existing workflow now runs:

```text
parse-cv → evaluate-cv-fit → interviewer-questions
```

The first two units are Python AUs. The final unit is the EVE agent you just
created. The planner composes all three from the same registry contract and A2A
surface; it does not import EVE or understand EVE sessions.

## Debrief

The adoption cost for this simple agent was one authored boundary file:

| EVE project remains responsible for | AOA bridge adds |
|---|---|
| `agent.ts`, `instructions.md`, tools, sessions | capability publication and stable Agent ID |
| EVE native runtime | registry discovery and lifecycle |
| framework-local history and evals | estate trace boundary and outward A2A face |

An agent-specific codec is still possible when the native input/output shape is
unusual. It is an exception, not the starting point. The replacement test is:
could another runtime honour the same card without making callers learn EVE?

## Instructor fallback

If a participant machine cannot scaffold or run the workspace, use the
pre-authored reference agent under `system/agents-eve/interviewer/` with the
`session3-reference` profile. The old `red-flags/` example is retained as a
code-level adapter example, but is no longer the learner path.
