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
  mode: "cv-fit",
  cvName: "",                  // last filename loaded into the CV box
  jdName: "",                  // last filename loaded into the JD box
  noteName: "",                // last filename loaded into the note box
  cvFile: null,
  jdFile: null,
  noteFile: null,
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
    const markdown = pickMarkdown(record);
    if (markdown) details.appendChild(renderMarkdown(markdown));
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

function pickMarkdown(record) {
  const outputs = record.outputs || {};
  if (record.step === "response" || record.step === "finish") {
    return outputs.report_markdown || outputs.answer_markdown || "";
  }
  return "";
}

function renderMarkdown(markdown) {
  const root = document.createElement("div");
  root.className = "rendered-markdown";
  let list = null;

  for (const rawLine of markdown.split("\n")) {
    const line = rawLine.trim();
    if (!line) {
      list = null;
      continue;
    }
    if (line.startsWith("## ")) {
      list = null;
      const h = document.createElement("h4");
      h.textContent = line.slice(3);
      root.appendChild(h);
      continue;
    }
    if (line.startsWith("# ")) {
      list = null;
      const h = document.createElement("h3");
      h.textContent = line.slice(2);
      root.appendChild(h);
      continue;
    }
    if (line.startsWith("- ")) {
      if (!list) {
        list = document.createElement("ul");
        root.appendChild(list);
      }
      const li = document.createElement("li");
      li.innerHTML = renderInlineMarkdown(line.slice(2));
      list.appendChild(li);
      continue;
    }
    list = null;
    const p = document.createElement("p");
    p.innerHTML = renderInlineMarkdown(line);
    root.appendChild(p);
  }
  return root;
}

function renderInlineMarkdown(text) {
  return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
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
  const status = $("intent-status");
  const btn = $("intent-submit");
  const payload = buildIntentPayload(status);
  if (!payload) return;
  const formBody = intentFormData(payload);

  btn.disabled = true;
  status.textContent = "running…";
  try {
    const resp = await fetch("/api/intent", {
      method: "POST",
      body: formBody,
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

function buildIntentPayload(status) {
  if (state.mode === "cv-fit") {
    const cv = $("intent-cv").value.trim();
    const jd = $("intent-jd").value.trim();
    if ((!cv && !state.cvFile) || (!jd && !state.jdFile)) {
      status.textContent = "need both a CV and a job description";
      return null;
    }
    return {
      kind: "cv-fit",
      cv_text: cv,
      jd_text: jd,
      cv_name: state.cvName || "cv.txt",
      jd_name: state.jdName || "jd.txt",
      cv_file: state.cvFile,
      jd_file: state.jdFile,
    };
  }

  const note = $("intent-note").value.trim();
  const question = $("intent-question").value.trim();
  if ((!note && !state.noteFile) || !question) {
    status.textContent = "need both a source note and a question";
    return null;
  }
  return {
    kind: "knowledge-query",
    note_text: note,
    note_name: state.noteName || "source-note.txt",
    note_file: state.noteFile,
    question,
  };
}

function intentFormData(payload) {
  const form = new FormData();
  form.append("kind", payload.kind);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "kind" || value == null) continue;
    if (value instanceof File) form.append(key, value, value.name);
    else form.append(key, value);
  }
  return form;
}

// ---------------------------------------------------------------------------
// File drop (per-textarea: drop on the CV box or the JD box)
// ---------------------------------------------------------------------------

function setupFileDrop() {
  for (const id of ["intent-cv", "intent-jd", "intent-note"]) {
    const ta = $(id);
    if (!ta) continue;

    ta.addEventListener("dragover", (e) => {
      e.preventDefault();
      ta.classList.add("dragover");
    });
    ta.addEventListener("dragleave", () => ta.classList.remove("dragover"));
    ta.addEventListener("input", () => clearDroppedFile(id));
    ta.addEventListener("drop", async (e) => {
      e.preventDefault();
      ta.classList.remove("dragover");
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      const f = files[0];
      ta.value = "";
      ta.placeholder = `Selected file: ${f.name}`;
      const labelId = ta.dataset.nameTarget;
      if (labelId && $(labelId)) $(labelId).textContent = f.name;
      if (id === "intent-cv") {
        state.cvName = f.name;
        state.cvFile = f;
      } else if (id === "intent-jd") {
        state.jdName = f.name;
        state.jdFile = f;
      } else {
        state.noteName = f.name;
        state.noteFile = f;
      }
    });
  }
}

function clearDroppedFile(id) {
  const ta = $(id);
  if (id === "intent-cv") {
    state.cvFile = null;
    state.cvName = "";
  } else if (id === "intent-jd") {
    state.jdFile = null;
    state.jdName = "";
  } else {
    state.noteFile = null;
    state.noteName = "";
  }
  const labelId = ta && ta.dataset.nameTarget;
  if (labelId && $(labelId)) $(labelId).textContent = "paste below or drop a file";
}

function setupModeTabs() {
  for (const btn of document.querySelectorAll("[data-mode]")) {
    btn.addEventListener("click", () => setMode(btn.dataset.mode));
  }
}

function setMode(mode) {
  state.mode = mode;
  for (const btn of document.querySelectorAll("[data-mode]")) {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  }
  for (const panel of document.querySelectorAll("[data-mode-panel]")) {
    panel.classList.toggle("hidden", panel.dataset.modePanel !== mode);
  }
  $("intent-submit").textContent = mode === "cv-fit" ? "Run cv-fit" : "Run knowledge-query";
  $("intent-status").textContent = "";
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
  setupModeTabs();
  $("intent-submit").addEventListener("click", submitIntent);
  setupFileDrop();
  loadInitialRegistry();
  connectEvents();
});
