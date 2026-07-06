// Entry point for the eve-interviewer container.
//
// Everything AOA-generic lives in adapter/serve.mjs. This file holds only the
// three agent-specific decisions: how to phrase the turn from the AOA inputs,
// how to parse the model's reply into AOA outputs, and how to read
// machine-checkable signals off the result. Copy this folder to make a new
// EVE-authored AU.
import path from "node:path";
import { serve } from "./serve.mjs";

const APP_ROOT = process.env.EVE_APP_ROOT || "/app";

// Tolerant JSON extraction — the same prompt-then-parse idea as the Python AUs'
// json_utils.parse_json: strip a stray code fence, then take the outermost
// object if the model wrapped it in any prose.
function parseResult(text) {
  if (!text || !text.trim()) return { error: "empty model response" };
  let s = text.trim();
  const fence = s.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) s = fence[1].trim();
  try {
    return JSON.parse(s);
  } catch {
    const start = s.indexOf("{");
    const end = s.lastIndexOf("}");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(s.slice(start, end + 1));
      } catch {
        /* fall through */
      }
    }
    return { error: "model did not return valid JSON", raw: s.slice(0, 500) };
  }
}

function buildMessage(inputs) {
  const evaluation = inputs.evaluation ?? {};
  const cv = inputs.cv;
  const lines = [
    "Design interview questions from this CV-fit evaluation.",
    "",
    "## Evaluation (JSON)",
    "```json",
    JSON.stringify(evaluation, null, 2),
    "```",
  ];
  if (cv) {
    lines.push("", "## Parsed CV (JSON)", "```json", JSON.stringify(cv, null, 2), "```");
  }
  lines.push(
    "",
    "Return 5-8 questions grouped by area, leading with the flagged gaps and lowest scores.",
    "Respond with only the JSON object described in your instructions.",
  );
  return lines.join("\n");
}

function computeSignals(outputs, latencySeconds) {
  const questions = outputs?.questions;
  return {
    valid_output_shape: outputs && typeof outputs === "object" && !("error" in outputs),
    has_questions: Array.isArray(questions) && questions.length > 0,
    latency_seconds: latencySeconds,
  };
}

serve({
  cardPath: process.env.CARD_PATH || path.join(APP_ROOT, "capability-card.yaml"),
  instructionsPath: path.join(APP_ROOT, "agent", "instructions.md"),
  buildMessage,
  parseResult,
  computeSignals,
}).catch((err) => {
  console.error("[aoa-eve] fatal:", err);
  process.exit(1);
});
