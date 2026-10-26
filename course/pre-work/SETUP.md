# Course setup

Use `main`, one **`.env`** file and the normal session launchers. All services are defined in **`system/docker-compose.yml`**. The scripts select the session for you.

## Fresh checkout

Install Git and Docker Desktop/Engine, and have a text editor available. On Windows use Docker Desktop with Linux containers and Command Prompt. EVE and AGNTCY run in containers; neither needs host Node, npm, Python or `dirctl`. Session 4's seed script uses Python 3 on macOS/Linux or built-in PowerShell on Windows.

Stop any older course instance with its `scripts/down.sh` or `scripts\down.bat` first. Course instances share container names and ports. Stopping preserves the older checkout's files and data.

```bash
git clone --branch main https://github.com/AgentOrientedArchitecture/aoa-course.git
cd aoa-course
git status --short --branch
docker compose version
cp .env.example .env
```

On Windows use `copy .env.example .env` for the last command. Edit the new `.env` in your editor. Never replace an existing populated file blindly, and never commit it.

## Hosted models

The example configures:

- **Generation:** Cerebras, `gpt-oss-120b`. Put its key in `LLM_API_KEY` privately.
- **Decisions:** TypeSafe, pinned `jev-1.13.0`. Put its key in `DECISION_API_KEY` privately.

