# Shared agent scaffold

`base.py` is the FastAPI scaffold every agent in this system extends.

It handles the four jobs every agent does the same way:

1. Discovers capability cards under `capabilities/<name>/`.
2. Computes `skills_hash` for each by SHA-ing the matching `skills.md`.
3. Stamps each card with a stable `agent_id`/`identity` for policy, trace, and audit.
4. Registers each capability with the registry on boot.
5. Watches each `skills.md` for changes and re-registers on edit.

`agent_id` identifies the acting AU runtime (`urn:aoa:agent:parser`,
`urn:aoa:agent:evaluator`, `urn:aoa:agent:reporter` in the course compose
file). `skills_hash` identifies the current working instructions for a
capability. Editing `skills.md` changes the hash and updates registration, but
it does not create a new agent identity.

A concrete agent provides a `handle(capability_id, inputs, ctx) -> outputs` function and a couple of lines of wiring. See [`AGENTS.md`](../../AGENTS.md) for the agent contract; see any of the agents under `agents/` for examples.

## What's in here

- `base.py` — the scaffold.
- `model.py` — a thin wrapper around the configured model provider (OpenAI, Anthropic, Ollama). Agents call `model.complete(prompt, **opts)` and don't know which provider is behind it.
- `registry_client.py` — a small HTTP client for talking to the registry service.
- `Dockerfile` — base image for agent containers.
- `requirements.txt` — runtime dependencies shared across agents.

Concrete agents inherit the base image and add their own `agent.py`.
