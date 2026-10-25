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

- **Generation:** Cerebras, `gpt-oss-120b`. Add `CEREBRAS_API_KEY` privately.
- **Decisions:** TypeSafe, pinned `jev-1.13.0`. Add `TYPESAFE_API_KEY` privately.

Run `./scripts/test_model_provider.sh` (Windows: `scripts\test_model_provider.bat`). It makes a small real generation request and should finish with `result=PASS`. This check does not test TypeSafe; the first CV run tests the decision path. Keys on Spark are not transferred by Git.

`PROVIDER=openai` means the OpenAI-compatible adapter; the endpoint selects Cerebras. The course maps `CEREBRAS_API_KEY` to the container's `OPENAI_API_KEY`. Other compatible providers can still use `AOA_OPENAI_API_KEY`, their endpoint and exact model ID; clear `CEREBRAS_API_KEY` when switching away from Cerebras. Keep TypeSafe configured for decisions or choose the local decision route below.

Check provider credit and account limits before class. The example does not promise a free tier or enough quota for a room of learners. Errors remain visible rather than silently replacing a provider.

## Local models

Use the **same `.env`**. Its commented LOCAL OPTION lists the settings to change; uncommenting duplicate keys is unnecessary—edit the existing values. Install Ollama on the laptop and pull the named model first:

```bash
ollama pull gpt-oss:20b
```

Set `PROVIDER=ollama`, `MODEL=gpt-oss:20b`, `DECISION_PROVIDER=ollama`, `DECISION_MODEL=gpt-oss:20b`, and the listed local endpoints. Set `OPENAI_BASE_URL=http://host.docker.internal:11434/v1` as well: EVE uses Ollama's OpenAI-compatible interface. Increase the timeouts as shown in the example. Use `gpt-oss:120b` for generation where hardware permits.

The local decision baseline uses constrained JSON and reports no calibrated probability. `DECISION_ALLOW_UNSCORED=true` is an explicit classroom policy; it does not make the local model equivalent to Jev. Time the local route before teaching it.

Optional container Ollama is retained: start with `AOA_LOCAL=1` in the shell, set `OLLAMA_HOST` and `DECISION_BASE_URL` to `http://ollama:11434`, set `OPENAI_BASE_URL=http://ollama:11434/v1`, and pull the model into that container. On Windows run `set AOA_LOCAL=1` before the launcher.

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

Save any source edits, then update `main` with `git pull --ff-only origin main`. Keep your existing `.env`, authored workshop and runtime data. A current Cerebras/TypeSafe configuration already saved as `.env` needs no rename or additional file.

If you have used an older setup, check the [migration note](../../archive/course-content-before-review/INDEX.md#updating-an-older-installation) for settings that can override `.env`. Fresh checkouts need only the file above. Exported terminal variables take precedence over `.env`.

Validation and remaining fresh-laptop checks are recorded in [the validation record](../VALIDATION.md). Keep the model stable during the course and inspect quality, failures, latency and cost before considering a replacement.
