// Studio frontend.
//
// Three panes (registry, trace, capability card) plus an intent form and a
// file drop. Subscribes to /events for a merged registry + planner SSE feed
// and re-renders incrementally.

const $ = (id) => document.getElementById(id);

const state = {
  capabilities: new Map(),     // id -> card
  selectedCapability: null,
  currentTraceId: null,
};

// ---------------------------------------------------------------------------
// Registry pane
// ---------------------------------------------------------------------------

function renderRegistry() {
  const list = $("registry-list");
  list.innerHTML = "";
  const entries = [...state.capabilities.values()].sort((a, b) =>
    a.id.localeCompare(b.id),
  );
  for (const card of entries) {
    const li = document.createElement("li");
    li.dataset.id = card.id;
    if (card.id === state.selectedCapability) li.classList.add("selected");
    const kind = (card.kind || "au").toLowerCase();
    const hash = (card.provenance && card.provenance.skills_hash) || "";
    li.innerHTML = `
      <span class="cap-kind ${kind}">${kind}</span>
      <span class="cap-id">${escapeHtml(card.id)}</span>
      <span class="cap-meta">v${escapeHtml(card.version || "?")} · ${hash ? hash.slice(0, 8) : "—"}</span>
    `;
    li.addEventListener("click", () => selectCapability(card.id));
    list.appendChild(li);
  }
}

async function selectCapability(id) {
  state.selectedCapability = id;
  renderRegistry();
  const resp = await fetch(`/api/capabilities/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    $("card-body").textContent = `Could not load card for ${id}`;
    return;
  }
  const card = await resp.json();
  $("card-body").textContent = JSON.stringify(card, null, 2);
}

function applyRegistryEvent(payload) {
  const ev = payload.event;
  if (ev === "snapshot") {
    state.capabilities.clear();
    for (const card of payload.cards || []) state.capabilities.set(card.id, card);
  } else if (ev === "registered" || ev === "updated") {
    if (payload.card && payload.card.id) {
      state.capabilities.set(payload.card.id, payload.card);
    }
  } else if (ev === "deregistered") {
    if (payload.card && payload.card.id) state.capabilities.delete(payload.card.id);
  }
  renderRegistry();
  // If the open card changed, refresh it.
  if (state.selectedCapability && payload.card && payload.card.id === state.selectedCapability) {
    selectCapability(state.selectedCapability);
  }
}

// ---------------------------------------------------------------------------
// Trace pane
// ---------------------------------------------------------------------------

function appendTraceRow(record) {
  // Reset the trace pane when a new flow starts.
  if (record.step === "start") {
    state.currentTraceId = record.trace_id;
    $("trace-list").innerHTML = "";
  }
  if (state.currentTraceId && record.trace_id !== state.currentTraceId) {
    // Skip events from older flows that are still draining.
    return;
  }

  const li = document.createElement("li");
  li.className = `step-${record.step}`;

  const head = document.createElement("div");
  head.className = "row-head";

  const left = document.createElement("span");
  left.innerHTML = `
    <span class="row-step">${escapeHtml(record.step)}</span>
    ${record.capability ? ` <span class="row-cap">${escapeHtml(record.capability)}</span>` : ""}
  `;

  const right = document.createElement("span");
  right.className = "row-meta";
  if (record.latency_seconds != null) {
    right.textContent = `${record.latency_seconds.toFixed(2)}s`;
  } else if (record.workflow) {
    right.textContent = record.workflow;
  }

  head.appendChild(left);
  head.appendChild(right);

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.appendChild(head);
  details.appendChild(summary);

  const body = pickPayload(record);
  if (body !== null) {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(body, null, 2);
    details.appendChild(pre);
  }

  li.appendChild(details);
  $("trace-list").appendChild(li);
  li.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function pickPayload(record) {
  if (record.step === "lookup") return record.card;
  if (record.step === "invoke") return record.inputs;
  if (record.step === "response") {
    return { outputs: record.outputs, signals: record.signals };
  }
  if (record.step === "error") return { error: record.error };
  if (record.step === "finish") return record.outputs;
  if (record.step === "start") return record.intent;
  return null;
}

// ---------------------------------------------------------------------------
// SSE
// ---------------------------------------------------------------------------

function connectEvents() {
  const es = new EventSource("/events");
  es.onopen = () => setStatus(true);
  es.onerror = () => setStatus(false);
  es.onmessage = (e) => {
    let msg;
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }
    if (msg.source === "registry") applyRegistryEvent(msg.payload);
    else if (msg.source === "planner") appendTraceRow(msg.payload);
  };
}

function setStatus(connected) {
  const el = $("status");
  el.textContent = connected ? "connected" : "disconnected";
  el.classList.toggle("connected", connected);
  el.classList.toggle("disconnected", !connected);
}

// ---------------------------------------------------------------------------
// Intent submission
// ---------------------------------------------------------------------------

async function submitIntent() {
  const cv = $("intent-cv").value.trim();
  const jd = $("intent-jd").value.trim();
  const status = $("intent-status");
  const btn = $("intent-submit");
  if (!cv || !jd) {
    status.textContent = "need both a CV and a job description";
    return;
  }
  btn.disabled = true;
  status.textContent = "running…";
  try {
    const resp = await fetch("/api/intent", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kind: "cv-fit", inputs: { cv_text: cv, jd_text: jd } }),
    });
    const body = await resp.json();
    if (!resp.ok) {
      status.textContent = `error: ${body.error || resp.statusText}`;
    } else {
      status.textContent = `done · trace ${body.trace_id}`;
    }
  } catch (e) {
    status.textContent = `error: ${e}`;
  } finally {
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// File drop
// ---------------------------------------------------------------------------

function setupFileDrop() {
  const overlay = $("file-drop-overlay");
  let depth = 0;

  document.addEventListener("dragenter", (e) => {
    e.preventDefault();
    depth += 1;
    overlay.classList.add("visible");
  });
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("dragleave", () => {
    depth = Math.max(0, depth - 1);
    if (depth === 0) overlay.classList.remove("visible");
  });
  document.addEventListener("drop", async (e) => {
    e.preventDefault();
    depth = 0;
    overlay.classList.remove("visible");
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || !files.length) return;
    const text = await files[0].text();
    $("intent-cv").value = text;
    $("intent-status").textContent = `loaded ${files[0].name} into CV box`;
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function loadInitialRegistry() {
  try {
    const r = await fetch("/api/capabilities");
    const data = await r.json();
    for (const card of data.capabilities || []) state.capabilities.set(card.id, card);
    renderRegistry();
  } catch {
    // SSE snapshot will fill it in.
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

window.addEventListener("DOMContentLoaded", () => {
  $("intent-submit").addEventListener("click", submitIntent);
  setupFileDrop();
  loadInitialRegistry();
  connectEvents();
});
