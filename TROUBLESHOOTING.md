# Troubleshooting

Use the [setup guide](course/pre-work/SETUP.md) and the session's
`WALKTHROUGH.md`. Run course scripts from the repository root in the host
terminal. The `eve-workshop>` prompt is a separate container shell for EVE
commands.

## Containers will not start / port already in use

A previous course checkout may still own 8080, 7100, 7200, 7250, 73xx, 74xx or
the Directory ports 8890/8891. Stop the previous course stack from its checkout
before starting another one.

macOS/Linux:

```bash
./scripts/down.sh
docker ps
```

Windows Command Prompt:

```bat
scripts\down.bat
docker ps
```

The stop scripts retain authored files, saved cases, wiki data and model
volumes. If Docker Desktop reports insufficient memory, increase its resource
allocation. Local model memory requirements are additional to the course
containers; choose a model that fits the laptop.

## Studio loads but the Registry pane is empty

Agents register at boot and retry until the registry is healthy. Give them a
few seconds, then inspect the logs:

```bash
./scripts/logs.sh
```

On Windows use `scripts\logs.bat`. Look for registration and service-start
errors. Use the public session launcher; it sets the active capability
allowlist in `scripts/compose.sh` or `scripts\compose.bat`. There is one current
Compose file, `system/docker-compose.yml`. Direct Compose commands with only a
profile omit those session settings.

## Generation calls fail

First run the Docker-based provider check. It uses the same image, environment,
SDKs, adapter and container network as the Python course agents. No host
Python or Node installation is needed.

macOS/Linux:

```bash
./scripts/test_model_provider.sh
```

Windows Command Prompt:

```bat
scripts\test_model_provider.bat
```

A successful check ends with `result=PASS`. It checks generation access, not a
TypeSafe decision or the complete course workflow.

Check the private `.env` against `.env.example`:

- **Cerebras:** `PROVIDER=openai`, `MODEL=gpt-oss-120b`,
  `OPENAI_BASE_URL=https://api.cerebras.ai/v1`, and `CEREBRAS_API_KEY`.
- **Another OpenAI-compatible provider:** clear `CEREBRAS_API_KEY`, then set
  `AOA_OPENAI_API_KEY`, the provider's exact model ID and its API root ending
  in `/v1`. Do not use the `/chat/completions` request path as the base URL.
- **Local Ollama:** use the local settings in the same `.env.example`,
  including `PROVIDER=ollama`, `OLLAMA_HOST` and EVE's `OPENAI_BASE_URL`.
  Confirm the selected model appears in `ollama list`. On Linux Docker Engine,
  Ollama must listen on an interface the Docker bridge can reach.
- **Bundled Ollama:** the optional `local` Compose profile is also supported.
  Follow the [setup guide](course/pre-work/SETUP.md); the model host is
  `http://ollama:11434` inside the course network.

`model_not_found` means the provider does not recognise the configured model
ID. Hosted and local IDs differ, for example `gpt-oss-120b` and `gpt-oss:120b`.
After editing `.env`, stop and rerun the relevant session launcher. Existing
checkouts may have a private legacy overlay that overrides `.env`; the setup
guide explains migration. Do not create another environment file to work
around an error.

## AU selection or wiki promotion stops before a result

A generation-provider check can pass while decision-provider access fails.
For hosted decisions, confirm `.env` contains `DECISION_PROVIDER=typesafe`,
`DECISION_MODEL=jev-1.13.0`, `DECISION_BASE_URL=https://api.typesafe.ai` and
`TYPESAFE_API_KEY`. Then restart using the session launcher.

In **AU selection**, inspect candidate eligibility, returned choice and the
acceptance threshold. No eligible capability, `no_suitable_capability`, a low
model probability or provider failure deliberately stops work. They are
separate outcomes. Correct configuration errors; do not lower the threshold
merely to make a demonstration proceed.

The local decision option is an unscored constrained-choice baseline. Follow
its complete setup, including `DECISION_ALLOW_UNSCORED=true`; it is not Jev and
supplies no comparable probability estimate.

## Session 3: generated files are missing on the laptop

At `eve-workshop>`, `pwd` should show `/workshop`. The host launcher prints the
host and checkout folder backing that mount. The generated files belong under
`system/agents-eve/workshop/agent/` in that exact checkout.

A terminal window on the Mac can still be an SSH session on Spark. Check the
host shown by the launcher, and compare the folder with the editor. Run `exit`
to leave the EVE shell and inspect the host checkout. Do not initialise a
second copy until the active host and mount are clear.

## Session 3: native EVE model calls fail

