import { createOpenAI } from "@ai-sdk/openai";
import { defineAgent } from "eve";

// Env-driven, OpenAI-compatible provider. This is the EVE side of the course's
// "indifferent to where reasoning happens" point: the same PROVIDER / MODEL /
// OPENAI_BASE_URL the Python agents use (see system/agents/_base/model.py) drives
// this EVE agent too. Ollama is reached through its OpenAI-compatible /v1 shim.
function baseUrl(): string {
  const explicit = process.env.OPENAI_BASE_URL?.trim();
  if (explicit) return explicit;
  const ollama = process.env.OLLAMA_HOST?.trim();
  if (ollama) return `${ollama.replace(/\/$/, "")}/v1`;
  return "http://localhost:11434/v1";
}

const provider = createOpenAI({
  baseURL: baseUrl(),
  apiKey: process.env.OPENAI_API_KEY || "not-needed-for-local",
});

export default defineAgent({
  model: provider(process.env.MODEL || "gpt-oss:120b"),
  // Local / unlisted model ids have no AI Gateway metadata, so give EVE's
  // compaction an explicit context window instead of letting it look one up.
  modelContextWindowTokens: Number(
    process.env.MODEL_CONTEXT_WINDOW_TOKENS || 128000,
  ),
});
