# Troubleshooting

The failures people actually hit, in the order they usually hit them.

## Containers won't start / port already in use

Something else owns 8080, 7100, 7200, 73xx, or 74xx. Find it and stop it, or
stop a previous course stack:

```bash
./scripts/down.sh        # stops every profile's containers
docker ps                # anything left listening?
```

Docker Desktop with too little memory (< 4 GB) can also kill containers at
startup — raise it in Docker Desktop → Settings → Resources.

## The Studio loads but the Registry pane is empty

The agents register on boot and retry until the registry is healthy, so give
it ~15 seconds after `up`. Still empty:

```bash
./scripts/logs.sh | grep -i "register"
```

A `REGISTRY_CARD_ALLOWLIST` mismatch (per session overlay) silently filters
cards — check the session's `docker-compose.session*.yml` if you've been
editing capability ids.

## Model calls fail (workflow errors at the evaluator/parser step)

Nine times out of ten this is `.env`:

First run the Docker-based provider check. It uses the same image, environment,
SDKs, provider adapter, and container network as the course agents—no host
Python, Node, or `curl` is needed:

```bash
./scripts/test_model_provider.sh
```

On Windows Command Prompt:

```bat
scripts\test_model_provider.bat
```

A successful check ends with `result=PASS`. If it fails, check:

- **Hosted (SambaNova / NVIDIA):** `PROVIDER=openai`, the provider's exact
  model id in `MODEL`, key in `AOA_OPENAI_API_KEY`, and `OPENAI_BASE_URL`
  ending in `/v1` (not `/chat/completions`).
- **Local Ollama on the host:** `PROVIDER=ollama`,
  `OLLAMA_HOST=http://host.docker.internal:11434`, and a model that appears in
  `ollama list`. On Linux Docker Engine, Ollama must listen on an interface the
  Docker bridge can reach; alternatively use the bundled Ollama container. If
  using the bundled container, set `OLLAMA_HOST=http://ollama:11434` and start
  its `local` profile as directed by the test's failure hint.
- `model_not_found` in a trace means the `MODEL` id doesn't exist at the
  provider — ids differ per provider (`gpt-oss:120b` vs `openai/gpt-oss-120b`).

Changed `.env`? Restart: `./scripts/down.sh && ./scripts/sessionN-up.sh`.

## Session 3: native EVE model calls fail

The learner-authored `system/agents-eve/workshop/agent/agent.ts` should use the
provider-neutral OpenAI-compatible wiring from the exercise. Check that the
workshop received `MODEL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and
`OLLAMA_HOST` from the course `.env`. First verify the provider using the checks
above, then reopen the native workshop with `session3-up` and retry `eve dev`.

If the error is `AI_APICallError: field 'input' is required` and the URL in the
stack trace ends in `/responses`, your `agent.ts` selects the model with
`provider(...)`, which targets OpenAI's newer Responses API. SambaNova,
Ollama's `/v1` shim, and most OpenAI-compatible providers only implement
`/chat/completions`. Use `provider.chat(...)` as in the walkthrough's
Checkpoint 2 file, then restart `eve dev`.


## I edited instructions.md / capability-card.yaml and nothing changed

For the Python agents in Sessions 1, 2, and 4:

- The watcher re-registers within a second or two — watch the Registry pane's
  `skills_hash` chip (instructions) or the card fields (card edits).
- Editing the **wrong copy** is the classic miss: edit the files under
  `system/agents/<agent>/capabilities/...` on the **host** — they are mounted
  into the containers read-only.
- Agent **code** (`agent.py`, `_base/`) is baked into the image, not mounted:
  code changes need `./scripts/sessionN-up.sh` again (it rebuilds).

Session 3 has a deliberate build-then-adopt boundary. Learner files live under
`system/agents-eve/workshop/`, while course runtime infrastructure lives under
`system/agents-eve/runtime/`. Retest `agent.ts` or `instructions.md` natively
with `session3-up` and `eve dev`; then rerun `session3-adopt` before checking AOA.
Edits to the generated `workshop/capability-card.yaml` also require rerunning
`session3-adopt` so the contract is revalidated and republished.

## Session 3: the EVE workshop image did not build

Build it at home with `./scripts/session3-build.sh` (Windows:
`scripts\session3-build.bat`). The image contains Node and the pinned EVE
toolchain, but no authored learner agent. Confirm it exists with
`docker image inspect aoa-course/eve-workshop:0.17.1`. If a laptop missed
pre-work, pair with a prepared neighbour rather than installing packages over
venue wifi.

## Session 4: every finding says "corpus silent"

The regulations corpus isn't seeded. Run:

```bash
./scripts/session4-seed.sh
```

On Windows Command Prompt:

```bat
scripts\session4-seed.bat
```

## Session 4: Article 12 is red for everything

Correct behaviour, not a bug: Art 12 (record-keeping) goes green only when
trace evidence exists for a capability. Run one CV-fit workflow, then re-run
**Agent card check**.

## Start over completely

```bash
./scripts/down.sh
docker compose -f system/docker-compose.yml down -v --remove-orphans
rm -f system/services/planner/traces/*.jsonl
rm -f system/services/registry/data/cards.json
./scripts/sessionN-up.sh
```

For Session 4's learner baseline on macOS or Linux, use
`./scripts/session4-reset.sh`, then rerun `./scripts/session4-seed.sh`.
