# Session 3 — EVE and AGNTCY

This is the complete session: build and test an EVE interviewer, adopt it into AOA, inspect its AGNTCY record, run the composed workflow and test the discovery boundary. Stay on this page for the required steps. The [adoption explanation](ADOPTION.md) and [Directory reference](DIRECTORY.md) provide optional detail.

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
and the course `.env`; it does not need Node. Complete the [setup](../../pre-work/SETUP.md) and generation smoke test first. All host commands below run from the root of the same checkout.

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

The launcher prints the machine name and the full **host workshop folder** before opening the shell. Check that it is the checkout you opened in your editor. `/workshop` is the container path; a shell connected to Spark writes to Spark, not this laptop.

The checked-in workspace is a pinned package shell with no authored agent. At
the `eve-workshop>` prompt, initialise it yourself:

```sh
eve init .
```

If EVE enters its terminal development UI automatically, press `Ctrl+C` so that you can
edit first. The scaffold may also report a default-model metadata error. If the
files below were created, continue to Checkpoint 2 and configure the course model
before starting `eve dev` again. Do not rerun `eve init` over authored files. The authored files now appear on the host:

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

// Endpoint resolution, in order:
//   1. OPENAI_BASE_URL   — any OpenAI-compatible endpoint (SambaNova, NVIDIA
//                          NIM, an MLX server on the host, ...).
//   2. OLLAMA_HOST + /v1 — Ollama's OpenAI-compatible shim.
//   3. localhost Ollama  — only reachable when EVE runs outside Docker;
//                          inside the workshop container Compose always sets
//                          OLLAMA_HOST, so this is a host-dev fallback.
function baseUrl(): string {
  const explicit = process.env.OPENAI_BASE_URL?.trim();
  if (explicit) return explicit;
  const ollama = process.env.OLLAMA_HOST?.trim();
  if (ollama) return `${ollama.replace(/\/$/, "")}/v1`;
  return "http://localhost:11434/v1";
}

const provider = createOpenAI({
  baseURL: baseUrl(),
  // Inside the workshop containers Compose supplies OPENAI_API_KEY from your
  // .env's CEREBRAS_API_KEY (or AOA_OPENAI_API_KEY for other providers), though
  // .env leaves OPENAI_API_KEY itself blank. Local endpoints need no key.
  apiKey: process.env.OPENAI_API_KEY || "not-needed-for-local",
});

export default defineAgent({
  // provider.chat(...) targets /chat/completions, which every
  // OpenAI-compatible endpoint serves. Calling provider(...) directly would
  // select OpenAI's newer Responses API (/responses), which SambaNova,
  // Ollama's shim, and most compatible providers do not implement.
  model: provider.chat(process.env.MODEL || "gpt-oss:120b"),
  modelContextWindowTokens: Number(
    process.env.MODEL_CONTEXT_WINDOW_TOKENS || 128000,
  ),
});
```

The same file works unchanged with every tested course `.env` — the workshop
containers receive `MODEL`, `OPENAI_BASE_URL`, `OLLAMA_HOST`, and (mapped from
`AOA_OPENAI_API_KEY`) `OPENAI_API_KEY` from Compose:

| Your `.env` | What the agent uses |
| --- | --- |
| Cerebras (default) | `OPENAI_BASE_URL` + `CEREBRAS_API_KEY`, mapped into the container as `OPENAI_API_KEY`. |
| Another OpenAI-compatible provider | `OPENAI_BASE_URL` + your `AOA_OPENAI_API_KEY`, model from `MODEL`. |
| Local option in `.env` (host Ollama) | `OLLAMA_HOST` (`http://host.docker.internal:11434`) + `/v1`, no key. |
| Container Ollama (`AOA_LOCAL=1`) | `OLLAMA_HOST` (`http://ollama:11434`) + `/v1`, no key. |
| MLX or another host-served OpenAI endpoint | Set `OPENAI_BASE_URL=http://host.docker.internal:<port>/v1` — `localhost` would point inside the container. |

Two limits worth knowing: this lab speaks the OpenAI-compatible interface
only, so `PROVIDER=anthropic` does not apply here (the `PROVIDER` variable is
ignored by `agent.ts`); and the `gpt-oss:120b` fallback model name is just a
last resort — Compose always passes your `.env`'s `MODEL`.

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
start the native development UI in this terminal:

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

