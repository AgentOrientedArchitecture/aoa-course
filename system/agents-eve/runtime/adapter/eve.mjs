// Runs the EVE runtime as a child process and drives one turn to completion.
//
// The container boots `eve dev --no-ui` on a loopback port (dev mode so that
// editing agent/instructions.md on the host hot-reloads behaviour for the next
// turn). Each AOA invocation is one durable EVE session; the adapter reads the
// final assistant message and parses the JSON the instructions ask for
// (prompt-then-parse), the same shape the Python AUs use. This keeps the agent
// tool-free and portable across every provider the course supports, including
// OpenAI-compatible endpoints that do not accept the `tool` message role.
import { spawn } from "node:child_process";
import path from "node:path";
import { Client } from "eve/client";

const APP_ROOT = process.env.EVE_APP_ROOT || "/app";
const EVE_BIN = path.join(APP_ROOT, "node_modules", ".bin", "eve");

let client;

export function startEve(port) {
  const child = spawn(
    EVE_BIN,
    ["dev", "--no-ui", "--host", "127.0.0.1", "--port", String(port)],
    { cwd: APP_ROOT, stdio: "inherit", env: process.env },
  );
  child.on("exit", (code, signal) => {
    console.error(`[eve] runtime exited (code=${code} signal=${signal}); shutting down`);
    process.exit(code ?? 1);
  });
  return child;
}

export async function waitEveReady(port, timeoutSeconds = 120, intervalMs = 1000) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  let lastErr;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/eve/v1/info`, {
        signal: AbortSignal.timeout(3000),
      });
      if (r.ok) return;
    } catch (err) {
      lastErr = err;
    }
    await new Promise((res) => setTimeout(res, intervalMs));
  }
  throw new Error(`eve runtime on :${port} not ready after ${timeoutSeconds}s (last error: ${lastErr})`);
}

// Send one message and return the final assistant text. Consumes the NDJSON
// event stream and keeps the last completed assistant message; falls back to the
// cumulative streamed text if no completed block arrives. Throws on turn failure.
export async function runTurn(port, message, timeoutMs = 120000) {
  if (!client) client = new Client({ host: `http://127.0.0.1:${port}` });
  const session = client.session();
  const response = await session.send({ message, signal: AbortSignal.timeout(timeoutMs) });

  let finalText = "";
  let streamedText = "";
  for await (const ev of response) {
    if (ev.type === "message.appended") {
      streamedText = ev.data?.messageSoFar ?? streamedText;
    } else if (ev.type === "message.completed") {
      const text = ev.data?.message;
      if (typeof text === "string" && text.trim()) finalText = text;
    } else if (ev.type === "turn.failed" || ev.type === "step.failed") {
      const d = ev.data?.details || ev.data || {};
      throw new Error(`EVE ${ev.type}: ${d.message || d.code || JSON.stringify(d).slice(0, 200)}`);
    }
  }
  return finalText || streamedText;
}
