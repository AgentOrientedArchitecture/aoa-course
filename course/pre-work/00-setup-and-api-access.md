# AoA Course Pre-Work: Model Access

Before the first hands-on session, set up one working model provider and verify
that the course stack can call it. The runtime supports local Ollama and
OpenAI-compatible hosted APIs through `.env` files in the repo root.

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
bash scripts/test_model_provider.sh
```

Expected result: `status=200` and a short JSON response containing
`{"ok":true}`.

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
bash scripts/test_model_provider.sh
```

Expected result: `status=200` and a short JSON response containing
`{"ok":true}`.

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

Then verify Ollama by starting the stack and checking the service logs:

```bash
./scripts/session2-up.sh
./scripts/logs.sh
```

---

## Run The Course Stack

After `.env` is configured, start the session you are working on:

```bash
./scripts/session2-up.sh
```

or:

```bash
./scripts/session4-up.sh
```

Open [http://localhost:8080](http://localhost:8080) after the containers start.

If you change `.env`, restart the stack:

```bash
./scripts/down.sh
./scripts/session2-up.sh
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
bash scripts/test_model_provider.sh
```

---

## Pre-Work Checklist

- [ ] Choose SambaNova, NVIDIA, or local Ollama on the host.
- [ ] Copy the matching example file to `.env`.
- [ ] Add your hosted API key if using SambaNova or NVIDIA.
- [ ] Run `bash scripts/test_model_provider.sh` if using SambaNova or NVIDIA.
- [ ] Start Session 2 or Session 4 and open the studio.

Last verified: May 2026.