Use the provider-neutral `agent.ts` in the
[Session 3 walkthrough](course/sessions/session-03-eve/WALKTHROUGH.md). Check
that the workshop received the model and endpoint settings from the course
`.env`. The launcher supplies the appropriate key as `OPENAI_API_KEY`; do not
paste a key into the TypeScript source.

If the error mentions a missing `input` field and a URL ending in `/responses`,
check whether `agent.ts` uses `provider(...)`. The course uses
`provider.chat(...)` for the Chat Completions API. Apply the walkthrough's
configuration, stop `eve dev` with Ctrl+C, and restart it.

The generated scaffold can attempt its default model before the course wiring
is installed. Follow the walkthrough's configuration and acceptance checkpoints
before diagnosing the configured course agent.

## Session 3: EVE permissions or image build failure

For `EACCES: permission denied, mkdir '/app/node_modules/eve/.eve'`, leave the
workshop and rebuild the course image from the updated checkout:

```bash
./scripts/session3-build.sh
./scripts/session3-up.sh
```

On Windows use `scripts\session3-build.bat` and `scripts\session3-up.bat`.
The image prepares EVE's package-local workflow cache for the workshop user.
Rebuilding preserves the authored workshop files; avoid editing installed
packages or running the workshop as root as a workaround.

Confirm the image exists with
`docker image inspect aoa-course/eve-workshop:0.17.1`. It contains Node and the
pinned EVE toolchain, but no authored learner agent. If a laptop has not
completed pre-work and cannot fetch its build dependencies during class, use a
prepared machine and keep the learner's files in their own checkout.

## I edited instructions.md / capability-card.yaml and nothing changed

For Python agents in Sessions 1, 2 and 4:

- Inspect the card's `skills_hash` after an instruction edit, or its fields
  after a card edit. The watcher re-registers the change.
- Edit the correct checkout's `system/agents/<agent>/capabilities/...` files on
  the host; they are mounted read-only inside the container.
- Python code is baked into the image. Code edits require rerunning the
  session launcher, which rebuilds.
- In Sessions 3–4, allow the Directory adapter to republish a changed AU.
  A stale Directory binding stops a new plan until publication catches up.

For EVE, keep the build-then-adopt boundary. Retest `agent.ts` or
`instructions.md` natively with `session3-up` and `eve dev`, then rerun
`session3-adopt`. Changes to `workshop/capability-card.yaml` also require
`session3-adopt` to revalidate and republish the contract.

## Session 3 or 4: AGNTCY discovery is unavailable or stale

Use the Directory inspection step in the
[Session 3 walkthrough](course/sessions/session-03-eve/WALKTHROUGH.md). From the
host repository root, request publication and wait for indexing:

```bash
./scripts/directory.sh sync --wait 120
```

On Windows use `scripts\directory.bat sync --wait 120`. Inspect Directory and
adapter logs if it fails. Use the session launcher to start the full active
estate. The planner deliberately does not fall back to local-only AU discovery
in Sessions 3–4. A catalogue card is a projection; pull the OASF JSON to inspect
the complete record and its content ID.

## Session 4: every finding says corpus silent

Seed and verify the regulations corpus:

```bash
./scripts/session4-seed.sh
```

On Windows use `scripts\session4-seed.bat`. Follow the prerequisite in the
[Session 4 walkthrough](course/sessions/session-04-compliance/WALKTHROUGH.md):
the shell seed script uses host Python 3; the batch route uses PowerShell.

## Session 4: Article 12 is red

The course check looks for trace evidence for each capability. Run an eligible
CV-fit workflow, then rerun **Agent card check**. Only the capabilities actually
invoked will gain that evidence. Green reports the presence of this narrow
signal; it does not establish satisfaction of Article 12 or legal compliance.

## Session 4: a previous case remains after stopping

This is expected. Cases and events persist in SQLite, and JSONL files are an
audit projection. Stop/start retains them. Open the saved case to inspect or
review its held result, or submit a new intent to create another case.

Deleting JSONL does not delete the authoritative case state and can remove
visible evidence until the projection is regenerated. The retained
`session4-reset.sh` is a legacy destructive helper: it clears wiki data and
JSONL and removes the learner's review constraint, but does not reset SQLite
cases. Do not use it as the current course restart procedure.

## Start in a separate clean checkout

Stop the existing stack, then follow the setup guide in a new checkout of
`main`. Keep the old checkout until any authored EVE files, private keys, wiki
material and cases you need have been preserved. A fresh checkout gives the
new walkthrough its intended starting files without deleting work in the old
one. Run only one course stack at a time because the services share ports and
container names.
