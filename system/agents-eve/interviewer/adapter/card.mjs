// Capability-card loading and runtime stamping for an EVE agent.
//
// EVE has no notion of a capability card, a governed agent identity, or a
// registry. This module is the AOA governance layer EVE lacks: it reads the
// authored capability-card.yaml sitting next to the agent, and stamps it with
// the same runtime fields the Python scaffold stamps in
// system/agents/_base/base.py (agent_id, identity, endpoint, a2a_endpoint,
// provenance.model, provenance.skills_hash) so the AOA registry, planner, studio,
// and trace treat this EVE agent exactly like a Python AU.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { parse as parseYaml } from "yaml";

export function sha256(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

const env = (name, fallback = "") => process.env[name] ?? fallback;

function agentName() {
  return env("AGENT_NAME", "agent");
}

function agentId() {
  return env("AGENT_ID", `urn:aoa:agent:${agentName()}`);
}

function agentHost() {
  return env("AGENT_HOST", env("AGENT_NAME", "agent"));
}

function agentPort() {
  return env("AGENT_PORT", "8888");
}

function identity() {
  return {
    agent_id: agentId(),
    agent_name: agentName(),
    runtime: env("AGENT_RUNTIME", "docker-compose-eve"),
    principal: env("AGENT_PRINCIPAL", agentId()),
  };
}

function endpoint(kind) {
  const base = `http://${agentHost()}:${agentPort()}`;
  return {
    invoke: `${base}/invoke`,
    a2a: `${base}/a2a`,
    card: `${base}/.well-known/agent-card.json`,
    kind,
  };
}

// Load the capability card and stamp it, returning { id, card, instructionsPath }.
export function loadStampedCard(cardPath, instructionsPath) {
  const card = parseYaml(readFileSync(cardPath, "utf8")) || {};
  if (!card.id) throw new Error(`${cardPath} is missing 'id'`);

  const instructionsText = readFileSync(instructionsPath, "utf8");
  card.provenance = card.provenance || {};
  card.provenance.skills_hash = sha256(instructionsText);
  if (card.provenance.model == null || card.provenance.model === "${MODEL}") {
    card.provenance.model = env("MODEL", "${MODEL}");
  }

  const id = identity();
  card.agent_id = id.agent_id;
  card.identity = { ...(card.identity || {}), ...id };

  const ep = endpoint(card.kind);
  card.endpoint = ep.invoke;
  if (card.kind === "au") {
    card.agent_card_url = ep.card;
    card.a2a_endpoint = ep.a2a;
  }
  return { id: card.id, card };
}

// Recompute only the behaviour hash after an instructions.md edit (hot reload).
export function rehash(card, instructionsPath) {
  card.provenance = card.provenance || {};
  card.provenance.skills_hash = sha256(readFileSync(instructionsPath, "utf8"));
  return card.provenance.skills_hash;
}

// The public A2A Agent Card, mirroring _build_agent_card in base.py: the full
// AOA capability contracts ride along in a data-only A2A extension, and the
// stable AOA agent identity in a second extension.
export function buildAgentCard(cards) {
  const name = agentName();
  const id = identity();
  const ep = endpoint("au");
  const describe = (c) => (c.purpose ? String(c.purpose).split(/\s+/).join(" ").trim() : `Capability ${c.id}`);
  const description =
    cards.length === 1 ? describe(cards[0]) : `${name} agent serving ${cards.length} AOA capabilities.`;
  return {
    protocolVersion: "0.3.0",
    name,
    description,
    url: ep.a2a,
    preferredTransport: "JSONRPC",
    version: "0.1.0",
    capabilities: {
      streaming: false,
      pushNotifications: false,
      stateTransitionHistory: false,
      extensions: [
        {
          uri: "urn:aoa:extensions:capability-card:v1",
          description: "AOA capability-card contracts exposed by this A2A agent.",
          required: false,
          params: { agent_identity: id, capabilities: cards },
        },
        {
          uri: "urn:aoa:extensions:agent-identity:v1",
          description: "Stable AOA Agent ID used by registry, policy, trace, and audit.",
          required: false,
          params: id,
        },
      ],
    },
    defaultInputModes: ["application/json", "text/plain"],
    defaultOutputModes: ["application/json", "text/markdown", "text/plain"],
    skills: cards.map((c) => ({
      id: c.id,
      name: c.id,
      description: describe(c),
      tags: ["aoa", "agentic-unit", "eve"],
      inputModes: ["application/json"],
      outputModes: ["application/json", "text/markdown"],
    })),
  };
}
