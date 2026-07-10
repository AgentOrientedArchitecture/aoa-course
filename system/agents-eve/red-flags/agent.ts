import { createOpenAI } from "@ai-sdk/openai";
import { defineAgent } from "eve";

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
  modelContextWindowTokens: Number(
    process.env.MODEL_CONTEXT_WINDOW_TOKENS || 128000,
  ),
});
