# Session 3 lab — build natively in EVE, then adopt into AOA

Session 3 starts with a blank authored workspace. You first create and accept an
agent with EVE's own CLI. Only after the native agent works do you adopt it into
AOA and run it as part of the existing CV-fit workflow.

The learner path has three public course commands:

1. `session3-build` — pre-build all Session 3 images, including the pinned workshop.
2. `session3-up` — open the native EVE workshop only.
3. `session3-adopt` — create the capability card when needed and start AOA with
   the adopted agent.

Node, npm, EVE, and package dependencies stay inside the pinned
`aoa-course/eve-workshop:0.17.1` image. Your laptop needs Docker, a text editor,
and the course `.env`; it does not need Node.

## Before the session — build the image

This is normally completed during pre-work. From the `aoa-course` directory:

```bat
scripts\session3-build.bat
```

On macOS or Linux:

```bash
./scripts/session3-build.sh
```

This builds the complete Session 3 image set without starting EVE, starting AOA,
or authoring an agent.

## Checkpoint 1 — initialise the blank workspace

Open the native workshop:

```bat
scripts\session3-up.bat
```

On macOS or Linux:

```bash
./scripts/session3-up.sh
```

`session3-up` runs native EVE only. It does not start the registry, planner,
studio, or AOA bridge. The container opens at `/workshop`, bind-mounted from:

```text
system/agents-eve/workshop/
```

The checked-in workspace is a pinned package shell with no authored agent. At
the `eve-workshop>` prompt, initialise it yourself:

```sh
eve init .
```

If EVE enters its development UI automatically, press `Ctrl+C` so that you can
edit first. The authored files now appear on the host:

```text
system/agents-eve/workshop/
  agent/
    agent.ts
    instructions.md
    channels/eve.ts
```

Generated files under `system/agents-eve/workshop/` are learner-owned. The
checked-in package shell keeps the workshop reproducible offline; course runtime
infrastructure is separate under `system/agents-eve/runtime/`.

## Checkpoint 2 — add provider-neutral model wiring

On the host, replace
`system/agents-eve/workshop/agent/agent.ts` with the complete file below:

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

This uses the OpenAI-compatible interface supplied by the course `.env`. The
same file works with the configured hosted provider or Ollama's `/v1` shim;
`.env` selects the provider endpoint and active model, while the code keeps only
a local-development fallback.

## Checkpoint 3 — give the agent one bounded job

Replace `system/agents-eve/workshop/agent/instructions.md` with this complete,
concise file:

````markdown
# Role

You design concise, evidence-seeking interview questions from a CV-fit
evaluation.

You receive an evaluation containing scores, a verdict, strengths, gaps, and
rationale. You may also receive a parsed CV.

Your role is to help a human interviewer test the evaluation. You do not
re-score the candidate, make a hiring decision, or recommend whether the
candidate should be hired.

# Evidence rules

Work only from the supplied evaluation and optional CV.

Treat every strength and gap as a hypothesis to test, not as an established
fact. Do not invent candidate experience, qualifications, employers, projects,
or personal details.

Prioritize:

1. Gaps and weak scores.
2. Claims that need concrete evidence.
3. Decisions, trade-offs, and measurable outcomes.
4. One forward-looking question about adapting to the role.

Ask for specific situations and actions rather than opinions or trivia.

Do not infer or request protected characteristics or other sensitive personal
information.

# Question rules

Create exactly 5 questions.

For each question:

- `area` must contain no more than 6 words.
- `question` must contain no more than 35 words.
- `why` must contain no more than 15 words.
- Ask only one primary question.
- Refer to a supplied score, strength, gap, rationale, or CV detail.
- Seek concrete evidence, decisions, actions, trade-offs, or outcomes.
- Do not repeat the evaluation as if it were proven fact.

Lead with the most important gap or weakest score.

Use at least one question to verify a stated strength.

End with one forward-looking question about how the candidate would adapt
their existing experience to the role.

# Output requirements

Return only one complete, valid JSON object.

Do not include:

- introductory text;
- concluding text;
- commentary;
- reasoning;
- Markdown code fences;
- text outside the JSON object.

Use exactly these top-level keys:

- `questions`
- `report_markdown`

Use exactly this structure:

{
  "questions": [
    {
      "area": "short area",
      "question": "concise evidence-seeking question",
      "why": "brief link to supplied evidence"
    }
  ],
  "report_markdown": "concise Markdown rendering"
}

