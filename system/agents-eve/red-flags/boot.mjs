// Capability-specific entry point for the EVE red-flags lab agent. The generic
// adapter remains unchanged; this file maps the agent's input, output and
// evaluation signals onto the common AOA boundary.
import path from "node:path";
import { serve } from "./serve.mjs";

const APP_ROOT = process.env.EVE_APP_ROOT || "/app";

function parseResult(text) {
  if (!text || !text.trim()) return { error: "empty model response" };
  let value = text.trim();
  const fence = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) value = fence[1].trim();
  try {
    return JSON.parse(value);
  } catch {
    const start = value.indexOf("{");
    const end = value.lastIndexOf("}");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(value.slice(start, end + 1));
      } catch {
        // Fall through to the structured error below.
      }
    }
    return { error: "model did not return valid JSON", raw: value.slice(0, 500) };
  }
}

function buildMessage(inputs) {
  return [
    "Review this CV-fit evaluation for risks a human interviewer should probe.",
    "",
    "## Evaluation (JSON)",
    "```json",
    JSON.stringify(inputs.evaluation ?? {}, null, 2),
    "```",
    "",
    "Respond with only the JSON object described in your instructions.",
  ].join("\n");
}

function computeSignals(outputs, latencySeconds) {
  return {
    valid_output_shape:
      outputs && typeof outputs === "object" && !("error" in outputs),
    has_flags: Array.isArray(outputs?.flags) && outputs.flags.length > 0,
    latency_seconds: latencySeconds,
  };
}

serve({
  cardPath: process.env.CARD_PATH || path.join(APP_ROOT, "capability-card.yaml"),
  instructionsPath: path.join(APP_ROOT, "agent", "instructions.md"),
  buildMessage,
  parseResult,
  computeSignals,
}).catch((error) => {
  console.error("[aoa-eve] fatal:", error);
  process.exit(1);
});