On a fresh checkout there is not yet an AOA capability, registry entry or Agent ID
for this interviewer. You have accepted a native EVE agent. If reusing a checkout,
earlier registry records may persist; they do not accept your new behaviour for you.

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
3. starts the Session 3 AOA services, the EVE bridge and AGNTCY Directory;
4. registers the agent as the `interviewer-questions` capability; and
5. publishes all active AUs to Directory and waits for their records to be searchable.

The generated card is the public contract; `agent/instructions.md` remains the
implementation's private behavioural guidance. Inspect the adopted result at:

- Studio: `http://localhost:8080`
- Registry: `http://localhost:7100/find?id=interviewer-questions`
- Agent Card: `http://localhost:7311/.well-known/agent-card.json`

If you edit `capability-card.yaml`, rerun `session3-adopt` so the adopted runtime
revalidates and republishes the card. If you return to native EVE and change the
agent after acceptance, repeat the native tests and rerun `session3-adopt`
before testing through AOA.

## Checkpoint 6 — inspect the discovered capabilities

Open [Studio](http://localhost:8080). In **Capability cards**, find
`interviewer-questions`. Switch between its summary and JSON. Inspect its Agent
ID, inputs, outputs and instructions hash. This is the locally adopted contract.

Now open [AGNTCY's catalogue](http://localhost:8891), search for `aoa-course`,
and select the interviewer. A fresh Session 3 publishes six AUs: the parser,
three CV evaluators, reporter and EVE interviewer. Deterministic tools retain
local registrations. Older Directory records may remain in a reused checkout;
publication history is not the list of currently eligible AUs.

Inspect the declared skill, endpoint and catalogue JSON. The automatic records
include each runtime's actual A2A Agent Card, which makes them visible in the
catalogue. Copy the interviewer's content ID and retrieve the **full OASF record**:

| Action | macOS/Linux | Windows Command Prompt |
|---|---|---|
| Ensure publication is ready | `./scripts/directory.sh sync --wait 120` | `scripts\directory.bat sync --wait 120` |
| Retrieve the record | `./scripts/directory.sh pull YOUR_CONTENT_ID --out interviewer-discovered.json` | `scripts\directory.bat pull YOUR_CONTENT_ID --out interviewer-discovered.json` |
| Compare it with local adoption | `./scripts/directory.sh check interviewer-discovered.json` | `scripts\directory.bat check interviewer-discovered.json` |

Replace `YOUR_CONTENT_ID` with the real value; do not type angle brackets around
it. Open `.course-data/interviewer-discovered.json` in your editor. The catalogue
JSON is a projection; this file is the complete retrieved description.

For a matching, approved card, expect `matching_local_contract`,
`local_lifecycle_approved` and `locally_eligible` to be true. Expect
`execution_authorised` and `identity_verified_by_directory_record` to be false.
Read the fields: a successful `check` command can still report a mismatch.

You have now inspected three different descriptions:

| Description | What it supplies |
|---|---|
| Local AOA capability card | Accepted contract, Agent ID and lifecycle |
| OASF record in AGNTCY | Portable description, declared skills and discovery evidence |
| Runtime A2A Agent Card | Endpoint and invocation surface |

None of these alone proves the agent's behaviour or grants permission to run it.

## Checkpoint 7 — run the composed workflow

Return to Studio's **Studio · all controls** view and choose **CV fit + interview**.
Drop or paste these synthetic fixtures into the CV and job-description fields:

- [`jordan-okafor.txt`](../session-01-cv-fit/cv-examples/jordan-okafor.txt)
- [`senior-data-engineer-fintech.txt`](../session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt)

The job file's retained filename says fintech; its content is **Senior Data
Engineer — Healthcare Payments**. Use the actual content when judging the result.
For **Assessment emphasis**, try `Assess production data pipelines and data reliability`.
This brief guides AU selection; the selected evaluator subsequently reads the documents.

Submit once. This session uses a fixed task sequence:

```text
parse-cv → evaluate-cv-fit → generate-interview-questions
```

The planner retrieves candidates from AGNTCY, checks them against current local
adoption and contracts, then selects compatible AUs. Multiple eligible evaluators
use the configured decision model. The first two tasks use Python AUs. The final
task binds to `interviewer-questions` and invokes your real EVE agent through
its adopted A2A endpoint. EVE details stay
inside the course-owned bridge.

In **AU selection**, inspect **Published records and local adoption checks**:

1. Find the interviewer's Directory content ID and its accepted local binding.
2. Inspect the evaluator candidates and accepted choice. A declaration or high
   model probability does not prove that this is the best assessment.
3. Follow the invocation to the EVE interviewer. Confirm it received the
   assessment, then inspect the returned five questions in **Run review**.
4. Reapply the native acceptance criteria from Checkpoint 4. Generic bridge
   signals check fields; they do not establish every word limit or question quality.

Keep the trace ID and record content ID with your observations. The proof is the
completed composition and its evidence, not merely a catalogue card appearing.

## Checkpoint 8 — test the discovery boundary

After a successful run, stop **only Directory**:

| Action | macOS/Linux | Windows Command Prompt |
|---|---|---|
| Stop Directory, retaining its records | `./scripts/directory.sh stop` | `scripts\directory.bat stop` |
| Restart it after the check | `./scripts/directory.sh up` | `scripts\directory.bat up` |
| Wait for publication before retrying | `./scripts/directory.sh sync --wait 120` | `scripts\directory.bat sync --wait 120` |

While Directory is stopped, submit a **new** CV/interview intent. Expect a
visible discovery error. Inspect the trace for `directory-unavailable` and
**zero AU invocations**. There is no silent fallback to the local registry list.
Opening a saved result can still work: reviewing stored evidence is different
from discovering AUs for a new run.

Restart Directory, wait for sync and submit again. The local registry still owns
adoption, lifecycle and tool lookup. From this session onwards, AGNTCY supplies
the AU discovery records that the planner must also validate. Session 4 continues
with this arrangement.

## Review questions

- What did EVE supply, what did the adoption bridge add, and what did AGNTCY add?
- Where did the fixed task sequence end and the decision about which AU to use begin?
- Why can a discoverable record still be ineligible for this task?
- What evidence showed that the adopted interviewer actually ran?
- Why did a new intent fail when Directory stopped while a saved result remained readable?
- Before using an externally owned agent, what identity, access, quality and operating checks would still be needed?

## Finish

Stop the course from the host terminal:

| macOS/Linux | Windows Command Prompt |
|---|---|
| `./scripts/down.sh` | `scripts\down.bat` |

This preserves your authored EVE files, cards, Directory records and saved runs.
Keep them for [Session 4](../session-04-compliance/WALKTHROUGH.md). For optional
manual publishing, contract-mismatch checks and the OASF taxonomy, use the
[Directory reference](DIRECTORY.md). These are not extra required setup steps.

## If a checkpoint fails

| Symptom | Check before continuing |
|---|---|
| Generated files appear only in the container | Compare the launcher's machine and host path with the checkout open in your editor; inspect `system/agents-eve/workshop/agent/` on that machine |
| `eve init` reports a model metadata error | If the files exist, complete Checkpoints 2–3, then run `eve info` and `eve dev` |
| `eve dev` cannot create `/app/node_modules/eve/.eve` | Exit the shell, update `main`, run `session3-build`, then `session3-up`; the current image provides the non-root cache directory. Keep authored files |
| Adoption reports missing files | Finish native authoring and acceptance in this checkout; do not copy unrelated runtime files over the workshop |
| Publication is not ready | Run `directory sync --wait 120` with the platform launcher above; inspect `scripts/logs.sh directory-bridge` or `scripts\logs.bat directory-bridge` |
| A card changed but discovery fails | Re-adopt after editing the EVE card, then sync. Historical records are retained; the planner requires the current binding |
| Model call fails | Check the private `.env`, generation smoke test, provider quota and decision service logs; errors are not replaced silently |

The course uses real third-party framework and Directory components, a learner-owned
agent and course-owned integration. It does not deploy AGNTCY federation, verified
enterprise identity, SLIM or a full observability platform. See the optional
[adoption explanation](ADOPTION.md) for those boundaries.
