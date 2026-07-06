// aoa-eve: the reusable bridge that makes an EVE agent a first-class AOA
// Agentic Unit. It gives the EVE runtime everything EVE itself does not provide:
//   * a capability card, stamped and registered with the AOA registry
//   * the AOA HTTP + A2A surface (/a2a, /.well-known/agent-card.json, /invoke,
//     /cards/<id>, /healthz) that the planner and studio already speak
//   * trace events on the AOA boundary so the studio's responsibility walk shows
//     this agent like any Python AU
//   * hot reload: editing instructions.md re-stamps skills_hash in the registry
//
// It mirrors, in JS, the jobs system/agents/_base/base.py does for Python agents.
// The agent-specific bits (how to phrase the turn, the output schema, the
// signals) are injected by boot.mjs, so this file stays generic.
import http from "node:http";
import { loadStampedCard, rehash, buildAgentCard } from "./card.mjs";
import { waitUntilReady, register, update } from "./registry.mjs";
import { startEve, waitEveReady, runTurn } from "./eve.mjs";

const PLANNER_URL = (process.env.PLANNER_URL || "").replace(/\/$/, "");

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, { "content-type": "application/json" });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

function shape(value) {
  if (Array.isArray(value)) return { type: "array", count: value.length };
  if (value && typeof value === "object") return { type: "object", keys: Object.keys(value).slice(0, 12) };
  if (typeof value === "string") return { type: "string", chars: value.length };
  if (value == null) return { type: "null" };
  return { type: typeof value };
}

