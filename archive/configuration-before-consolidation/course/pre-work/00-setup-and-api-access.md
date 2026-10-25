# AoA Course Pre-Work: Setup and Model Access

Before the first hands-on session, install the base tooling, set up one working
model provider, and verify that the course stack can call it. The runtime
supports local Ollama and OpenAI-compatible hosted APIs through `.env` files in
the repo root. The provider test and Session 3's EVE dependencies run inside
Docker; no host Node/npm installation is required. On macOS and Linux, the
Session 3 adopt script uses `curl` and the Session 4 seed/reset scripts use the
system `python3` (standard library only — no packages or virtualenvs); both
ship with macOS and are preinstalled on most Linux distributions. Windows
learners need neither: the `.bat` scripts use PowerShell.

---

## Base Tooling

You need these before the workshop:

1. **Docker Desktop** (or Docker Engine + Compose v2). Confirm with
   `docker compose version`.
2. **Git**, to clone this repository.

Then build the course containers once at home (this downloads base images —
a few GB — so it must not wait for venue wifi). After configuring `.env`
below, run each session script once and shut down again:

```bash
./scripts/session1-up.sh && ./scripts/down.sh
./scripts/session2-up.sh && ./scripts/down.sh
./scripts/session3-build.sh
./scripts/session4-up.sh && ./scripts/down.sh
```

`session3-build` downloads and builds the complete Session 3 image set,
including the pinned `aoa-course/eve-workshop:0.17.1` toolchain. It does not
start EVE or AOA, run `eve init`, or create learner files; authoring happens
interactively during Session 3. On Windows use `scripts\session3-build.bat`.

This course currently provides three tested environment examples:

- `.env.sambanova` - SambaNova Cloud
- `.env.nvidia` - NVIDIA NIM
- `.env.ollama` - Ollama running locally on your host machine

Use one of these as your starting point, copy it to `.env`, add any required
API key, then run the provider test.

---

## Option 1: SambaNova Cloud

SambaNova is the first hosted provider path for the course.

1. Sign up at [cloud.sambanova.ai](https://cloud.sambanova.ai).
2. Open **API Keys and URLs** in the SambaNova dashboard.
3. Create an API key and save it immediately.
4. Copy the course example:

```bash
cp .env.sambanova .env
```

5. Edit `.env` and set:

```env
PROVIDER=openai
MODEL=gpt-oss-120b
AOA_OPENAI_API_KEY=your-sambanova-key
OPENAI_BASE_URL=https://api.sambanova.ai/v1/
```

Then verify it:

```bash
./scripts/test_model_provider.sh
```

On Windows Command Prompt:

```bat
scripts\test_model_provider.bat
```

The test builds the evaluator image and calls the configured model through the
same provider adapter and container network used by the agents. A successful
check ends with `result=PASS`.

---

## Option 2: NVIDIA NIM

NVIDIA NIM is the second hosted provider path for the course.

1. Sign up at [build.nvidia.com](https://build.nvidia.com).
2. Create an API key at
   [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys).
3. Copy the course example:

```bash
cp .env.nvidia .env
```

4. Edit `.env` and set:

```env
PROVIDER=openai
MODEL=openai/gpt-oss-120b
AOA_OPENAI_API_KEY=your-nvidia-key
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
```

NVIDIA model IDs are provider-prefixed. For this course, use
`openai/gpt-oss-120b`, not `gpt-oss:120b` or `gpt-oss-120b`.

Then verify it:

```bash
./scripts/test_model_provider.sh
```

On Windows Command Prompt:

```bat
scripts\test_model_provider.bat
```

A successful check ends with `result=PASS`.

---

## Option 3: Local Ollama On Your Host

Use this path if you want to run the model on your own machine instead of using
a hosted API. The provided `.env.ollama` file points Docker containers at an
Ollama server running on the host via `http://host.docker.internal:11434`.

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull the model used by the course example:

```bash
ollama pull gpt-oss:20b
```

3. Confirm Ollama is running on your host:

```bash
ollama list
```

4. Copy the course example:

```bash
cp .env.ollama .env
```

The important values are:

```env
PROVIDER=ollama
MODEL=gpt-oss:20b
OLLAMA_HOST=http://host.docker.internal:11434
```

Then verify Ollama through the same Docker runtime used by the agents:

```bash
./scripts/test_model_provider.sh
```

On Windows Command Prompt:

```bat
scripts\test_model_provider.bat
```

A successful check ends with `result=PASS`. On Linux Docker Engine, host Ollama
must listen on an interface reachable from Docker; use the bundled Ollama
container instead if you do not want to expose the host service to the bridge.

---

## Run The Course Stack

After `.env` is configured, start the session you are working on:

```bash
./scripts/session1-up.sh
```

or:

```bash
./scripts/session2-up.sh
```

Open [http://localhost:8080](http://localhost:8080) after the containers start.

If you change `.env`, restart the stack:

```bash
./scripts/down.sh
./scripts/session1-up.sh
```

---

## Common Configuration Checks

For hosted providers:

- `PROVIDER` should be `openai`.
- `AOA_OPENAI_API_KEY` should contain the hosted provider key.
- `OPENAI_BASE_URL` should be the API root ending in `/v1`, not the full
  `/chat/completions` endpoint.
- `MODEL` must use the provider's exact model ID.

For local Ollama on the host:

- `PROVIDER` should be `ollama`.
- `MODEL` should be an Ollama model name that exists in `ollama list`.
- `OLLAMA_HOST` should be `http://host.docker.internal:11434`.
- `AOA_OPENAI_API_KEY` and `OPENAI_BASE_URL` can be blank.

---

## Providers Not Tested In This Course Stack

The providers below may work because they offer OpenAI-compatible APIs, but the
course does not currently provide checked `.env` examples for them:

| Provider | Typical base URL | Notes |
|---|---|---|
| Groq | `https://api.groq.com/openai/v1` | Model IDs and rate limits vary by account. |
| OpenRouter | `https://openrouter.ai/api/v1` | Aggregates many providers; use exact model IDs from OpenRouter. |
| Google AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai/` | OpenAI compatibility differs from standard OpenAI behavior. |
| Mistral AI | `https://api.mistral.ai/v1` | Should be tested with the course payload before relying on it. |

If you use one of these, create your own `.env` from `.env.example`, set
`PROVIDER=openai`, set the provider base URL and key, then run:

```bash
./scripts/test_model_provider.sh
```

On Windows Command Prompt, run `scripts\test_model_provider.bat`.

---

## Pre-Work Checklist

- [ ] Install Docker Desktop (or Docker Engine + Compose v2) and Git.
- [ ] Choose SambaNova, NVIDIA, or local Ollama on the host.
- [ ] Copy the matching example file to `.env`.
- [ ] Add your hosted API key if using SambaNova or NVIDIA.
- [ ] Run the Docker-based provider test for hosted APIs or Ollama:
      `./scripts/test_model_provider.sh` (Windows:
      `scripts\test_model_provider.bat`).
- [ ] Run the Session 1, 2, and 4 start commands once at home, shutting each
      stack down afterwards; run `session3-build` for Session 3.
- [ ] Start any session stack and open the studio.

Last verified: July 2026.