For both models hosted by Ollama, start from [`.env.ollama.example`](../../.env.ollama.example) instead: `cp .env.ollama.example .env` (Windows: `copy .env.ollama.example .env`). It configures GPT-OSS 120B and Clef 27B; put the same Ollama key in `LLM_API_KEY` and `DECISION_API_KEY`. No local Ollama installation is needed. Hosted Clef requires a paid plan or usage credits. As checked on 26 October 2026, Clef Flash is listed for local use; the hosted example uses Clef. See [Ollama's decision API](https://docs.ollama.com/capabilities/decision). This is a configuration example, not a completed course rehearsal with this hosted pair.

Run `./scripts/test_model_provider.sh` (Windows: `scripts\test_model_provider.bat`). It makes a small real generation request and should finish with `result=PASS`. This check does not test the decision model; the first Session 1 CV run tests that path. Keys on Spark are not transferred by Git.

The key names describe their jobs, not their vendors. `PROVIDER=openai` selects
the OpenAI-compatible protocol; it does not require an OpenAI account. For
another compatible generation service, change `LLM_BASE_URL`, `MODEL` and
`LLM_API_KEY` together. Use that service's API root and exact model ID, then run
the generation smoke test. All course generation clients, including EVE, use
the same `LLM_BASE_URL` and `LLM_API_KEY` names.

| Generation service | `LLM_BASE_URL` with `PROVIDER=openai` |
|---|---|
| [NVIDIA](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-120b-infer) | `https://integrate.api.nvidia.com/v1` |
| [OpenRouter](https://openrouter.ai/developers) | `https://openrouter.ai/api/v1` |
| [Ollama cloud](https://docs.ollama.com/api/openai-compatibility) | `https://ollama.com/v1` |

For Ollama cloud, use the model name returned by its cloud catalogue; no local
Ollama installation is required. `PROVIDER=ollama` remains the native local
Ollama route. The table describes documented endpoints, not completed course
rehearsals with each provider.

Decisions have separate settings: `DECISION_PROVIDER`, `DECISION_BASE_URL`,
`DECISION_MODEL` and `DECISION_API_KEY`. A generic key name does not make a
generation endpoint a decision endpoint: the native decision route requires
the System One request/response contract. Use TypeSafe, the hosted Ollama example
above, or the local route below.

When switching providers, replace the key together with its endpoint so a key
for one service is not sent to another. Compatible API shape is a starting point;
it does not establish that every provider/model combination passes the course.
The [validation record](../VALIDATION.md) states which combinations were exercised.

Check provider credit and account limits before class. The example does not promise a free tier or enough quota for a room of learners. Errors remain visible rather than silently replacing a provider.

## Local models

Use the **same `.env`**. Its commented LOCAL OPTION lists the settings to change; uncommenting duplicate keys is unnecessary—edit the existing values. Install Ollama on the laptop and pull the named model first:

```bash
ollama pull gpt-oss:20b
```

Set `PROVIDER=ollama`, `MODEL=gpt-oss:20b`, `DECISION_PROVIDER=ollama`, `DECISION_MODEL=gpt-oss:20b`, and the listed local endpoints. Set `LLM_BASE_URL=http://host.docker.internal:11434/v1` as well: EVE uses Ollama's OpenAI-compatible interface. Increase the timeouts as shown in the example. Use `gpt-oss:120b` for generation where hardware permits.

For an unauthenticated local server, set `LLM_API_KEY=local-no-auth` and clear
`DECISION_API_KEY`. The placeholder keeps the OpenAI-compatible EVE client and
generation smoke test initialised without forwarding a hosted key.

The local decision baseline uses constrained JSON and reports no calibrated probability. `DECISION_ALLOW_UNSCORED=true` is an explicit classroom policy; it does not make the local model equivalent to Jev. Time the local route before teaching it.

Optional container Ollama is retained: start with `AOA_LOCAL=1` in the shell, set `OLLAMA_HOST` and `DECISION_BASE_URL` to `http://ollama:11434`, set `LLM_BASE_URL=http://ollama:11434/v1`, and pull the model into that container. On Windows run `set AOA_LOCAL=1` before the launcher.

### Native local decisions with Clef

Clef-Flash is a decision model with a native System One API. It can supply the
course's AU selection and wiki-promotion decisions, retaining model probabilities
and the caller's acceptance gate. It is a separate option from the unscored
chat baseline above; the hosted Cerebras/TypeSafe defaults remain unchanged.

For [Ollama 0.35.1 or later](https://ollama.com/library/clef-flash), download
`clef-flash` with `ollama pull clef-flash`. Change these existing `.env` settings:

```dotenv
DECISION_PROVIDER=systemone
DECISION_MODEL=clef-flash
DECISION_BASE_URL=http://host.docker.internal:11434
DECISION_API_KEY=
DECISION_ALLOW_UNSCORED=false
```

`DECISION_BASE_URL` is the server root; the adapter adds `/v1/systemone`.
The same protocol works with compatible `llama.cpp` servers and
[oMLX 0.7.2](https://github.com/jundot/omlx/releases/tag/v0.7.2). For oMLX,
use a decision checkpoint such as
[`Jundot/clef-flash-oQ4e`](https://huggingface.co/Jundot/clef-flash-oQ4e),
including its joint decision head. Set the exact model ID returned by that
server's `/v1/models`, its port, and `DECISION_API_KEY` only if that server
requires authentication. Replace any hosted decision key with the local server's
key, or leave it empty for an unauthenticated server.

Keep `DECISION_ALLOW_UNSCORED=false`. Probabilities are model outputs, not a
calibrated chance of correctness; re-evaluate the 0.65 teaching gate with your
inputs. Ollama's Clef choice interface supports 2–26 options, which covers the
current course candidate sets. A request or server failure remains visible;
the adapter does not substitute a hosted decision.

Changing only the decision settings leaves generation on its configured provider.
For fully local inference, generation must also use Ollama or an OpenAI-compatible
local server such as oMLX. For example, if oMLX serves `Qwen3.8-27B-4bit` on port
8000, edit the existing generation settings:

```dotenv
PROVIDER=openai
LLM_API_KEY=local-no-auth
LLM_BASE_URL=http://host.docker.internal:8000/v1
MODEL=Qwen3.8-27B-4bit
```

`local-no-auth` is a placeholder for an **unauthenticated local server only**:
the course client and smoke test require a non-empty key. If authentication is
enabled, use that server's own key instead. Use the actual port and model ID
reported by your server; never send a hosted key to the local endpoint.
Docker must be able to reach the host server at `host.docker.internal`;
success from a host terminal alone does not verify container access. Check the
server's listen-address settings and run the course's model-provider smoke test.
The optional Clef trial below exercises the decision interface separately.

Start with a model that fits alongside Docker and Clef, then measure the course
examples before trying a larger one.
[Local trial observations](../validation/2026-10-25-local-models/README.md)
record what has actually been checked.

## Start and stop

Run these from the repository root:

| Action | macOS/Linux | Windows Command Prompt |
|---|---|---|
| Test generation access | `./scripts/test_model_provider.sh` | `scripts\test_model_provider.bat` |
| Session 1: CV | `./scripts/session1-up.sh` | `scripts\session1-up.bat` |
| Session 2: wiki | `./scripts/session2-up.sh` | `scripts\session2-up.bat` |
| Session 3: build images | `./scripts/session3-build.sh` | `scripts\session3-build.bat` |
| Session 3: author in EVE | `./scripts/session3-up.sh` | `scripts\session3-up.bat` |
| Session 3: adopt the tested agent | `./scripts/session3-adopt.sh` | `scripts\session3-adopt.bat` |
| Session 4: governance | `./scripts/session4-up.sh` | `scripts\session4-up.bat` |
| Seed Session 4 evidence | `./scripts/session4-seed.sh` | `scripts\session4-seed.bat` |
| Logs | `./scripts/logs.sh` | `scripts\logs.bat` |
| Stop, retaining data | `./scripts/down.sh` | `scripts\down.bat` |

Session 3 native authoring stops the AOA services and opens the standalone EVE workshop. The shell launcher prints the machine and host folder so a remote shell is distinguishable from a local laptop. Follow the [EVE walkthrough](../sessions/session-03-eve/WALKTHROUGH.md), exit its container shell, then adopt.

After adoption, Studio is at [localhost:8080](http://localhost:8080). AGNTCY's catalogue is at [localhost:8891](http://localhost:8891). Session 3 adoption and Session 4 startup automatically publish the active AUs and wait for discovery readiness. All required discovery and failure checks are in the [Session 3 walkthrough](../sessions/session-03-eve/WALKTHROUGH.md).

`down` covers all course services, including decision models, EVE, Directory and container Ollama. It retains authored files, saved cases, wiki content, Directory records and model volumes. Host-installed Ollama is independent of Compose.

## Existing checkouts

Save any source edits, then update `main` with `git pull --ff-only origin main`.
Keep your existing `.env`, authored workshop and runtime data. The course now
uses one naming scheme for model access; update an older `.env` before starting:

| Old setting | Rename to |
|---|---|
| `CEREBRAS_API_KEY` or `AOA_OPENAI_API_KEY` | `LLM_API_KEY` — retain the value for the endpoint you use |
| `OPENAI_BASE_URL` | `LLM_BASE_URL` |
| `TYPESAFE_API_KEY` | `DECISION_API_KEY` |

Remove the old entries after renaming; they are no longer read. Keep `PROVIDER`,
`MODEL`, `DECISION_PROVIDER`, `DECISION_MODEL` and `DECISION_BASE_URL` unchanged
when retaining the same services. If your authored EVE `agent.ts` uses the old
environment names, replace those reads with the current
[provider-neutral wiring](../sessions/session-03-eve/WALKTHROUGH.md#checkpoint-2--add-provider-neutral-model-wiring).
Rebuild/restart the session after saving the configuration, then rerun the model
smoke test. This migration does not require another environment file.

If you have used an older setup, check the [migration note](../../archive/course-content-before-review/INDEX.md#updating-an-older-installation) for settings that can override `.env`. Fresh checkouts need only the file above. Exported terminal variables take precedence over `.env`.

Validation and remaining fresh-laptop checks are recorded in [the validation record](../VALIDATION.md). Keep the model stable during the course and inspect quality, failures, latency and cost before considering a replacement.
