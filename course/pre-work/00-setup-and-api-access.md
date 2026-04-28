# AoA Course — Pre-Work: Getting Access to an LLM API

Welcome to the pre-course setup guide. Before the first session, every participant needs working API access to at least one LLM provider. A core principle of the **Architecture of Agents (AoA)** course is favouring **smaller, efficient models** over frontier heavyweights — they're faster, cheaper, and often more than sufficient for well-designed agentic systems.

This guide will get you set up with free-tier API access in under 30 minutes. **No credit card is required for any provider listed here.**

---

## Why Multiple Providers?

Different providers have different rate limits, models, and speeds. By signing up to several, you avoid hitting a wall mid-exercise. The code pattern is identical across all of them — you just swap a URL and a key.

---

## Step 1: The Core Providers

Sign up to **at least two** from this list before the course begins. We recommend signing up to all of them — it only takes a few minutes each.

### 🟢 NVIDIA NIM *(Highest Priority)*

**The home of `gpt-oss-120b`** — the primary model used throughout this course.

- **Sign up:** [build.nvidia.com](https://build.nvidia.com)
- Requires a free NVIDIA Developer Program account — phone number verification takes ~1 minute
- **Generate your key:** [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys)
- Your key will start with `nvapi-`
- **Base URL:** `https://integrate.api.nvidia.com/v1`
- **Free tier:** 1,000 credits on signup, up to 5,000 requestable, 40 RPM
- **100+ models available** including Llama 3.3 70B, Qwen3 235B, and more

### 🟢 Cerebras *(Speed Champion)*

Ultra-fast inference — often 1,000+ tokens/second. Excellent for agent loops.

- **Sign up:** [cloud.cerebras.ai](https://cloud.cerebras.ai)
- Navigate to **API Keys** in your dashboard after signup
- **Free tier:** 1M tokens/day, 30 RPM, 14,400 requests/day
- **Key models:** `gpt-oss-120b`, Llama 3.3 70B, Qwen3 235B

### 🟢 SambaNova Cloud *(Speed Champion #2)*

Another speed-optimised inference platform, excellent for rapid iteration.

- **Sign up:** [cloud.sambanova.ai](https://cloud.sambanova.ai)
- After signup, go to **API Keys and URLs** in the dashboard
- Save your key immediately — it cannot be retrieved again
- **Key models:** Llama 3.3 70B, DeepSeek models, Qwen3 family

### 🟢 Groq

Extremely fast LPU-powered inference. Great for exercises requiring real-time responsiveness.

- **Sign up:** [console.groq.com](https://console.groq.com)
- Sign up with email or GitHub — no credit card required
- Generate your key under **API Keys** in the console
- **Free tier:** All models available, rate-limited per model, refreshes daily
- **Key models:** Llama 3.3 70B, Llama 4 Scout, Kimi K2

### 🟡 OpenRouter *(The Aggregator — Optional but Recommended)*

One API key that routes to 30+ free models. Ideal if you want a single key for everything.

- **Sign up:** [openrouter.ai](https://openrouter.ai)
- Create your API key from the dashboard — no card required
- **Free tier:** 20 RPM, 200 requests/day per model
- Use model IDs ending in `:free` e.g. `meta-llama/llama-3.3-70b-instruct:free`
- **Bonus:** Routes to NVIDIA NIM models too, so one key covers both

### 🟡 Google AI Studio *(Best Backup — Optional)*

Most generous daily limits of any provider. Good safety net for intensive exercises.

- **Sign up:** [aistudio.google.com](https://aistudio.google.com)
- Sign in with any Google account, then click **Get API Key → Create API Key**
- **Free tier:** 1,500 requests/day, 1M token context window
- **Base URL:** `https://generativelanguage.googleapis.com/v1beta/openai/` (OpenAI-compatible)

### 🟡 Mistral AI *(EU-Hosted — Optional)*

Excellent for participants who prefer EU-hosted infrastructure.

- **Sign up:** [console.mistral.ai](https://console.mistral.ai)
- The free **Experiment** tier requires no credit card
- **Free tier:** ~1 req/s, 30 RPM, access to all Mistral models
- **Key models:** Mistral Large 3, Mistral Small 3.1, Ministral 8B

---

## Step 2: Store Your Keys Safely

Never hardcode API keys in your scripts. Set them as environment variables.

A `.env.example` file is included at the root of this repo — copy it to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Or add them to your shell profile:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxx"
export CEREBRAS_API_KEY="csk-xxxxxxxxxxxx"
export SAMBANOVA_API_KEY="xxxxxxxxxxxxxxxx"
export GROQ_API_KEY="gsk_xxxxxxxxxxxx"
export OPENROUTER_API_KEY="sk-or-xxxxxxxxxxxx"
export GEMINI_API_KEY="AIzaxxxxxxxxxxxxxxxx"
export MISTRAL_API_KEY="xxxxxxxxxxxxxxxx"
```

Then reload: `source ~/.bashrc`

---

## Step 3: Validate Your Setup

All providers use the **OpenAI-compatible API format**. This means the same Python code works everywhere — you only change two values: the `base_url` and the `api_key`.

Run this test snippet for each provider you've signed up to:

```python
from openai import OpenAI
import os

# Swap these two lines per provider — everything else stays the same
BASE_URL = "https://integrate.api.nvidia.com/v1"   # NVIDIA NIM
API_KEY  = os.environ["NVIDIA_API_KEY"]

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

response = client.chat.completions.create(
    model="nvidia/gpt-oss-120b",   # change model ID per provider
    messages=[{"role": "user", "content": "Hello! Reply in one sentence."}],
    max_tokens=64
)

print(response.choices[0].message.content)
```

### Provider Quick-Reference

| Provider | `base_url` | Example Model ID | Env Var |
|---|---|---|---|
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | `nvidia/gpt-oss-120b` | `NVIDIA_API_KEY` |
| Cerebras | `https://api.cerebras.ai/v1` | `gpt-oss-120b` | `CEREBRAS_API_KEY` |
| SambaNova | `https://api.sambanova.ai/v1` | `Meta-Llama-3.3-70B-Instruct` | `SAMBANOVA_API_KEY` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `meta-llama/llama-3.3-70b-instruct:free` | `OPENROUTER_API_KEY` |
| Google AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` | `GEMINI_API_KEY` |
| Mistral | `https://api.mistral.ai/v1` | `mistral-small-latest` | `MISTRAL_API_KEY` |

---

## Step 4: Handle Rate Limits Gracefully

You will hit `429 Too Many Requests` during the course — this is expected and is actually **your first lesson in agentic resilience**. Add this pattern to your scripts:

```python
import time

def call_with_retry(client, model, messages, retries=3):
    for attempt in range(retries):
        try:
            return client.chat.completions.create(
                model=model, messages=messages, max_tokens=256
            )
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 2 ** attempt   # exponential backoff: 1s, 2s, 4s
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
```

If you consistently hit limits on one provider, simply switch to another — the code change is two lines.

---

## ✅ Pre-Work Checklist

Before Session 1, confirm you can tick these off:

- [ ] Signed up to **NVIDIA NIM** and have an `nvapi-` key
- [ ] Signed up to **at least one** speed provider (Cerebras or SambaNova)
- [ ] Signed up to **Groq**
- [ ] All keys stored as environment variables (not hardcoded in scripts)
- [ ] Successfully ran the validation snippet and got a response back
- [ ] *(Optional)* OpenRouter key set up for single-key convenience

If you hit any issues during setup, bring them to the start of Session 1 — troubleshooting environment setup together is a valuable shared experience.

---

## Why Not Just Use GPT-4 or Claude?

A core AoA principle is that **model choice should match task complexity**. Reaching for the most powerful frontier model by default is an antipattern — it's slower, more expensive, and trains you to paper over weak architecture with raw capability. Throughout this course you'll develop the instinct for when a 7B model is enough, when 70B is appropriate, and when (rarely) a frontier model is genuinely warranted.

`gpt-oss-120b` is our default recommendation — it's capable, fast on the right hardware, open-weight, and available free via multiple providers above.

---

*This guide will be updated as provider free tiers evolve. Last verified: April 2026.*
