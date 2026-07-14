// Studio frontend.
//
// Three panes (registry, trace, capability card) plus an intent form and a
// file drop. Subscribes to /events for a merged registry + planner SSE feed
// and re-renders incrementally.

const $ = (id) => document.getElementById(id);

const WORKFLOWS = [
  "agent-card-check",
  "cv-fit",
  "flow-audit",
  "cv-fit-interview",
  "knowledge-ingest",
  "wiki-graph",
  "knowledge-query",
];

// cv-fit-interview reuses the CV + JD form panel of cv-fit; it only differs in the
// workflow the planner runs (it adds the EVE interviewer as a final step).
function panelForMode(mode) {
  return mode === "cv-fit-interview" ? "cv-fit" : mode;
}
const studioConfig = window.STUDIO_CONFIG || {};
const configuredWorkflows = Array.isArray(studioConfig.workflows)
  ? studioConfig.workflows.filter((mode) => WORKFLOWS.includes(mode))
  : WORKFLOWS;
const enabledWorkflows = new Set(configuredWorkflows.length ? configuredWorkflows : ["cv-fit"]);

// Result governance (eligibility, held drafts, human review) is the Session 4
// story. Show those surfaces when this profile runs the governance workflows,
// or when a run's release policy actually requires review.
const governanceUiDefault = ["agent-card-check", "flow-audit"].some((w) => enabledWorkflows.has(w));

function governanceStagesActive(life) {
  return governanceUiDefault || life.releasePolicy === "human-review-before-release";
}

const state = {
  capabilities: new Map(),     // id -> card
  governanceEvents: [],
  selectedCapability: null,
  currentTraceId: null,
  records: [],
  lifecycle: emptyLifecycle(),
  wikiGraph: { nodes: [], edges: [] },
  selectedWikiNode: null,
  mode: configuredWorkflows[0] || "cv-fit",
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
    fallbackDetail: "",
    tasks: [],
    taskById: new Map(),
    plan: [],
    releasePolicy: "",
    governance: null,
    planDigest: "",
    draft: null,
    resultDigest: "",
    review: null,
    release: null,
    quarantine: null,
    result: null,
    error: "",
  };
}

function plannerFallbackText(reason) {
  const text = String(reason || "");
  if (!text) return "";
  if (/task \d+ must be an object/.test(text) || text.includes("plan.tasks")) {
    return "Planner model returned an invalid plan; using the deterministic workflow.";
  }
  if (text.includes("Client error") || text.includes("HTTPStatusError")) {
    return "Planner model request failed; using the deterministic workflow.";
  }
  if (text.includes("Name or service not known")) {
    return "Planner model request failed; using the deterministic workflow.";
  }
  return text;
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
    const agentId = card.agent_id || (card.identity && card.identity.agent_id) || "unbound";
    const lifecycle = card.lifecycle || {};
    li.innerHTML = `
      <span class="cap-kind ${kind}">${kind}</span>
      <span class="cap-id">${escapeHtml(card.id)}</span>
      <span class="cap-meta">${escapeHtml(agentId)}</span>
      <span class="cap-governance">
        ${lifecycle.status ? `<span class="life-status">${escapeHtml(lifecycle.status)}</span>` : ""}
        ${actorChip("published", lifecycle.published_by)}
        ${actorChip("approved", lifecycle.approved_by)}
        ${actorChip("deprecated", lifecycle.deprecated_by)}
      </span>
      <span class="cap-meta">v${escapeHtml(card.version || "?")} · skills ${hash ? hash.slice(0, 8) : "—"}</span>
    `;
    li.addEventListener("click", () => selectCapability(card.id));
    li.querySelectorAll("[data-actor-id]").forEach((actor) => {
      actor.addEventListener("click", (event) => {
        event.stopPropagation();
        selectGovernanceActor(actor.dataset.actorId, card.id);
      });
    });
    list.appendChild(li);
  }
  renderGovernanceEvents();
}

function actorChip(label, actorId) {
  if (!actorId) return "";
  return `<button type="button" class="actor-chip" data-actor-id="${escapeHtml(actorId)}">${escapeHtml(label)} ${escapeHtml(shortActor(actorId))}</button>`;
}

function shortActor(actorId) {
  const text = String(actorId || "");
  const parts = text.split(":");
  return parts[parts.length - 1] || text;
}

