// Pure projections of recorded evidence; these functions never execute work.
export const escapeText = (value) => String(value ?? "").replace(/[&<>"']/g,
  char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

export function cardSections(card) {
  const displayed = new Set(["id", "purpose", "inputs", "outputs", "constraints", "evaluation_signals"]);
  return {
    inputs: Array.isArray(card.inputs) ? card.inputs : [],
    outputs: Array.isArray(card.outputs) ? card.outputs : [],
    constraints: Array.isArray(card.constraints) ? card.constraints : [],
    signals: Array.isArray(card.evaluation_signals) ? card.evaluation_signals : [],
    // Preserve unknown fields and nested metadata, rather than a fixed whitelist.
    metadata: Object.fromEntries(Object.entries(card).filter(([key]) => !displayed.has(key))),
    json: JSON.stringify(card, null, 2),
  };
}

export function taskIds(records) {
  return [...new Set(records.flatMap(record => {
    if (record.step === "breakdown") return (record.tasks || []).map(task => task.id);
    if (record.step === "plan") return (record.plan || []).map(task => task.task);
    return record.task && ["allocation", "invoke", "response", "allocation-held"].includes(record.step) ? [record.task] : [];
  }).filter(Boolean))];
}

export function allocationEvidence(records, taskId) {
  const latest = (step, predicate = () => true) => records.findLast(r => r.step === step && predicate(r));
  const task = latest("breakdown")?.tasks?.find(task => task.id === taskId);
  const allocation = latest("allocation", r => r.task === taskId);
  const accepted = latest("allocation-accepted", r => r.task === taskId);
  const validation = latest("composition-validation");
  const held = latest("allocation-held", r => !r.task || r.task === taskId);
  const execution = latest("invoke", r => r.task === taskId);
  const response = latest("response", r => r.task === taskId);
  const candidates = Array.isArray(allocation?.candidates) ? allocation.candidates : [];
  const validatedBeforeAcceptance = Boolean(accepted && validation?.valid === true
    && records.indexOf(validation) < records.indexOf(accepted));
  return { task, allocation, accepted, validation, held, execution, response, candidates, validatedBeforeAcceptance };
}

export function probabilityLabel(value) {
  return typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "Not reported";
}

export function allocationHoldMessage(allocation, held) {
  if (held?.message || allocation?.message) return held?.message || allocation.message;
  // Older traces have the evidence but only a generic selection-held reason.
  if (!held) return "";
  if (allocation?.outcome === "no-eligible-capability") return "No AU passed the recorded contract eligibility checks. No AU was invoked.";
  if (allocation?.choice === "no_suitable_capability") return "The decision model returned no suitable capability. No AU was invoked.";
  const probability = allocation?.decision?.winner_probability;
  const minimum = allocation?.minimum_probability;
  if (Number.isFinite(probability) && Number.isFinite(minimum) && probability < minimum) {
    const scoreLabel = (probability * 100).toFixed(2), minimumLabel = (minimum * 100).toFixed(2);
    const exact = scoreLabel === minimumLabel ? ` (reported probability ${probability} < ${minimum})` : "";
    return `${allocation.choice || "The returned choice"} received ${scoreLabel}%, below the configured ${minimumLabel}% minimum${exact}. No AU was invoked.`;
  }
  return `Selection held: ${held.reason || "inspect the recorded evidence"}.`;
}

export function runOutputs(records) {
  // Keep task order, while a later recorded response updates that task's output.
  const outputs = new Map();
  for (const record of records) {
    if (record.step === "response") outputs.set(record.task || record.capability, record);
  }
  return [...outputs.values()];
}

export function recordedInputs(records, output) {
  const index = records.indexOf(output);
  return records.slice(0, index < 0 ? records.length : index).findLast(r =>
    r.step === "invoke" && r.task === output.task)?.inputs ?? null;
}

export function runEvidenceStatus(life) {
  const states = {
    "allocation-held": "Allocation held — no AU was invoked",
    "draft-held": "Held draft — awaiting exact-result review",
    draft: "Draft — not released",
    reviewed: "Review recorded — inspect release or quarantine evidence",
    released: "Released result",
    quarantined: "Quarantined — no result released",
    rejected: "Plan rejected — no application result",
    error: "Run error — inspect recorded evidence",
    done: "Run completed — output quality still needs review",
    running: "Run in progress",
  };
  return states[life.status] || "No run selected";
}
