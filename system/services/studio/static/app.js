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
  records: [],
  lifecycle: emptyLifecycle(),
  wikiGraph: { nodes: [], edges: [] },
  selectedWikiNode: null,
  mode: "cv-fit",
  cvName: "",                  // last filename loaded into the CV box
  jdName: "",                  // last filename loaded into the JD box
  noteName: "",                // last filename loaded into the note box
  cvFile: null,
  jdFile: null,
  noteFile: null,
};

function emptyLifecycle() {
  return {
    status: "idle",
    workflow: "",
    intent: null,
    capabilityContext: [],
    source: "",
    proposal: null,
    validation: null,
    fallbackReason: "",
    tasks: [],
    taskById: new Map(),
    plan: [],
    result: null,
    error: "",
  };
}

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
  state.selectedWikiNode = null;
  $("detail-title").textContent = "Capability card";
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
    state.records = [];
    state.lifecycle = emptyLifecycle();
    $("trace-list").innerHTML = "";
  }
  if (state.currentTraceId && record.trace_id !== state.currentTraceId) {
    // Skip events from older flows that are still draining.
    return;
  }
  state.records.push(record);
  applyLifecycleEvent(record);
  renderLifecycle();

  const li = document.createElement("li");
  li.className = `step-${record.step}`;

  const head = document.createElement("div");
  head.className = "row-head";

  const left = document.createElement("span");
  left.innerHTML = `
    <span class="row-step">${escapeHtml(record.step)}</span>
    ${record.task ? ` <span class="row-cap">${escapeHtml(record.task)}</span>` : ""}
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
  const eventDetails = document.querySelector(".event-details");
  if (eventDetails && eventDetails.open) {
    li.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function applyLifecycleEvent(record) {
  const life = state.lifecycle;
  if (record.step === "start") {
    life.status = "running";
    life.workflow = record.workflow || "";
    life.intent = record.intent || null;
    return;
  }
  if (record.step === "capability-context") {
    life.capabilityContext = record.capabilities || [];
    return;
  }
  if (record.step === "breakdown") {
    life.source = record.source || life.source;
    life.tasks = (record.tasks || []).map((task) => ({
      id: task.id,
      purpose: task.purpose,
      inputMap: task.input_map || {},
      selectedCapability: task.selected_capability || "",
      status: "planned",
      latency: null,
      candidates: [],
      outputs: null,
      error: "",
    }));
    life.taskById = new Map(life.tasks.map((task) => [task.id, task]));
    return;
  }
  if (record.step === "plan-proposal") {
    life.source = record.source || life.source;
    life.proposal = record.proposal || null;
    life.validation = record.validation || null;
    life.fallbackReason = record.fallback_reason || "";
    return;
  }
  if (record.step === "discover") {
    const task = ensureTask(record.task);
    task.candidates = record.candidates || [];
    if (!task.selectedCapability && task.candidates.length) {
      task.selectedCapability = task.candidates[0].id || "";
    }
    return;
  }
  if (record.step === "select") {
    const task = ensureTask(record.task);
    task.selectedCapability = record.capability || task.selectedCapability;
    task.score = record.score;
    task.reasons = record.reasons || [];
    task.status = "selected";
    return;
  }
  if (record.step === "plan") {
    life.plan = record.plan || [];
    for (const item of life.plan) {
      const task = ensureTask(item.task);
      task.selectedCapability = item.capability || task.selectedCapability;
      task.purpose = item.purpose || task.purpose;
      task.inputMap = item.input_map || task.inputMap;
    }
    return;
  }
  if (record.step === "invoke") {
    const task = ensureTask(record.task || record.capability);
    task.status = "running";
    task.inputs = record.inputs || {};
    return;
  }
  if (record.step === "response") {
    const task = ensureTask(record.task || record.capability);
    const outputs = record.outputs || {};
    task.status = outputs.error ? "error" : "done";
    task.latency = record.latency_seconds;
    task.outputs = outputs;
    task.signals = record.signals || {};
    if (outputs.error) task.error = outputs.error;
    return;
  }
  if (record.step === "error") {
    const task = ensureTask(record.task || record.capability || "error");
    task.status = "error";
    task.error = record.error || "error";
    life.status = "error";
    life.error = record.error || "error";
    return;
  }
  if (record.step === "finish") {
    life.result = record.outputs || {};
    life.status = record.outputs && record.outputs.error ? "error" : "done";
    void loadWikiGraph();
  }
}

function ensureTask(id) {
  const safeId = id || "task";
  let task = state.lifecycle.taskById.get(safeId);
  if (task) return task;
  task = {
    id: safeId,
    purpose: "",
    inputMap: {},
    selectedCapability: "",
    status: "pending",
    latency: null,
    candidates: [],
    outputs: null,
    error: "",
  };
  state.lifecycle.tasks.push(task);
  state.lifecycle.taskById.set(safeId, task);
  return task;
}

function renderLifecycle() {
  const life = state.lifecycle;
  $("intent-title").textContent = lifecycleIntentTitle(life);
  const runState = $("run-state");
  runState.textContent = life.status;
  runState.className = `run-state ${life.status}`;
  renderLifecycleRail(life);
  renderPlanner(life);
  renderTasks(life);
  renderResult(life);
}

// ---------------------------------------------------------------------------
// Wiki graph
// ---------------------------------------------------------------------------

async function loadWikiGraph() {
  const stateLabel = $("wiki-graph-state");
  if (stateLabel) stateLabel.textContent = "loading";
  try {
    const resp = await fetch("/api/wiki/graph");
    const graph = await resp.json();
    state.wikiGraph = {
      nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
      edges: Array.isArray(graph.edges) ? graph.edges : [],
      error: graph.error || "",
    };
  } catch (e) {
    state.wikiGraph = { nodes: [], edges: [], error: String(e) };
  }
  renderWikiGraph();
}

function renderWikiGraph() {
  const root = $("wiki-graph");
  const stateLabel = $("wiki-graph-state");
  if (!root || !stateLabel) return;
  const graph = state.wikiGraph || { nodes: [], edges: [] };
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  stateLabel.textContent = graph.error ? "error" : `${nodes.length} nodes`;
  root.innerHTML = "";
  root.className = "wiki-graph";
  if (graph.error) {
    root.classList.add("muted-block");
    root.textContent = `Could not load wiki graph: ${graph.error}`;
    return;
  }
  if (!nodes.length) {
    root.classList.add("muted-block");
    root.textContent = "No wiki nodes yet.";
    return;
  }

  const layout = graphLayout(nodes);
  const svg = svgEl("svg", {
    viewBox: `0 0 ${layout.width} ${layout.height}`,
    role: "img",
    "aria-label": "Wiki graph",
  });
  const defs = svgEl("defs", {});
  const marker = svgEl("marker", {
    id: "arrow",
    viewBox: "0 0 10 10",
    refX: "9",
    refY: "5",
    markerWidth: "6",
    markerHeight: "6",
    orient: "auto-start-reverse",
  });
  marker.appendChild(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#b8b8b0" }));
  defs.appendChild(marker);
  svg.appendChild(defs);

  const edgeLayer = svgEl("g", { class: "graph-edges" });
  for (const edge of edges) {
    const source = layout.positions.get(edge.source);
    const target = layout.positions.get(edge.target);
    if (!source || !target) continue;
    edgeLayer.appendChild(svgEl("line", {
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      class: "graph-edge",
      "marker-end": "url(#arrow)",
    }));
    const label = truncate(edge.relation || "", 18);
    if (label) {
      const text = svgEl("text", {
        x: (source.x + target.x) / 2,
        y: (source.y + target.y) / 2 - 4,
        class: "graph-edge-label",
      });
      text.textContent = label;
      edgeLayer.appendChild(text);
    }
  }
  svg.appendChild(edgeLayer);

  const nodeLayer = svgEl("g", { class: "graph-nodes" });
  for (const node of nodes) {
    const pos = layout.positions.get(node.id);
    if (!pos) continue;
    const group = svgEl("g", {
      class: `graph-node ${node.type || "unknown"} ${node.id === state.selectedWikiNode ? "selected" : ""}`,
      transform: `translate(${pos.x} ${pos.y})`,
      tabindex: "0",
    });
    group.addEventListener("click", () => selectWikiNode(node.id));
    group.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") selectWikiNode(node.id);
    });
    appendNodeShape(group, node.type || "unknown");
    const text = svgEl("text", { y: 37, class: "graph-node-label" });
    text.textContent = truncate(node.label || node.id, 24);
    group.appendChild(text);
    nodeLayer.appendChild(group);
  }
  svg.appendChild(nodeLayer);
  root.appendChild(svg);
}

function graphLayout(nodes) {
  const typeOrder = ["document", "concept", "passage", "open_question"];
  const groups = new Map(typeOrder.map((type) => [type, []]));
  for (const node of nodes) {
    const type = typeOrder.includes(node.type) ? node.type : "concept";
    groups.get(type).push(node);
  }
  const maxGroupSize = Math.max(1, ...[...groups.values()].map((items) => items.length));
  const width = 920;
  const height = Math.max(330, maxGroupSize * 82 + 70);
  const positions = new Map();
  typeOrder.forEach((type, typeIndex) => {
    const items = groups.get(type);
    const x = 80 + typeIndex * ((width - 160) / (typeOrder.length - 1));
    items.forEach((node, itemIndex) => {
      const gap = items.length <= 1 ? 0 : (height - 130) / (items.length - 1);
      positions.set(node.id, {
        x,
        y: items.length <= 1 ? height / 2 : 65 + itemIndex * gap,
      });
    });
  });
  return { width, height, positions };
}

function appendNodeShape(group, type) {
  if (type === "document") {
    group.appendChild(svgEl("rect", { x: -42, y: -20, width: 84, height: 40, rx: 6 }));
  } else if (type === "passage") {
    group.appendChild(svgEl("rect", { x: -34, y: -16, width: 68, height: 32, rx: 2 }));
  } else if (type === "open_question") {
    group.appendChild(svgEl("polygon", { points: "0,-24 42,0 0,24 -42,0" }));
  } else {
    group.appendChild(svgEl("circle", { r: 21 }));
  }
}

function selectWikiNode(id) {
  state.selectedWikiNode = id;
  state.selectedCapability = null;
  renderRegistry();
  renderWikiGraph();
  const node = (state.wikiGraph.nodes || []).find((item) => item.id === id);
  if (!node) return;
  $("detail-title").textContent = "Wiki node";
  const edges = (state.wikiGraph.edges || []).filter(
    (edge) => edge.source === id || edge.target === id,
  );
  $("card-body").textContent = JSON.stringify({
    id: node.id,
    type: node.type,
    label: node.label,
    details: node.details || {},
    edges,
  }, null, 2);
}

function svgEl(name, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs || {})) {
    el.setAttribute(key, value);
  }
  return el;
}

function truncate(value, max) {
  const text = String(value || "");
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function lifecycleIntentTitle(life) {
  const kind = (life.intent && life.intent.kind) || life.workflow || state.mode;
  if (kind === "cv-fit") return "Evaluate a CV against a job description";
  if (kind === "knowledge-ingest") return "Ingest source material into the AOA wiki";
  if (kind === "knowledge-query") return "Answer a question from the AOA wiki";
  return "No run yet";
}

function renderLifecycleRail(life) {
  const stages = [
    ["intent", "Intent", Boolean(life.intent)],
    ["context", "Capabilities", life.capabilityContext.length > 0],
    ["proposal", "Plan proposal", Boolean(life.proposal || life.fallbackReason || life.source === "deterministic")],
    ["validation", "Validation", Boolean(life.validation || life.fallbackReason || life.source === "deterministic")],
    ["work", "Work", life.tasks.some((task) => ["running", "done", "error"].includes(task.status))],
    ["result", "Result", Boolean(life.result)],
  ];
  const rail = $("lifecycle-rail");
  rail.innerHTML = "";
  for (const [key, label, done] of stages) {
    const li = document.createElement("li");
    li.className = done ? "done" : "pending";
    if (key === "work" && life.tasks.some((task) => task.status === "running")) {
      li.className = "active";
    }
    if ((key === "result" || key === "validation" || key === "work") && life.status === "error") {
      li.classList.add("error");
    }
    li.innerHTML = `<span class="stage-dot"></span><span>${escapeHtml(label)}</span>`;
    rail.appendChild(li);
  }
}

function renderPlanner(life) {
  const source = life.source || "waiting";
  $("planner-source").textContent = source;
  const body = $("planner-body");
  body.innerHTML = "";
  if (!life.intent) {
    body.className = "planner-body muted-block";
    body.textContent = "No plan yet.";
    return;
  }
  body.className = "planner-body";

  const summary = document.createElement("div");
  summary.className = "planner-summary";
  const contextCount = life.capabilityContext.length;
  const validationText = life.validation && life.validation.valid
    ? "validated"
    : life.fallbackReason
      ? "fallback"
      : "pending";
  summary.innerHTML = `
    <span><strong>${contextCount}</strong> capabilities considered</span>
    <span><strong>${escapeHtml(source)}</strong> planner</span>
    <span class="${validationText === "fallback" ? "warn-text" : ""}">${escapeHtml(validationText)}</span>
  `;
  body.appendChild(summary);

  if (life.fallbackReason) {
    const fallback = document.createElement("p");
    fallback.className = "fallback-note";
    fallback.textContent = `Fallback: ${life.fallbackReason}`;
    body.appendChild(fallback);
  }

  if (life.proposal) {
    const details = document.createElement("details");
    details.className = "compact-details";
    details.innerHTML = `<summary>Planner JSON</summary><pre>${escapeHtml(JSON.stringify(life.proposal, null, 2))}</pre>`;
    body.appendChild(details);
  }
}

function renderTasks(life) {
  $("task-count").textContent = String(life.tasks.length);
  const list = $("task-list");
  list.innerHTML = "";
  for (const task of life.tasks) {
    const li = document.createElement("li");
    li.className = `task-card ${task.status || "pending"}`;
    const latency = task.latency == null ? "" : `<span>${task.latency.toFixed(2)}s</span>`;
    const capability = task.selectedCapability || "not selected";
    li.innerHTML = `
      <div class="task-main">
        <span class="task-status">${escapeHtml(task.status || "pending")}</span>
        <div>
          <h4>${escapeHtml(task.id)}</h4>
          <p>${escapeHtml(task.purpose || "")}</p>
        </div>
      </div>
      <div class="task-meta">
        <span>${escapeHtml(capability)}</span>
        ${latency}
      </div>
    `;
    const details = document.createElement("details");
    details.className = "compact-details";
    details.innerHTML = `<summary>Details</summary><pre>${escapeHtml(JSON.stringify(taskDetail(task), null, 2))}</pre>`;
    li.appendChild(details);
    list.appendChild(li);
  }
}

function taskDetail(task) {
  return {
    input_map: task.inputMap,
    candidates: task.candidates,
    reasons: task.reasons,
    signals: task.signals,
    error: task.error,
  };
}

function renderResult(life) {
  const resultState = $("result-state");
  const body = $("result-body");
  body.innerHTML = "";
  if (!life.result) {
    resultState.textContent = life.status === "running" ? "waiting" : life.status;
    body.className = "result-body muted-block";
    body.textContent = "No result yet.";
    return;
  }
  const markdown = life.result.report_markdown || life.result.answer_markdown || life.result.ingest_markdown || "";
  resultState.textContent = life.result.error ? "error" : "complete";
  body.className = "result-body";
  if (markdown) {
    body.appendChild(renderMarkdown(markdown));
  } else {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(life.result, null, 2);
    body.appendChild(pre);
  }
}

function pickPayload(record) {
  if (record.step === "capability-context") {
    return { capabilities: record.capabilities };
  }
  if (record.step === "breakdown") return { tasks: record.tasks };
  if (record.step === "plan-proposal") {
    return {
      source: record.source,
      proposal: record.proposal,
      validation: record.validation,
      fallback_reason: record.fallback_reason,
    };
  }
  if (record.step === "discover") {
    return { task: record.task, query: record.query, candidates: record.candidates };
  }
  if (record.step === "select") {
    return {
      task: record.task,
      capability: record.capability,
      score: record.score,
      reasons: record.reasons,
      card: record.card,
    };
  }
  if (record.step === "plan") return { plan: record.plan };
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
    return outputs.report_markdown || outputs.answer_markdown || outputs.ingest_markdown || "";
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

  if (state.mode === "knowledge-ingest") {
    const note = $("intent-note").value.trim();
    if (!note && !state.noteFile) {
      status.textContent = "need source material to ingest";
      return null;
    }
    return {
      kind: "knowledge-ingest",
      note_text: note,
      note_name: state.noteName || "source-note.txt",
      note_file: state.noteFile,
    };
  }

  const question = $("intent-question").value.trim();
  if (!question) {
    status.textContent = "need a question";
    return null;
  }
  return {
    kind: "knowledge-query",
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
  const labels = {
    "cv-fit": "Run cv-fit",
    "knowledge-ingest": "Run ingest",
    "knowledge-query": "Run query",
  };
  $("intent-submit").textContent = labels[mode] || "Run";
  $("intent-status").textContent = "";
  if (!state.lifecycle.intent) renderLifecycle();
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
  renderLifecycle();
  loadInitialRegistry();
  loadWikiGraph();
  connectEvents();
});
