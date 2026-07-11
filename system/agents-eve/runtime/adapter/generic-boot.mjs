// Zero-code adoption entry point for an EVE agent whose native interface is
// JSON-in/JSON-out. The generic aoa-eve bridge derives the turn message,
// tolerant JSON parsing, and basic output-presence signals from the capability
// card. Agent-specific adapters remain possible, but are not the default.
import path from "node:path";
import { serve } from "./serve.mjs";

const appRoot = process.env.EVE_APP_ROOT || "/app";

serve({
  cardPath: process.env.CARD_PATH || path.join(appRoot, "capability-card.yaml"),
  instructionsPath: path.join(appRoot, "agent", "instructions.md"),
}).catch((error) => {
  console.error("[aoa-eve] fatal:", error);
  process.exit(1);
});
