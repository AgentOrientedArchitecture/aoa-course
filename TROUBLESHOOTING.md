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

- **Hosted (SambaNova / NVIDIA):** `PROVIDER=openai`, the provider's exact
  model id in `MODEL`, key in `AOA_OPENAI_API_KEY`, and `OPENAI_BASE_URL`
  ending in `/v1` (not `/chat/completions`). Verify with
  `bash scripts/test_model_provider.sh` — expect `status=200` and `{"ok":true}`.
- **Local Ollama on the host:** `PROVIDER=ollama`,
  `OLLAMA_HOST=http://host.docker.internal:11434`, and a model that appears in
  `ollama list`. If you want the bundled Ollama container instead, set
  `AOA_LOCAL=1` and `OLLAMA_HOST=http://ollama:11434`.
- `model_not_found` in a trace means the `MODEL` id doesn't exist at the
  provider — ids differ per provider (`gpt-oss:120b` vs `openai/gpt-oss-120b`).

Changed `.env`? Restart: `./scripts/down.sh && ./scripts/sessionN-up.sh`.

## SambaNova rejects the EVE agent / "tool role not supported"

Expected: some OpenAI-compatible endpoints reject the `tool` message role. The
course's EVE agent deliberately runs tool-free (sentinels in
`system/agents-eve/interviewer/agent/tools/`) so it works on all tested
providers. If you enabled real EVE tools in the enrichment exercise, switch to
Ollama or NVIDIA NIM for that agent.

## I edited instructions.md / capability-card.yaml and nothing changed

- The watcher re-registers within a second or two — watch the Registry pane's
  `skills_hash` chip (instructions) or the card fields (card edits).
- Editing the **wrong copy** is the classic miss: edit the files under
  `system/agents/<agent>/capabilities/...` on the **host** — they are mounted
  into the containers read-only.
- Agent **code** (`agent.py`, `_base/`) is baked into the image, not mounted:
  code changes need `./scripts/sessionN-up.sh` again (it rebuilds).

## Session 3: `npx eve@latest init` is slow or fails at the venue

Warm the cache at home (`npx eve@latest --version`) per the pre-work. Node
must be ≥ 20 (`node --version`). Corporate proxies that break npm: set
`npm_config_proxy`/`https-proxy` or use a hotspot.

## Session 4: every finding says "corpus silent"

The regulations corpus isn't seeded. Run:

```bash
./scripts/session4-seed.sh
```

## Session 4: Article 12 is red for everything

Correct behaviour, not a bug: Art 12 (record-keeping) goes green only when
trace evidence exists for a capability. Run one CV-fit workflow, then re-run
the estate check.

## Start over completely

```bash
./scripts/down.sh
docker compose -f system/docker-compose.yml down -v --remove-orphans
rm -f system/services/planner/traces/*.jsonl
git checkout -- system/services/registry/data/cards.json 2>/dev/null || true
./scripts/sessionN-up.sh
```

For Session 4's staged demo state specifically, use `./scripts/session4-reset.sh`.