`questions` must contain exactly 5 objects.

Every question object must contain exactly:

- `area`
- `question`
- `why`

All three values must be strings.

`report_markdown` must contain the same 5 questions as short Markdown bullets.
It may group them under short area headings, but it must not repeat the `why`
text or add new questions.

Keep the entire response below 1,200 tokens. Prefer shorter wording if needed
to ensure the JSON object is complete.

Before returning the response, silently verify that:

1. The JSON object is complete and syntactically valid.
2. Every string is closed.
3. All arrays and objects are closed.
4. There are exactly 5 questions.
5. Both required top-level keys are present.
6. There is no text outside the JSON object.
````

The output boundary is deliberately strict: exactly five questions, bounded
field lengths, JSON only, and no more than 1200 tokens.

## Checkpoint 4 — run the native acceptance tests

Back at `eve-workshop>`, inspect what EVE discovered:

```sh
eve info
```

Confirm that EVE reports the agent and channel from the learner workspace. Then
start the native development UI yourself:

```sh
eve dev
```

Use this first acceptance input:

```text
Design interview questions from this evaluation:
{"scores":{"seniority_match":2,"sql_depth":4},"verdict":"fit","strengths":["Strong SQL"],"gaps":["No production ownership evidence"],"rationale":"SQL evidence is strong; operational ownership is unclear."}
```

Before adoption, run the native acceptance tests. Check that the response:

- is valid JSON with no surrounding prose or code fence;
- has exactly the keys `questions` and `report_markdown`;
- contains exactly 5 question objects, each with only `area`, `question`, and
  `why`;
- obeys every word limit and the 1,200-token response limit;
- probes the production-ownership gap as a hypothesis;
- confirms SQL with evidence rather than flattery;
- ends with a role-ramp question; and
- does not re-score the candidate or make a hiring recommendation.

Also test a sparse evaluation with empty strengths or gaps. The agent must still
return exactly five grounded questions without inventing candidate details.
Iterate on `instructions.md` and repeat these native acceptance tests until the
standalone EVE agent passes. Press `Ctrl+C`, then `exit`, when ready.

At this point there is no AOA capability, registry entry, or Agent ID. You have
accepted a native EVE agent, not yet an Agentic Unit.

## Checkpoint 5 — adopt the accepted agent

From the course root on Windows:

```bat
scripts\session3-adopt.bat
```

On macOS or Linux:

```bash
./scripts/session3-adopt.sh
```

`session3-adopt`:

1. validates that the learner-authored EVE files exist;
2. creates `system/agents-eve/workshop/capability-card.yaml` automatically if it
   is missing;
3. starts the Session 3 AOA services and generic EVE bridge; and
4. registers the agent as the `interviewer-questions` capability.

The generated card is the public contract; `agent/instructions.md` remains the
implementation's private behavioural guidance. Inspect the adopted result at:

- Studio: `http://localhost:8080`
- Registry: `http://localhost:7100/find?id=interviewer-questions`
- Agent Card: `http://localhost:7311/.well-known/agent-card.json`

If you edit `capability-card.yaml`, rerun `session3-adopt` so the adopted runtime
revalidates and republishes the card. If you return to native EVE and change the
agent after acceptance, repeat the native tests and rerun `session3-adopt`
before testing through AOA.

## Checkpoint 6 — run the composed workflow

Open Studio at `http://localhost:8080`, choose **CV fit + interview**, and submit
a CV and job description from `course/data/session-01-cv-fit/`.

The intent runs:

```text
parse-cv → evaluate-cv-fit → interviewer-questions
```

The first two steps are existing Python AUs. The final step is the EVE agent you
created and accepted natively. The planner invokes it through the same registry
contract and A2A surface without importing EVE or understanding EVE sessions.

Use the responsibility walk to verify the adopted Agent ID, capability, trace
boundary, and five returned questions.

## Debrief

| EVE remains responsible for | AOA adds at adoption |
|---|---|
| learner-authored `agent.ts` and `instructions.md` | generated capability card and stable Agent ID |
| native CLI, runtime, sessions, and development UI | registry discovery and lifecycle |
| native acceptance before composition | outward A2A surface and estate trace boundary |

The ownership boundary is visible on disk: reusable course infrastructure lives
under `system/agents-eve/runtime/`; the agent you authored and its generated
contract live under `system/agents-eve/workshop/`.
