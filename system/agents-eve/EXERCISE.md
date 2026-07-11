# Session 3 lab — learn EVE, build an agent, then adopt it into AOA

This lab begins with no authored agent. You will use EVE's own CLI, edit the
files EVE creates, and test the agent through EVE before AOA is involved. Only
then will you publish a capability contract and use the agent through the
course's existing intent interface.

The sequence is:

1. **Learn the EVE CLI** — run `eve init`, `eve info`, and `eve dev` yourself.
2. **Build and test** — edit the bind-mounted EVE project and talk to the agent
   in EVE's terminal UI.
3. **Adopt** — add one capability card and start the generic AOA bridge.
4. **Compose** — invoke your agent through **CV fit + interview** in Studio.

Node, npm, EVE, and dependencies live inside a pinned Docker image. Your laptop
needs Docker, a text editor, and the course `.env`; it does not need Node.

## Checkpoint 1 — enter the EVE workshop

From the `aoa-course` directory, run:

```bat
scripts\session3-up.bat
```

On macOS or Linux:

```bash
./scripts/session3-up.sh
```

The script does two things:

1. starts the Session 3 AOA services in the background;
2. attaches your terminal to the pinned EVE workshop container.

You should see a banner and this prompt:

```text
eve-workshop>
```

The container's `/workshop` directory is bind-mounted from this Windows-visible
directory:

```text
system\agents-eve\workshop
```

Anything EVE creates there appears immediately in your editor on the laptop.

Explore the CLI, then initialise the agent yourself:

```sh
eve --help
eve init .
```

EVE adds its authored surface to the existing pinned package shell:

```text
system/agents-eve/workshop/
  agent/
    agent.ts
    instructions.md
    channels/eve.ts
```

After initialisation, EVE may enter its development UI automatically. Press
`Ctrl+C` to return to the `eve-workshop>` shell while you edit the generated
files. If you exit the container accidentally, run `session3-up` again; the
mounted files remain on the laptop.

At this point there is still no capability card and nothing has registered in
AOA. You have an EVE project, not yet an Agentic Unit.

## Checkpoint 2 — turn the default project into your agent

Keep the workshop terminal open. On the Windows host, open:

```text
system\agents-eve\workshop\agent\agent.ts
```

Replace it with the course's provider-neutral model wiring. It consumes the
same `.env` model settings as the other course agents:

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

Now edit:

```text
system\agents-eve\workshop\agent\instructions.md
```

Give the agent one bounded job: turn a CV-fit evaluation into 5–8 questions
that help a human interviewer test the stated strengths and gaps. Require one
JSON result:

```json
{
  "questions": [
    { "area": "...", "question": "...", "why": "..." }
  ],
  "report_markdown": "..."
}
```

Useful rules to express in your own instructions:

- work only from the supplied evaluation and optional CV;
- lead with gaps and weak scores, but treat a gap as a hypothesis;
- ask for concrete situations, decisions, evidence, and trade-offs;
- do not re-score the candidate or make a hiring decision;
- return JSON only.

Back at `eve-workshop>`, ask EVE what it discovered:

```sh
eve info
```

Then start EVE's interactive development UI:

```sh
eve dev
```

Talk to the agent directly. A useful first message is:

```text
Design interview questions from this evaluation:
{"scores":{"seniority_match":2},"verdict":"fit","strengths":["Strong SQL"],"gaps":["No production ownership evidence"]}
```

Iterate on `instructions.md` from the Windows editor and send another message.
EVE watches the mounted files and rebuilds for the next turn. Stay here until
the standalone agent behaves as intended.

This checkpoint matters: EVE has now proved its value without AOA. It owns the
agent files, model wiring, runtime, sessions, and developer feedback loop.

Press `Ctrl+C` when you are ready to return to the workshop shell.

## Checkpoint 3 — add the AOA adoption boundary

Still inside the workshop container, copy the small contract template:

```sh
cp /adoption-kit/interviewer-questions.yaml capability-card.yaml
```

On Windows, open the new file at:

```text
system\agents-eve\workshop\capability-card.yaml
```

Read it and add one constraint that matters in your employment context. The
separation should now be concrete:

- `agent/instructions.md` tells this implementation how to behave;
- `capability-card.yaml` tells other teams what they may rely on.

Do not change the EVE-authored files merely to make adoption work. For an
ordinary JSON-in/JSON-out agent, the generic bridge derives the invocation
message, tolerant result parsing, and basic signals from the card.

Leave the container shell:

```sh
exit
```

Back in Windows Command Prompt, adopt the agent:

```bat
scripts\session3-adopt.bat
```

On macOS or Linux:

```bash
./scripts/session3-adopt.sh
```

This starts the EVE runtime behind the reusable AOA bridge. Inspect the result
in a browser if useful:

- Registry: `http://localhost:7100/find?id=interviewer-questions`
- Agent Card: `http://localhost:7311/.well-known/agent-card.json`

The same EVE agent now has a stable Agent ID, registry lifecycle, outward A2A
face, trace boundary, model provenance, and `skills_hash`.

## Checkpoint 4 — use the existing intent interface

Open Studio at `http://localhost:8080` and select **CV fit + interview**. Submit
a CV and job description from `course/data/session-01-cv-fit/`.

The intent runs:

```text
parse-cv → evaluate-cv-fit → interviewer-questions
```

The first two steps are existing Python AUs. The final step is the EVE agent you
created and tested. The planner calls it through the same registry contract and
A2A surface; the intent interface does not import EVE or understand EVE
sessions.

Read the responsibility walk in Studio. It should show your adopted Agent ID
and the questions returned by your EVE implementation.

## Debrief

| EVE remains responsible for | AOA adds at adoption |
|---|---|
| `agent.ts`, `instructions.md`, tools, sessions | capability publication and stable Agent ID |
| EVE CLI, native runtime, and development UI | registry discovery and lifecycle |
| framework-local history and evals | estate trace boundary and outward A2A face |

The agent-specific adoption cost was one public contract file. A custom codec
is possible for an unusual native shape, but it is an exception rather than the
default. The replacement test is: could another runtime honour the same card
without making the intent interface learn EVE?

## Compatibility helpers and fallback

- `session3-lab-native` remains as an alias for `session3-up`.
- `session3-lab-wrap` remains as the underlying adoption helper.
- `session3-lab-init` remains as a non-interactive instructor fallback; it is
  deliberately not part of the learner path.
- The pre-authored agent under `system/agents-eve/interviewer/` remains the
  instructor fallback under the `session3-reference` profile.