async function selectCapability(id) {
  state.selectedCapability = id;
  state.selectedWikiNode = null;
  $("detail-title").textContent = "Capability card";
  renderRegistry();
  const resp = await fetch(`/api/capabilities/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    setDetailText(`Could not load card for ${id}`);
    return;
  }
  const card = await resp.json();
  setDetailJson(card);
}

function applyRegistryEvent(payload) {
  const ev = payload.event;
  if (ev === "snapshot") {
    state.capabilities.clear();
    for (const card of payload.cards || []) state.capabilities.set(card.id, card);
    seedGovernanceEvents(payload.cards || []);
  } else if (ev === "registered" || ev === "updated" || isGovernanceEvent(ev)) {
    if (payload.card && payload.card.id) {
      state.capabilities.set(payload.card.id, payload.card);
    }
    if (isGovernanceEvent(ev)) recordGovernanceEvent(payload);
  } else if (ev === "deregistered") {
    if (payload.card && payload.card.id) state.capabilities.delete(payload.card.id);
  }
  renderRegistry();
  // If the open card changed, refresh it.
  if (state.selectedCapability && payload.card && payload.card.id === state.selectedCapability) {
    selectCapability(state.selectedCapability);
  }
}

function isGovernanceEvent(ev) {
  return ev === "card_published" || ev === "card_approved" || ev === "card_deprecated";
}

function seedGovernanceEvents(cards) {
  if (state.governanceEvents.length) return;
  for (const card of cards) {
    const lifecycle = (card && card.lifecycle) || {};
    if (lifecycle.published_by) {
      state.governanceEvents.push({
        event: "card_published",
        card_id: card.id,
        actor_id: lifecycle.published_by,
        ts: lifecycle.published_at || "",
      });
    }
    if (lifecycle.approved_by) {
      state.governanceEvents.push({
        event: "card_approved",
        card_id: card.id,
        actor_id: lifecycle.approved_by,
        ts: lifecycle.approved_at || "",
      });
    }
    if (lifecycle.deprecated_by) {
      state.governanceEvents.push({
        event: "card_deprecated",
        card_id: card.id,
        actor_id: lifecycle.deprecated_by,
        ts: lifecycle.deprecated_at || "",
      });
    }
  }
  state.governanceEvents = state.governanceEvents
    .filter((event) => event.card_id && event.actor_id)
    .slice(-24);
}

function recordGovernanceEvent(payload) {
  const card = payload.card || {};
  const lifecycle = payload.lifecycle || card.lifecycle || {};
  state.governanceEvents.push({
    event: payload.event,
    card_id: card.id || "",
    actor_id: payload.actor_id || actorForLifecycleEvent(payload.event, lifecycle),
    ts: lifecycleTsForEvent(payload.event, lifecycle),
  });
  state.governanceEvents = state.governanceEvents.slice(-24);
}

function actorForLifecycleEvent(event, lifecycle) {
  if (event === "card_published") return lifecycle.published_by || "";
  if (event === "card_approved") return lifecycle.approved_by || "";
  if (event === "card_deprecated") return lifecycle.deprecated_by || "";
  return "";
}

function lifecycleTsForEvent(event, lifecycle) {
  if (event === "card_published") return lifecycle.published_at || "";
  if (event === "card_approved") return lifecycle.approved_at || "";
  if (event === "card_deprecated") return lifecycle.deprecated_at || "";
  return "";
}

function renderGovernanceEvents() {
  const list = $("governance-list");
  if (!list) return;
  list.innerHTML = "";
  const events = [...state.governanceEvents].reverse().slice(0, 8);
  if (!events.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "No lifecycle events yet.";
    list.appendChild(li);
    return;
  }
  for (const event of events) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="gov-event">${escapeHtml(event.event.replace("card_", ""))}</span>
      <button type="button" class="actor-chip" data-actor-id="${escapeHtml(event.actor_id)}">${escapeHtml(shortActor(event.actor_id))}</button>
      <span class="gov-card">${escapeHtml(event.card_id)}</span>
    `;
    const actor = li.querySelector("[data-actor-id]");
    if (actor) {
      actor.addEventListener("click", () => selectGovernanceActor(event.actor_id, event.card_id));
    }
    list.appendChild(li);
  }
}

function selectGovernanceActor(actorId, cardId = "") {
  state.selectedCapability = null;
  state.selectedWikiNode = null;
  renderRegistry();
  $("detail-title").textContent = "Governance actor";
  const events = state.governanceEvents.filter((event) => event.actor_id === actorId);
  setDetailJson({
    actor_id: actorId,
    selected_card: cardId,
    recent_events: events,
  });
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
  } else if (!state.currentTraceId && record.trace_id) {
    // Attached mid-run (e.g. the page was refreshed while a flow was in
    // flight): adopt the in-flight trace so the trace summary and the
    // held-result review controls target it.
    state.currentTraceId = record.trace_id;
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
    pre.className = "json-view";
    pre.innerHTML = highlightJson(body);
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
    life.fallbackReason = plannerFallbackText(record.fallback_reason);
    life.fallbackDetail = record.fallback_detail || "";
    if (!life.fallbackDetail && life.fallbackReason !== (record.fallback_reason || "")) {
      life.fallbackDetail = record.fallback_reason || "";
    }
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
    life.releasePolicy = (record.release_policy || {}).mode || "";
    for (const item of life.plan) {
      const task = ensureTask(item.task);
      task.selectedCapability = item.capability || task.selectedCapability;
      task.purpose = item.purpose || task.purpose;
      task.inputMap = item.input_map || task.inputMap;
    }
    return;
  }
  if (record.step === "plan-governance") {
    life.governance = {
      decision: record.decision || "",
      plan_digest: record.plan_digest || "",
      findings: record.findings || [],
      card_eligibility: record.card_eligibility || {},
      release_policy: record.release_policy || {},
      result_review_required: Boolean(record.result_review_required),
      knowledge_evidence: record.knowledge_evidence || {},
      evaluation_markdown: record.evaluation_markdown || "",
      signals: record.signals || {},
    };
    life.planDigest = record.plan_digest || life.planDigest;
    return;
  }
  if (record.step === "governance-release") {
    life.status = "running";
    return;
  }
  if (record.step === "plan-rejected") {
    life.status = "rejected";
    return;
  }
  if (record.step === "result-draft") {
    life.draft = record.outputs || {};
    life.resultDigest = record.result_digest || "";
    life.status = "draft";
    return;
  }
  if (record.step === "result-hold") {
    life.resultDigest = record.result_digest || life.resultDigest;
    life.status = "draft-held";
    return;
  }
  if (record.step === "result-review") {
    life.review = {
      decision: record.decision || "",
      actor_id: record.actor_id || "",
      reviewed_at: record.reviewed_at || record.ts || "",
      result_digest: record.result_digest || "",
      review_notes: record.review_notes || "",
    };
    life.status = "reviewed";
    return;
  }
  if (record.step === "result-release") {
    life.release = {
      result_digest: record.result_digest || "",
      actor_id: record.actor_id || "",
      released_at: record.ts || "",
    };
    life.result = record.outputs || {};
    life.status = "released";
    return;
  }
  if (record.step === "result-quarantine") {
    life.quarantine = {
      result_digest: record.result_digest || "",
      actor_id: record.actor_id || "",
      quarantined_at: record.ts || "",
    };
    life.status = "quarantined";
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
    if (life.status === "quarantined" || life.status === "rejected") {
      void loadWikiGraph();
      return;
    }
    life.result = record.outputs || life.result || {};
    life.status = record.outputs && record.outputs.error
      ? "error"
      : life.status === "released"
        ? "released"
        : "done";
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
  const governed = governanceStagesActive(life);
  for (const el of document.querySelectorAll(".governance-section")) {
    el.classList.toggle("hidden", !governed);
  }
  const resultLabel = $("result-section-label");
  if (resultLabel) resultLabel.textContent = governed ? "Released result" : "Result";
  const cvNote = $("cv-fit-note");
  if (cvNote) {
    cvNote.textContent = governed
      ? cvNote.dataset.governedNote
      : cvNote.dataset.naiveNote;
  }
  renderLifecycleRail(life);
  renderTraceSummary();
  renderResponsibilityWalk();
  renderPlanner(life);
  renderPlanGovernance(life);
  renderTasks(life);
  renderResultReview(life);
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
    const cleaned = cleanGraph(graph);
    state.wikiGraph = {
      nodes: cleaned.nodes,
      edges: cleaned.edges,
      error: graph.error || "",
    };
  } catch (e) {
    state.wikiGraph = { nodes: [], edges: [], error: String(e) };
  }
  renderWikiGraph();
}

