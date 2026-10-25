# Revised model access

Use Docker and the existing course repository. macOS/Linux use `.sh` launchers; Windows Command Prompt uses the matching `.bat` launchers with Docker Desktop running Linux containers. EVE and the AGNTCY Directory tools run in containers. No separate WSL checkout, host Python or host `dirctl` installation is needed for the Directory lab; WSL2 remains an optional way to run the shell launchers.

## Get the October course

Use **`main`** for the course, including the revised examples, Studio inspection views and architecture documentation. The separate `aoa-course-v2` prototype and `feat/decision-allocator` branch are not prerequisites for this walkthrough.

For a fresh participant-install test, clone into a new directory. This avoids reusing saved cases, uploaded inputs or an authored EVE workshop from an earlier run. Keep the existing checkout and its data.

On **macOS/Linux**, use Terminal. On **Windows**, use Command Prompt, or a WSL2 Linux terminal with Docker available there. The following clone and check commands work in either:

```bash
git clone --branch main https://github.com/AgentOrientedArchitecture/aoa-course.git aoa-course-october-test
cd aoa-course-october-test
git status --short --branch
docker compose version
```

Confirm that the branch is `main` and Docker Compose is available before continuing. Configure one model route below, then use the matching session launcher. The presence of `.env.revised` selects the revised course automatically.

### Update an existing checkout

Run `git status --short` first. Commit or otherwise save any listed source edits before switching branches; keep existing configuration and learner data. From the repository root:

```bash
git remote set-branches --add origin main
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --branch
```

The first command also makes `main` available to checkouts originally cloned with `--single-branch`. These commands work in Terminal, Windows Command Prompt and WSL2. They retain existing branches and do not reset the EVE workshop, saved cases or private environment files. For later updates while already on `main`, use `git pull --ff-only origin main`; if Git reports divergent commits or local changes, resolve those rather than resetting the checkout.

The recorded end-to-end validation is on Spark. Fresh macOS and Windows walkthroughs are pending; see [validation record](../REVISED-VALIDATION.md). Record any setup or instruction failures as part of those tests.

## Hosted route

Copy `.env.cerebras-typesafe.example` to `.env.revised`. Add keys privately as `CEREBRAS_API_KEY` and `TYPESAFE_API_KEY`; alternatively keep keys in the ignored `.env` and leave them out of `.env.revised`. Never commit populated environment files.

In a fresh checkout:

```bash
cp .env.cerebras-typesafe.example .env.revised
```

In Windows Command Prompt, use `copy .env.cerebras-typesafe.example .env.revised` instead. For the local route below, use the same copy command with `.env.local-revised.example`.

Add the keys in your local editor before starting. Git transfers the example configuration, not the private keys stored on Spark. If `.env.revised` already exists, inspect it before replacing it.

The revised launchers load `.env` first, then `.env.revised`. Values set in the second file override the first; exported terminal variables take precedence over both. The example leaves key variables unset so existing keys in `.env` are retained. The original course selection loads only `.env`.

Generation uses the existing OpenAI-compatible adapter, Cerebras's endpoint and `gpt-oss-120b`. Decisions use TypeSafe's separate typed-choice API with the version pinned to `jev-1.13.0`. A model ID is recorded with each decision; the stable version avoids following the latest alias during a class.

Check provider access before the live session. Do not assume a permanent free tier or enough quota for a room of learners. Cerebras currently describes trial credits and free-trial rate limits; TypeSafe account access, credit and organisation limits need checking in the account. A provider outage or exhausted quota produces a visible error, never an unlabelled replacement decision.

