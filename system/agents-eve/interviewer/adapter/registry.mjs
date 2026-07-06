// Minimal AOA registry client for an EVE agent — the TypeScript/JS counterpart
// of system/agents/_base/registry_client.py. Same four endpoints:
//   POST /register, POST /update, GET /find?id=, GET /list
// with boot-time retries because the agent starts alongside the registry.
const BASE = (process.env.REGISTRY_URL || "http://registry:7100").replace(/\/$/, "");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function waitUntilReady(timeoutSeconds = 30, intervalMs = 500) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  let lastErr;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${BASE}/healthz`, { signal: AbortSignal.timeout(2000) });
      if (r.ok) return;
    } catch (err) {
      lastErr = err;
    }
    await sleep(intervalMs);
  }
  throw new Error(`registry at ${BASE} not ready after ${timeoutSeconds}s (last error: ${lastErr})`);
}

export async function register(card) {
  const r = await fetch(`${BASE}/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(card),
  });
  if (!r.ok) throw new Error(`register ${card.id} failed: ${r.status} ${await r.text()}`);
}

export async function update(card) {
  const r = await fetch(`${BASE}/update`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(card),
  });
  if (!r.ok) throw new Error(`update ${card.id} failed: ${r.status} ${await r.text()}`);
}