async function resetWikiStore() {
  const stateLabel = $("wiki-graph-state");
  const btn = $("wiki-reset");
  if (!window.confirm("Clear the local wiki store and graph?")) return;
  if (btn) btn.disabled = true;
  if (stateLabel) stateLabel.textContent = "resetting";
  try {
    const resp = await fetch("/api/wiki/reset", { method: "POST" });
    const body = await resp.json();
    if (!resp.ok) {
      state.wikiGraph = { nodes: [], edges: [], error: body.error || resp.statusText };
    } else {
      state.selectedWikiNode = null;
      state.wikiGraph = { nodes: [], edges: [], error: "" };
    }
  } catch (e) {
    state.wikiGraph = { nodes: [], edges: [], error: String(e) };
  } finally {
    if (btn) btn.disabled = false;
    renderWikiGraph();
  }
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

function cleanGraph(graph) {
  const allowedTypes = new Set(["document", "concept", "passage", "open_question"]);
  const nodes = [];
  const seen = new Set();
  for (const raw of Array.isArray(graph.nodes) ? graph.nodes : []) {
    if (!raw || typeof raw !== "object") continue;
    const id = String(raw.id || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    nodes.push({
      id,
      type: allowedTypes.has(raw.type) ? raw.type : "concept",
      label: String(raw.label || id),
      details: raw.details && typeof raw.details === "object" ? raw.details : {},
    });
  }
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = [];
  for (const raw of Array.isArray(graph.edges) ? graph.edges : []) {
    if (!raw || typeof raw !== "object") continue;
    const source = String(raw.source || "").trim();
    const target = String(raw.target || "").trim();
    if (!nodeIds.has(source) || !nodeIds.has(target) || source === target) continue;
    edges.push({
      source,
      target,
      relation: String(raw.relation || "relates_to"),
    });
  }
  return { nodes, edges };
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
  setDetailJson({
    id: node.id,
    type: node.type,
    label: node.label,
    details: node.details || {},
    edges,
  });
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
  if (kind === "agent-card-check") return "Inspect individual agent-card evidence";
  if (kind === "cv-fit") return "Evaluate a CV against a job description";
  if (kind === "cv-fit-interview") return "Evaluate a CV, then generate interview questions";
  if (kind === "knowledge-ingest") return "Ingest source material into the AOA wiki";
  if (kind === "wiki-graph") return "Inspect the AOA wiki graph";
  if (kind === "knowledge-query") return "Answer a question from the AOA wiki";
  if (kind === "flow-audit") return "Audit post-execution flow evidence";
  return "No run yet";
}

function renderLifecycleRail(life) {
  const governed = governanceStagesActive(life);
  const stages = [
    ["intent", "Intent", Boolean(life.intent)],
    ["context", "Capabilities", life.capabilityContext.length > 0],
    ["proposal", "Resolved plan", Boolean(life.plan.length || life.proposal || life.source === "deterministic")],
  ];
  if (governed) stages.push(["governance", "Eligibility", Boolean(life.governance)]);
  stages.push(["work", "Application work", life.tasks.some((task) => ["running", "done", "error"].includes(task.status))]);
  if (governed) {
    stages.push(
      ["draft", "Draft", Boolean(life.draft)],
      ["review", "Human review", Boolean(life.review)],
      ["release", "Release", Boolean(life.release || life.quarantine)],
    );
  } else {
    // The naive sessions run straight through to a released result.
    stages.push(["result", "Result", Boolean(life.result)]);
  }
  const rail = $("lifecycle-rail");
  rail.innerHTML = "";
  for (const [key, label, done] of stages) {
    const li = document.createElement("li");
    li.className = done ? "done" : "pending";
    if (key === "draft" && life.status === "draft-held") {
      li.className = "held";
    }
    if (key === "work" && life.tasks.some((task) => task.status === "running")) {
      li.className = "active";
    }
    if (["governance", "work", "draft", "review", "release", "result"].includes(key)
        && ["error", "rejected", "quarantined"].includes(life.status)) {
      li.classList.add("error");
    }
    li.innerHTML = `<span class="stage-dot"></span><span>${escapeHtml(label)}</span>`;
    rail.appendChild(li);
  }
}

function renderTraceSummary() {
  const idLabel = $("trace-id-label");
  const root = $("trace-summary");
  if (!idLabel || !root) return;
  const records = state.records || [];
  if (!state.currentTraceId || !records.length) {
    idLabel.textContent = "waiting";
    root.className = "trace-summary muted-block";
    root.textContent = "No trace yet.";
    return;
  }

  idLabel.textContent = state.currentTraceId;
  root.className = "trace-summary";
  const auCount = records.filter((r) => r.step === "au-start").length;
  const toolCount = records.filter((r) => r.step === "tool-invoke").length;
  const errorCount = records.filter((r) => r.step === "error" || r.step === "au-error" || r.step === "tool-error").length;
  const duration = traceDuration(records);
  const planner = state.lifecycle.source || "pending";
  root.innerHTML = `
    <span><strong>${escapeHtml(state.currentTraceId)}</strong><em>trace id</em></span>
    <span><strong>${escapeHtml(planner)}</strong><em>planner</em></span>
    <span><strong>${auCount}</strong><em>AU starts</em></span>
    <span><strong>${toolCount}</strong><em>tool calls</em></span>
    <span class="${errorCount ? "warn-text" : ""}"><strong>${errorCount}</strong><em>errors</em></span>
    <span><strong>${duration}</strong><em>duration</em></span>
  `;
}

function renderResponsibilityWalk() {
  const list = $("responsibility-walk");
  if (!list) return;
  list.innerHTML = "";
  const records = (state.records || []).filter(isResponsibilityRecord);
  if (!records.length) {
    const li = document.createElement("li");
    li.className = "trace-step muted";
    li.textContent = "Run an intent to see the correlated responsibility walk.";
    list.appendChild(li);
    return;
  }
  for (const record of records) {
    const view = traceEventView(record);
    const li = document.createElement("li");
    li.className = `trace-step ${view.layer} ${view.status}`;
    li.innerHTML = `
      <span class="trace-layer">${escapeHtml(view.layerLabel)}</span>
      <div class="trace-copy">
        <div class="trace-title">${escapeHtml(view.title)}</div>
        <div class="trace-detail">${escapeHtml(view.detail)}</div>
        ${view.meta ? `<div class="trace-meta">${escapeHtml(view.meta)}</div>` : ""}
      </div>
    `;
    const payload = pickPayload(record);
    if (payload !== null) {
      const details = document.createElement("details");
      details.className = "compact-details trace-payload";
      details.innerHTML = `<summary>Payload</summary><pre class="json-view">${highlightJson(payload)}</pre>`;
      li.appendChild(details);
    }
    list.appendChild(li);
  }
}

function isResponsibilityRecord(record) {
  return new Set([
    "start",
    "capability-context",
    "plan-proposal",
    "governance-invoke",
    "plan-governance",
    "governance-release",
    "plan-rejected",
    "result-draft",
    "result-hold",
    "result-review",
    "result-release",
    "result-quarantine",
    "select",
    "lookup",
    "invoke",
    "au-start",
    "tool-invoke",
    "tool-response",
    "tool-error",
    "au-finish",
    "au-error",
    "response",
    "error",
    "finish",
  ]).has(record.step);
}

function traceEventView(record) {
  const step = record.step || "event";
  const cap = record.capability || "";
  const task = record.task || "";
  const parent = record.parent_capability || "";
  const agentId = record.agent_id || "";
  const layer = traceLayer(step);
  const status = step.includes("error") || step === "error" ? "error" : step.endsWith("response") || step === "finish" || step === "au-finish" ? "done" : "";
  const latency = record.latency_seconds != null ? `${record.latency_seconds.toFixed(2)}s` : "";
  if (step === "start") {
    return traceView(layer, status, "Intent received", record.workflow || (record.intent && record.intent.kind) || "workflow", latency);
  }
  if (step === "capability-context") {
    return traceView(layer, status, "Registry context loaded", `${(record.capabilities || []).length} AU cards considered`, latency);
  }
  if (step === "plan-proposal") {
    const validation = record.validation && record.validation.valid ? "validated" : record.fallback_reason ? "fallback" : "pending validation";
    return traceView(layer, status, "Planner proposed route", `${record.source || "planner"} plan, ${validation}`, latency);
  }
  if (step === "governance-invoke") {
    return traceView("governance", status, `Evaluating resolved plan`, record.capability || "plan governance", record.plan_digest || "");
  }
  if (step === "plan-governance") {
    return traceView("governance", status, `Plan decision: ${record.decision || "unknown"}`, record.workflow || "workflow", record.plan_digest || "");
  }
  if (step === "plan-rejected") {
    return traceView("governance", "error", "Plan blocked as ineligible", "No application AU was invoked", record.plan_digest || "");
  }
  if (step === "result-draft") {
    return traceView("result", "done", "Draft evaluation ready", "Draft is not released", record.result_digest || "");
  }
  if (step === "result-hold") {
    return traceView("governance", "held", "Draft held for human review", "Review the actual evaluation before release", record.result_digest || "");
  }
  if (step === "result-review") {
    return traceView("governance", record.decision === "reject" ? "error" : "done", `Result ${record.decision || "reviewed"}`, record.actor_id || "human reviewer", record.result_digest || "");
  }
  if (step === "result-release") {
    return traceView("result", "done", "Approved result released", record.actor_id || "human reviewer", record.result_digest || "");
  }
  if (step === "result-quarantine") {
    return traceView("result", "error", "Rejected result quarantined", record.actor_id || "human reviewer", record.result_digest || "");
  }
  if (step === "governance-release") {
    return traceView("governance", "done", "Plan released automatically", record.decision || "proceed", record.plan_digest || "");
  }
  if (step === "select") {
    const hash = record.card && record.card.provenance && record.card.provenance.skills_hash;
    return traceView(layer, status, `Selected ${cap}`, task || "task", hash ? `skills ${hash.slice(0, 8)}` : latency);
  }
  if (step === "lookup") {
    return traceView(layer, status, `Looked up ${cap}`, task || "capability card", endpointHost(record.card && record.card.endpoint));
  }
  if (step === "invoke") {
    return traceView(layer, status, `Orchestrator invoked ${cap}`, shapeLine(record.inputs), latency || task);
  }
  if (step === "au-start") {
    const hash = record.skills_hash ? `skills ${String(record.skills_hash).slice(0, 8)}` : "";
    return traceView(layer, status, `${cap} started`, shapeLine(record.inputs_shape), [agentId || record.agent, record.model, hash].filter(Boolean).join(" · "));
  }
  if (step === "tool-invoke") {
    const detail = record.query ? `query: ${record.query}` : shapeLine(record.inputs_shape);
    const meta = record.operation ? `${record.operation} · inward tool boundary` : "inward tool boundary";
    return traceView(layer, status, `${parent} called ${cap}`, detail, meta);
  }
  if (step === "tool-response") {
    const citation = Array.isArray(record.citations) ? record.citations[0] : null;
    const detail = citation && citation.passage_id
      ? `citation: ${citation.passage_id}`
      : shapeLine(record.outputs_shape);
    const meta = citation && citation.source_path
      ? citation.source_path
      : signalLine(record.signals) || latency;
    return traceView(layer, status, `${cap} returned`, detail, meta);
  }
  if (step === "tool-error") {
    return traceView(layer, status, `${cap} failed`, record.error || "tool error", latency);
  }
  if (step === "au-finish") {
    return traceView(layer, status, `${cap} finished`, shapeLine(record.outputs_shape), signalLine(record.signals) || latency);
  }
  if (step === "au-error") {
    return traceView(layer, status, `${cap} failed`, record.error || "AU error", agentId || record.agent || "");
  }
  if (step === "response") {
    return traceView(layer, status, `Orchestrator received ${cap}`, shapeLine(record.outputs), signalLine(record.signals) || latency);
  }
  if (step === "error") {
    return traceView(layer, status, `Error in ${cap || task || "workflow"}`, record.error || "error", latency);
  }
  if (step === "finish") {
    return traceView(layer, status, "Final artefact ready", shapeLine(record.outputs), latency);
  }
  return traceView(layer, status, step, cap || task || "", latency);
}

function traceView(layer, status, title, detail, meta) {
  const labels = {
    intent: "Intent",
    planner: "Planner",
    registry: "Registry",
    orchestrator: "Run",
    au: "AU",
    tool: "Tool",
    governance: "Governance",
    result: "Result",
  };
  return {
    layer,
    status,
    layerLabel: labels[layer] || "Trace",
    title,
    detail: detail || "",
    meta: meta || "",
  };
}

function traceLayer(step) {
  if (step === "start") return "intent";
  if (step === "capability-context" || step === "lookup" || step === "select") return "registry";
  if (step === "plan-proposal") return "planner";
  if (["governance-invoke", "plan-governance", "governance-release", "plan-rejected", "result-hold", "result-review"].includes(step)) return "governance";
  if (["result-draft", "result-release", "result-quarantine"].includes(step)) return "result";
  if (step === "au-start" || step === "au-finish" || step === "au-error") return "au";
  if (step === "tool-invoke" || step === "tool-response" || step === "tool-error") return "tool";
  if (step === "finish") return "result";
  return "orchestrator";
}

function traceDuration(records) {
  const first = Date.parse(records[0] && records[0].ts);
  const last = Date.parse(records[records.length - 1] && records[records.length - 1].ts);
  if (!Number.isFinite(first) || !Number.isFinite(last) || last < first) return "running";
  return `${((last - first) / 1000).toFixed(1)}s`;
}

function shapeLine(value) {
  if (!value || typeof value !== "object") return "";
  const keys = Object.keys(value);
  if (!keys.length) return "empty payload";
  return keys.slice(0, 5).map((key) => `${key}:${shapeToken(value[key])}`).join(", ");
}

function shapeToken(value) {
  if (value && typeof value === "object" && value.type) {
    if (value.type === "string") return `${value.chars || 0} chars`;
    if (value.type === "array") return `array(${value.count || 0})`;
    return value.type;
  }
  if (Array.isArray(value)) return `array(${value.length})`;
  if (value && typeof value === "object") return "object";
  if (typeof value === "string") return `${value.length} chars`;
  return typeof value;
}

function signalLine(signals) {
  if (!signals || typeof signals !== "object") return "";
  const entries = Object.entries(signals).slice(0, 4);
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(" · ");
}

function endpointHost(endpoint) {
  if (!endpoint) return "";
  try {
    return new URL(endpoint).host;
  } catch {
    return String(endpoint);
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
    fallback.textContent = life.fallbackReason;
    body.appendChild(fallback);

    if (life.fallbackDetail && life.fallbackDetail !== life.fallbackReason) {
      const details = document.createElement("details");
      details.className = "compact-details";
      details.innerHTML = `<summary>Planner fallback detail</summary><pre class="json-view">${escapeHtml(life.fallbackDetail)}</pre>`;
      body.appendChild(details);
    }
  }

  if (life.proposal) {
    const details = document.createElement("details");
    details.className = "compact-details";
    details.innerHTML = `<summary>Planner JSON</summary><pre class="json-view">${highlightJson(life.proposal)}</pre>`;
    body.appendChild(details);
  }
}

function renderPlanGovernance(life) {
  const stateLabel = $("governance-state");
  const body = $("governance-body");
  if (!stateLabel || !body) return;

  if (!life.governance) {
    stateLabel.textContent = "waiting";
    body.className = "result-body muted-block";
    body.textContent = "No resolved plan has been evaluated yet.";
    return;
  }

  stateLabel.textContent = life.governance.decision || "evaluated";
  body.className = "result-body";
  body.innerHTML = "";
  const markdown = life.governance.evaluation_markdown || "";
  if (markdown) body.appendChild(renderMarkdown(markdown));
  else {
    const pre = document.createElement("pre");
    pre.className = "json-view";
    pre.innerHTML = highlightJson(life.governance);
    body.appendChild(pre);
  }
}


function renderResultReview(life) {
  const stateLabel = $("result-review-state");
  const body = $("result-review-body");
  const controls = $("result-review-controls");
  if (!stateLabel || !body || !controls) return;

  controls.hidden = life.status !== "draft-held";
  if (!life.draft) {
    stateLabel.textContent = life.status === "rejected" ? "plan blocked" : "waiting";
    body.className = "result-body muted-block";
    body.textContent = life.status === "rejected"
      ? "The plan was ineligible, so no application AU ran and no draft exists."
      : "No draft result is awaiting review.";
    return;
  }

  stateLabel.textContent = life.status;
  body.className = "result-body";
  body.innerHTML = "";
  const notice = document.createElement("p");
  notice.className = "draft-notice";
  if (life.status === "released") {
    notice.textContent = `Human-approved draft released unchanged. Result digest: ${life.resultDigest}`;
  } else if (life.status === "quarantined") {
    notice.textContent = `Human-rejected draft quarantined; no result released. Result digest: ${life.resultDigest}`;
  } else {
    notice.textContent = `Draft only — not released. Result digest: ${life.resultDigest}`;
  }
  body.appendChild(notice);
  const markdown = life.draft.report_markdown || life.draft.answer_markdown || life.draft.ingest_markdown || life.draft.findings_markdown || "";
  if (markdown) body.appendChild(renderMarkdown(markdown));
  else {
    const pre = document.createElement("pre");
    pre.className = "json-view";
    pre.innerHTML = highlightJson(life.draft);
    body.appendChild(pre);
  }
  if (life.review) {
    const review = document.createElement("p");
    review.className = "approval-evidence";
    review.textContent = `${life.review.decision} by ${life.review.actor_id}: ${life.review.review_notes}`;
    body.appendChild(review);
  }
}


async function reviewHeldResult(decision) {
  const life = state.lifecycle;
  const approve = $("result-review-approve");
  const reject = $("result-review-reject");
  const status = $("result-review-action-status");
  const notes = $("result-review-notes").value.trim();
  if (!state.currentTraceId || life.status !== "draft-held" || !life.resultDigest) {
    status.textContent = "No held draft is attached to this page; submit a new run and review its draft.";
    return;
  }
  if (!notes) {
    status.textContent = "Add reviewer notes before approving or rejecting the draft.";
    return;
  }

  approve.disabled = true;
  reject.disabled = true;
  status.textContent = decision === "approve" ? "Approving and releasing…" : "Rejecting and quarantining…";
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(state.currentTraceId)}/review`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        decision,
        result_digest: life.resultDigest,
        review_notes: notes,
      }),
    });
    const run = await response.json();
    if (!response.ok) {
      status.textContent = `error: ${apiErrorMessage(run, response.statusText)}`;
      return;
    }
    life.status = run.status || life.status;
    life.review = run.review || life.review;
    life.resultDigest = run.result_digest || life.resultDigest;
    if (run.status === "released") life.result = run.outputs || {};
    status.textContent = run.status === "released"
      ? "Reviewed result released."
      : run.status === "quarantined"
        ? "Reviewed result quarantined."
        : `run ${run.status}`;
    renderLifecycle();
  } catch (error) {
    status.textContent = `error: ${error}`;
  } finally {
    approve.disabled = false;
    reject.disabled = false;
  }
}


function apiErrorMessage(payload, fallback) {
  const value = payload && (payload.detail || payload.error);
  if (value == null) return fallback;
  if (typeof value !== "string") {
    // e.g. FastAPI validation errors put a list of objects in `detail`.
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }
  try {
    const parsed = JSON.parse(value);
    return parsed.detail || parsed.error || value;
  } catch {
    return value;
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
    details.innerHTML = `<summary>Details</summary><pre class="json-view">${highlightJson(taskDetail(task))}</pre>`;
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
    body.textContent = life.status === "draft-held"
      ? "The evaluation remains a draft. Review it above before any result is released."
      : life.status === "quarantined"
        ? "The human-rejected draft is quarantined; no final result was released."
        : life.status === "rejected"
          ? "The plan was ineligible, so no result was produced."
          : "No released result yet.";
    return;
  }
  const markdown = life.result.report_markdown || life.result.answer_markdown || life.result.ingest_markdown || life.result.findings_markdown || "";
  resultState.textContent = life.result.error ? "error" : life.status === "released" ? "released" : "complete";
  body.className = "result-body";
  if (markdown) {
    body.appendChild(renderMarkdown(markdown));
  } else {
    const pre = document.createElement("pre");
    pre.className = "json-view";
    pre.innerHTML = highlightJson(life.result);
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
      fallback_reason: plannerFallbackText(record.fallback_reason),
      fallback_detail: record.fallback_detail || record.fallback_reason,
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
  if (record.step === "governance-invoke") return { plan_digest: record.plan_digest, inputs: record.inputs };
  if (record.step === "plan-governance") {
    return {
      decision: record.decision,
      plan_digest: record.plan_digest,
      card_eligibility: record.card_eligibility,
      release_policy: record.release_policy,
      result_review_required: record.result_review_required,
      knowledge_evidence: record.knowledge_evidence,
      findings: record.findings,
      signals: record.signals,
    };
  }
  if (["governance-release", "plan-rejected", "result-draft", "result-hold", "result-review", "result-release", "result-quarantine"].includes(record.step)) {
    return {
      decision: record.decision,
      actor_id: record.actor_id,
      plan_digest: record.plan_digest,
      result_digest: record.result_digest,
      review_required: record.review_required,
      review_notes: record.review_notes,
      card_eligibility: record.card_eligibility,
      outputs: record.outputs,
    };
  }
  if (record.step === "lookup") return record.card;
  if (record.step === "invoke") return record.inputs;
  if (record.step === "au-start") {
    return {
      capability: record.capability,
      agent: record.agent,
      agent_id: record.agent_id,
      model: record.model,
      skills_hash: record.skills_hash,
      inputs_shape: record.inputs_shape,
    };
  }
  if (record.step === "tool-invoke") {
    return {
      parent_capability: record.parent_capability,
      capability: record.capability,
      operation: record.operation,
      query: record.query,
      limit: record.limit,
      inputs_shape: record.inputs_shape,
    };
  }
  if (record.step === "tool-response") {
    return {
      passages_returned: record.passages_returned,
      citations: record.citations,
      outputs_shape: record.outputs_shape,
      signals: record.signals,
    };
  }
  if (record.step === "au-finish") {
    return {
      capability: record.capability,
      agent: record.agent,
      agent_id: record.agent_id,
      outputs_shape: record.outputs_shape,
      signals: record.signals,
    };
  }
  if (record.step === "au-error" || record.step === "tool-error") {
    return { capability: record.capability, agent: record.agent, agent_id: record.agent_id, error: record.error };
  }
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
  if (["response", "result-draft", "result-release", "finish"].includes(record.step)) {
    return outputs.report_markdown || outputs.answer_markdown || outputs.ingest_markdown || outputs.findings_markdown || "";
  }
  if (record.step === "plan-governance") {
    return record.evaluation_markdown || "";
  }
  return "";
}

function renderMarkdown(markdown) {
  const root = document.createElement("div");
  root.className = "rendered-markdown";
  const lines = markdown.split("\n");
  let list = null;
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      list = null;
      index += 1;
      continue;
    }

    if (line.startsWith("|") && index + 1 < lines.length) {
      const header = markdownTableCells(line);
      const separator = markdownTableCells(lines[index + 1].trim());
      if (header.length && separator.length === header.length && separator.every(isMarkdownTableSeparator)) {
        list = null;
        const wrapper = document.createElement("div");
        wrapper.className = "markdown-table-wrap";
        const table = document.createElement("table");
        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");
        for (const cell of header) {
          const th = document.createElement("th");
          th.innerHTML = renderInlineMarkdown(cell);
          headerRow.appendChild(th);
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);
        const tbody = document.createElement("tbody");
        index += 2;
        while (index < lines.length && lines[index].trim().startsWith("|")) {
          const row = document.createElement("tr");
          for (const cell of markdownTableCells(lines[index].trim())) {
            const td = document.createElement("td");
            td.innerHTML = renderInlineMarkdown(cell);
            row.appendChild(td);
          }
          tbody.appendChild(row);
          index += 1;
        }
        table.appendChild(tbody);
        wrapper.appendChild(table);
        root.appendChild(wrapper);
        continue;
      }
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      list = null;
      const level = Math.min(6, heading[1].length + 2);
      const h = document.createElement(`h${level}`);
      h.innerHTML = renderInlineMarkdown(heading[2]);
      root.appendChild(h);
      index += 1;
      continue;
    }
    if (line.startsWith(">")) {
      list = null;
      const quote = document.createElement("blockquote");
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        const quoteLine = lines[index].trim().replace(/^>\s?/, "");
        const p = document.createElement("p");
        p.innerHTML = renderInlineMarkdown(quoteLine);
        quote.appendChild(p);
        index += 1;
      }
      root.appendChild(quote);
      continue;
    }
    if (line === "---") {
      list = null;
      root.appendChild(document.createElement("hr"));
      index += 1;
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
      index += 1;
      continue;
    }
    list = null;
    const p = document.createElement("p");
    p.innerHTML = renderInlineMarkdown(line);
    root.appendChild(p);
    index += 1;
  }
  return root;
}

function markdownTableCells(line) {
  const text = line.replace(/^\|/, "").replace(/\|$/, "");
  const cells = [];
  let cell = "";
  let escaped = false;
  for (const char of text) {
    if (escaped) {
      cell += char;
      escaped = false;
    } else if (char === "\\") {
      escaped = true;
    } else if (char === "|") {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += char;
    }
  }
  cells.push(cell.trim());
  return cells;
}

function isMarkdownTableSeparator(cell) {
  return /^:?-{3,}:?$/.test(cell);
}

function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function setDetailText(text) {
  const body = $("card-body");
  body.classList.remove("json-view");
  body.textContent = text;
}

function setDetailJson(value) {
  const body = $("card-body");
  body.classList.add("json-view");
  body.innerHTML = highlightJson(value);
}

function highlightJson(value) {
  const json = JSON.stringify(value, null, 2);
  return json.replace(
    /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"\s*:|"(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (token) => {
      const trimmed = token.trimEnd();
      const suffix = token.slice(trimmed.length);
      if (trimmed.endsWith(":")) {
        return `<span class="json-key">${escapeHtml(trimmed.slice(0, -1))}</span>:${suffix}`;
      }
      if (trimmed.startsWith('"')) {
        return `<span class="json-string">${escapeHtml(trimmed)}</span>${suffix}`;
      }
      if (trimmed === "true" || trimmed === "false") {
        return `<span class="json-boolean">${trimmed}</span>${suffix}`;
      }
      if (trimmed === "null") {
        return `<span class="json-null">${trimmed}</span>${suffix}`;
      }
      return `<span class="json-number">${trimmed}</span>${suffix}`;
    },
  );
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
  if (state.mode === "wiki-graph") {
    btn.disabled = true;
    status.textContent = "refreshing...";
    await loadWikiGraph();
    status.textContent = "refreshed";
    btn.disabled = false;
    return;
  }
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
    } else if (body.status === "draft-held") {
      status.textContent = `draft ready for human review · trace ${body.trace_id}`;
    } else if (body.status === "rejected") {
      status.textContent = `plan blocked by eligibility policy · trace ${body.trace_id}`;
    } else if (body.outputs && body.outputs.error) {
      status.textContent = `error: ${body.outputs.error}`;
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
  if (state.mode === "cv-fit" || state.mode === "cv-fit-interview") {
    const cv = $("intent-cv").value.trim();
    const jd = $("intent-jd").value.trim();
    if ((!cv && !state.cvFile) || (!jd && !state.jdFile)) {
      status.textContent = "need both a CV and a job description";
      return null;
    }
    return {
      kind: state.mode,
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

  if (state.mode === "flow-audit") {
    return {
      kind: state.mode,
      include_legacy: Boolean($("flow-audit-include-legacy")?.checked),
    };
  }

  if (state.mode === "agent-card-check") {
    // No learner inputs: this workflow reads the estate's governance artefacts.
    return { kind: state.mode };
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

function applyWorkflowConfig() {
  const session4Stages = ["agent-card-check", "cv-fit", "flow-audit"];
  if (session4Stages.every((mode) => enabledWorkflows.has(mode))) {
    const stageLabels = {
      "agent-card-check": "1. Agent card check",
      "cv-fit": "2. CV fit",
      "flow-audit": "3. Flow audit",
    };
    for (const [mode, label] of Object.entries(stageLabels)) {
      const btn = document.querySelector(`[data-mode="${mode}"]`);
      if (btn) btn.textContent = label;
    }
  }
  for (const btn of document.querySelectorAll("[data-mode]")) {
    btn.hidden = !enabledWorkflows.has(btn.dataset.mode);
  }
  // setMode recomputes every panel's hidden state from the selected mode.
  const initialMode = enabledWorkflows.has(state.mode) ? state.mode : configuredWorkflows[0] || "cv-fit";
  setMode(initialMode);
}

function setMode(mode) {
  if (!enabledWorkflows.has(mode)) return;
  state.mode = mode;
  for (const btn of document.querySelectorAll("[data-mode]")) {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  }
  for (const panel of document.querySelectorAll("[data-mode-panel]")) {
    panel.classList.toggle("hidden", panel.dataset.modePanel !== panelForMode(mode));
  }
  $("lifecycle").classList.toggle("hidden", mode === "wiki-graph");
  const labels = {
    "agent-card-check": "Run agent card check",
    "cv-fit": "Run CV fit",
    "cv-fit-interview": "Run cv-fit + interview",
    "knowledge-ingest": "Run ingest",
    "wiki-graph": "Refresh graph",
    "knowledge-query": "Ask wiki",
    "flow-audit": "Run flow audit",
  };
  $("intent-submit").textContent = labels[mode] || "Run";
  $("intent-status").textContent = "";
  if (mode === "wiki-graph") void loadWikiGraph();
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
  applyWorkflowConfig();
  setupModeTabs();
  $("intent-submit").addEventListener("click", submitIntent);
  $("result-review-approve").addEventListener("click", () => reviewHeldResult("approve"));
  $("result-review-reject").addEventListener("click", () => reviewHeldResult("reject"));
  const reset = $("wiki-reset");
  if (reset) reset.addEventListener("click", resetWikiStore);
  setupFileDrop();
  renderLifecycle();
  loadInitialRegistry();
  if (enabledWorkflows.has("wiki-graph")) void loadWikiGraph();
  connectEvents();
});