Current primary references (checked 21 October 2026): [Cerebras rate limits](https://inference-docs.cerebras.ai/support/rate-limits), [Cerebras pricing](https://www.cerebras.ai/pricing), [TypeSafe models](https://docs.typesafe.ai/models), [TypeSafe Choice](https://docs.typesafe.ai/primitives/choice).

## Local route

Copy `.env.local-revised.example` to `.env.revised`. Install Ollama on the host and pull `gpt-oss:20b`, or choose another available model explicitly. On capable hardware use `gpt-oss:120b` for generation to retain the course comparison. The example uses the smaller model to keep an ordinary local option.

The decision baseline uses Ollama's constrained JSON output and temperature zero. It reports a named choice and **no probability estimate**. `DECISION_ALLOW_UNSCORED=true` is an explicit classroom policy. Schema constraints and temperature zero do not establish semantic accuracy, calibration or universal determinism.

Host Ollama is reached from containers at `host.docker.internal:11434`. For container Ollama, set both model endpoints to `http://ollama:11434`, set `AOA_LOCAL=1` when starting and ensure the named models are pulled into that container. Local and hosted routes use the same AU contracts and inspectable execution path.

## Start and stop

Run from the repository root after creating `.env.revised`:

| Action | macOS/Linux or WSL2 | Windows Command Prompt |
|---|---|---|
| Check generation provider access | `./scripts/test_model_provider.sh` | `scripts\test_model_provider.bat` |
| Session 1: CV | `./scripts/session1-up.sh` | `scripts\session1-up.bat` |
| Session 2: wiki | `./scripts/session2-up.sh` | `scripts\session2-up.bat` |
| Session 3: pre-build images | `./scripts/session3-build.sh` | `scripts\session3-build.bat` |
| Session 3: native EVE authoring | `./scripts/session3-up.sh` | `scripts\session3-up.bat` |
| Session 3: adopt the tested agent | `./scripts/session3-adopt.sh` | `scripts\session3-adopt.bat` |
| Session 3: start AGNTCY Directory | `./scripts/directory.sh up` | `scripts\directory.bat up` |
| Stop only AGNTCY Directory | `./scripts/directory.sh stop` | `scripts\directory.bat stop` |
| Session 4: compliance | `./scripts/session4-up.sh` | `scripts\session4-up.bat` |
| Seed Session 4 evidence after startup | `./scripts/session4-seed.sh` | `scripts\session4-seed.bat` |
| Follow service logs | `./scripts/logs.sh` | `scripts\logs.bat` |
| Stop course services | `./scripts/down.sh` | `scripts\down.bat` |

Session 3's native authoring step stops the running AOA services so learners can inspect EVE on its own. After authoring and native testing, exit that shell and use the adoption launcher. Adoption builds the image before installing dependencies, retains existing learner files/cards, and checks both agent health and registry presence before reporting success.

`down` includes every original and revised Compose service, including the decision service, specialist CV evaluators, EVE, AGNTCY Directory and container Ollama. It retains volumes, saved cases, Directory records, wiki state and authored workshop files by default. `logs` covers the same service set; add a service name to narrow it. A Directory started through the optional native-host route still needs Ctrl+C in its terminal. Host-installed Ollama is also independent of Compose.

The explicit revised entry points remain available on both platforms: `revised-up.sh/.bat 1`, `2` or `4`, and `revised-eve.sh/.bat build`, `native` or `adopt`. They always choose the revised configuration. The ordinary session launchers instead honour `AOA_REVISED`: `1`/`true` forces revised, `0`/`false` forces original, and unset/`auto` selects by the presence of `.env.revised`. On macOS/Linux, for example, `AOA_REVISED=0 ./scripts/session1-up.sh` runs the original course. In Windows Command Prompt, run `set AOA_REVISED=0` first; `set AOA_REVISED=` restores automatic selection.

Open `http://localhost:8080`. Check `http://localhost:7250/healthz` from the host: it names the decision provider/model and says whether configuration is present. It does **not** claim a successful provider call. Run the first CV example to verify actual access.

Keep the model choice stable during the four sessions. Record model, prompts/skills hashes, candidate cards, task quality, failure/abstention rate, latency, usage and cost before considering a replacement. Do not compare a hosted price with local zero: local compute and operator time still have a cost.