async function emitTrace(record) {
  if (!PLANNER_URL || !record.trace_id) return;
  try {
    await fetch(`${PLANNER_URL}/trace-events`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(record),
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // trace is best-effort; never fail an invocation because the planner is busy
  }
}

// Mirror of base.py:_extract_a2a_invocation.
function extractA2A(params) {
  const metadata = params.metadata || {};
  const message = params.message || {};
  const msgMeta = message.metadata || {};
  let capabilityId =
    metadata.aoa_capability || msgMeta.aoa_capability || metadata.capability || msgMeta.capability || "";
  let traceId = metadata.trace_id || msgMeta.trace_id || params.taskId || "";
  let inputs = {};
  for (const part of message.parts || []) {
    if (part.kind !== "data") continue;
    const data = part.data;
    if (!data || typeof data !== "object") continue;
    if (!capabilityId) capabilityId = String(data.aoa_capability || data.capability || "");
    if (!traceId) traceId = String(data.trace_id || "");
    const maybe = data.inputs != null ? data.inputs : data;
    if (maybe && typeof maybe === "object") {
      inputs = maybe;
      break;
    }
  }
  return { capabilityId, traceId, inputs };
}

function markdownOf(outputs) {
  for (const key of ["report_markdown", "answer_markdown", "ingest_markdown", "markdown"]) {
    const v = outputs?.[key];
    if (typeof v === "string" && v.trim()) return v;
  }
  return null;
}

function jsonRpcError(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

/**
 * Start the agent.
 * @param {object} cfg
 * @param {string} cfg.cardPath          path to capability-card.yaml
 * @param {string} cfg.instructionsPath  path to agent/instructions.md (for skills_hash + watch)
 * @param {(inputs:object)=>string} cfg.buildMessage   turn message from AOA inputs
 * @param {(text:string)=>object} cfg.parseResult      parse the assistant text into AOA outputs
 * @param {(outputs:object, latencySeconds:number)=>object} cfg.computeSignals
 */
export async function serve(cfg) {
  const evePort = Number(process.env.EVE_PORT || 3000);
  const agentPort = Number(process.env.AGENT_PORT || 8888);
  const agentName = process.env.AGENT_NAME || "eve-agent";
  const agentId = process.env.AGENT_ID || `urn:aoa:agent:${agentName}`;

  const { id, card } = loadStampedCard(cfg.cardPath, cfg.instructionsPath);
  const agentCard = buildAgentCard([card]);

  // 1. Bring up the EVE runtime and the registry, then register.
  startEve(evePort);
  await Promise.all([waitEveReady(evePort), waitUntilReady()]);
  await register(card);
  console.log(`[aoa-eve] registered ${id} (skills_hash ${card.provenance.skills_hash.slice(0, 8)})`);

  // 2. Hot reload: re-stamp + re-register when instructions.md changes. We poll
  // rather than use fs.watch because inotify events do not reliably cross a
  // bind mount on Docker Desktop (macOS/Windows), and the studio's live
  // skills_hash is the whole point of the exercise.
  const HOT_RELOAD_INTERVAL_MS = Number(process.env.HOT_RELOAD_INTERVAL_MS || 1500);
  setInterval(async () => {
    const before = card.provenance.skills_hash;
    let after;
    try {
      after = rehash(card, cfg.instructionsPath);
    } catch {
      return; // file briefly unreadable mid-write; try again next tick
    }
    if (after === before) return;
    try {
      await update(card);
      console.log(`[aoa-eve] reloaded ${id} (skills_hash ${after.slice(0, 8)})`);
    } catch (err) {
      console.error(`[aoa-eve] failed to update ${id}: ${err}`);
    }
  }, HOT_RELOAD_INTERVAL_MS).unref();

  // 3. Invoke: drive one EVE turn and return the AOA result envelope.
  async function invoke(capabilityId, traceId, inputs) {
    if (capabilityId !== id) {
      return { outputs: { error: `unknown capability: ${capabilityId}` }, signals: { exception: true } };
    }
    await emitTrace({
      trace_id: traceId,
      step: "au-start",
      capability: id,
      agent: agentName,
      agent_id: agentId,
      boundary: "au",
      model: card.provenance.model,
      skills_hash: card.provenance.skills_hash,
      inputs_shape: shape(inputs),
    });
    const t0 = Date.now();
    try {
      const message = cfg.buildMessage(inputs);
      const text = await runTurn(evePort, message);
      const latency = (Date.now() - t0) / 1000;
      const outputs = cfg.parseResult(text);
      const signals = cfg.computeSignals(outputs, latency);
      await emitTrace({
        trace_id: traceId,
        step: "au-finish",
        capability: id,
        agent: agentName,
        agent_id: agentId,
        boundary: "au",
        outputs_shape: shape(outputs),
        signals,
        latency_seconds: latency,
      });
      return { outputs, signals };
    } catch (err) {
      const latency = (Date.now() - t0) / 1000;
      await emitTrace({
        trace_id: traceId,
        step: "au-error",
        capability: id,
        agent: agentName,
        agent_id: agentId,
        boundary: "au",
        error: String(err),
        latency_seconds: latency,
      });
      return {
        outputs: { error: String(err) },
        signals: { exception: true, exception_type: err?.name || "Error", error: String(err) },
      };
    }
  }

  // 4. The AOA HTTP + A2A surface — identical routes to base.py:build_app.
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const p = url.pathname;
    try {
      if (req.method === "GET" && p === "/healthz") return json(res, 200, { ok: true, capabilities: [id] });
      if (req.method === "GET" && (p === "/.well-known/agent-card.json" || p === "/a2a/.well-known/agent-card.json"))
        return json(res, 200, agentCard);
      if (req.method === "GET" && p.startsWith("/cards/")) {
        const wanted = decodeURIComponent(p.slice("/cards/".length));
        if (wanted !== id) return json(res, 404, { detail: `unknown capability: ${wanted}` });
        return json(res, 200, card);
      }
      if (req.method === "POST" && p === "/invoke") {
        const capabilityId = url.searchParams.get("capability");
        if (!capabilityId) return json(res, 400, { detail: "missing ?capability=<id>" });
        const body = await readBody(req);
        const env = await invoke(capabilityId, body.trace_id || "", body.inputs || {});
        return json(res, 200, { trace_id: body.trace_id || "", ...env });
      }
      if (req.method === "POST" && p === "/a2a") {
        const body = await readBody(req);
        const requestId = body.id;
        if (body.jsonrpc !== "2.0") return json(res, 200, jsonRpcError(requestId, -32600, "expected JSON-RPC 2.0"));
        if (body.method !== "message/send") return json(res, 200, jsonRpcError(requestId, -32601, "method not found"));
        const params = body.params || {};
        const { capabilityId, traceId, inputs } = extractA2A(params);
        if (!capabilityId) return json(res, 200, jsonRpcError(requestId, -32602, "missing aoa_capability metadata"));
        const trace = traceId || Math.random().toString(16).slice(2, 14);
        const env = await invoke(capabilityId, trace, inputs);
        const parts = [];
        const md = markdownOf(env.outputs);
        if (md) parts.push({ kind: "text", text: md });
        parts.push({
          kind: "data",
          data: { trace_id: trace, aoa_capability: capabilityId, outputs: env.outputs, signals: env.signals },
        });
        return json(res, 200, {
          jsonrpc: "2.0",
          id: requestId,
          result: {
            kind: "message",
            messageId: `${trace}-${capabilityId}-response`,
            role: "agent",
            parts,
            metadata: { trace_id: trace, aoa_capability: capabilityId },
          },
        });
      }
      return json(res, 404, { detail: "not found" });
    } catch (err) {
      return json(res, 500, { detail: String(err) });
    }
  });

  server.listen(agentPort, "0.0.0.0", () => {
    console.log(`[aoa-eve] ${agentName} serving AOA surface on :${agentPort} (EVE runtime on :${evePort})`);
  });
}
