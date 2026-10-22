import { escapeText as esc, cardSections, taskIds, allocationEvidence,
  probabilityLabel, runOutputs, recordedInputs, runEvidenceStatus } from "./inspection-model.mjs";

const jsonBlock = value => `<pre class="inspection-json">${esc(JSON.stringify(value, null, 2))}</pre>`;
const valueText = value => typeof value === "object" ? JSON.stringify(value) : String(value ?? "");
const list = values => values.length ? `<ul>${values.map(v => `<li>${esc(valueText(v))}</li>`).join("")}</ul>` : '<p class="inspection-muted">None declared.</p>';
const fieldList = fields => fields.map(field => `<div class="inspection-field"><span>${esc(field.name || "Unnamed field")}${field.required ? ' <small>required</small>' : ''}</span><code>${esc(valueText(field.type || "unspecified"))}</code></div>`).join("") || '<p class="inspection-muted">None declared.</p>';
const detail = (label, value) => `<details><summary>${esc(label)}</summary>${jsonBlock(value)}</details>`;

// Replace only the contents of an inspection panel, preserving open disclosures
// and keyboard focus when live evidence updates the same view.
function updatePanel(element, html) {
  if (element.dataset.rendered === html) return;
  const open = new Set([...element.querySelectorAll("details[open]")].map(d => d.querySelector("summary")?.textContent));
  const focus = element.contains(document.activeElement) ? document.activeElement.dataset.focusKey : null;
  element.innerHTML = html;
  element.dataset.rendered = html;
  for (const d of element.querySelectorAll("details")) if (open.has(d.querySelector("summary")?.textContent)) d.open = true;
  if (focus) [...element.querySelectorAll("[data-focus-key]")].find(e => e.dataset.focusKey === focus)?.focus({preventScroll:true});
}

export function createStudioInspector({ renderMarkdown, selectCapability }) {
  const $ = id => document.getElementById(id);
  let card = null, cardView = "readable", records = [], life = {}, saved = false;
  let taskId = "", stage = "choice", candidateId = "", outputId = "", traceId = null;
  let taskPinned = false, outputPinned = false;
  const cardControls = $("card-view-controls");
  const cardReadable = $("card-readable");
  const cardJson = $("card-body");

  function setWorkspace(value) {
    document.body.dataset.workspace = value;
    for (const button of document.querySelectorAll("[data-workspace-view]")) {
      button.setAttribute("aria-pressed", String(button.dataset.workspaceView === value));
    }
  }
  for (const button of document.querySelectorAll("[data-workspace-view]")) {
    button.addEventListener("click", () => setWorkspace(button.dataset.workspaceView));
  }

  function paintCard() {
    cardControls.hidden = !card;
    cardReadable.hidden = !card || cardView !== "readable";
    cardJson.hidden = Boolean(card && cardView !== "json");
    for (const b of cardControls.querySelectorAll("[data-card-view]")) b.setAttribute("aria-pressed", String(b.dataset.cardView === cardView));
    if (!card) return;
    const sections = cardSections(card);
    updatePanel(cardReadable, `<div class="inspection-heading"><h3>${esc(card.id)}</h3><span class="inspection-badge">${esc(card.kind || "au")} · ${esc(card.lifecycle?.status || "status not declared")}</span></div>
      <p>${esc(card.purpose || "No purpose declared.")}</p>
      <div class="inspection-contract"><section><h4>Accepts</h4>${fieldList(sections.inputs)}</section><section><h4>Returns</h4>${fieldList(sections.outputs)}</section></div>
      <h4>Declared constraints</h4>${list(sections.constraints)}
      <details><summary>Declared evaluation signals</summary>${list(sections.signals)}<p class="inspection-muted">These are declarations. Inspect a run for observed signals.</p></details>
      <details><summary>Identity, lifecycle and technical metadata</summary>${Object.entries(sections.metadata).map(([key,value])=>detail(key.replaceAll("_"," "),value)).join("")}</details>
      <p class="inspection-muted">Current registry declaration. Registry approval does not establish output quality.</p>`);
  }
  cardControls.addEventListener("click", async event => {
    const button = event.target.closest("button");
    if (!button || !card) return;
    if (button.dataset.cardView) { cardView = button.dataset.cardView; paintCard(); }
    if (button.id === "card-copy") {
      try {
        await navigator.clipboard.writeText(cardSections(card).json);
        $("card-copy-status").textContent = "Complete JSON copied.";
      } catch {
        cardView = "json"; paintCard();
        $("card-copy-status").textContent = "Copy is unavailable in this browser. Select the complete JSON below.";
      }
    }
  });

  function stageBody(view) {
    const a = view.allocation, d = a?.decision;
    const chosen = view.candidates.find(c => c.id === candidateId);
    const raw = value => value ? detail("Recorded event",value) : "";
    if (stage === "task") return `<h3>Proposed task</h3><p>${esc(view.task?.purpose || "Task proposal not recorded in this trace.")}</p>${raw(view.task)}`;
    if (stage === "eligible") return `<h3>Contract eligibility</h3><p>${a ? `${view.candidates.filter(c=>c.eligible).length} eligible capabilities recorded for this task.` : "No bounded-allocation event recorded. The original planner evidence remains available in Studio."}</p>
      ${view.candidates.map(c=>`<details><summary>${esc(c.id)} · ${c.eligible?'eligible':'excluded'}</summary><p>${esc(c.purpose)}</p>${c.eligible?'<p>Eligible under the recorded contract checks; quality is not established.</p>':list(c.reasons || [])}</details>`).join("")}`;
    if (stage === "choice") {
      if (!a) return '<h3>Choice evidence</h3><p>No bounded-allocation event is recorded for this task. Inspect the original selection events in Studio.</p>';
      return `<h3>${a.model_called ? "Model choice" : "Contract selection"}</h3>
        <p>Returned choice: <strong>${esc(a.choice || "none")}</strong></p>
        <p>${a.model_called ? `${esc(d?.provider || "provider not recorded")} / ${esc(d?.model || "model not recorded")}` : "No decision-model call was made for this allocation."}</p>
        ${chosen ? `<h4>Inspecting ${esc(chosen.id)}</h4><p>${esc(chosen.purpose)}</p>` : ""}
        ${a.model_called ? `<div class="inspection-facts"><div><strong>${probabilityLabel(d?.probabilities?.[candidateId])}</strong><span>Model-reported probability for this candidate</span></div><div><strong>${Number.isFinite(d?.latency_seconds) ? d.latency_seconds.toFixed(3)+' s' : 'Not recorded'}</strong><span>Allocator call</span></div></div><p class="inspection-muted">Model probability is not measured accuracy. Inspecting another candidate does not change the recorded choice.</p><p>No suitable capability: ${probabilityLabel(d?.probabilities?.no_suitable_capability)}</p>` : ""}
        <p>Recorded outcome: ${esc(a.outcome || "not reported")}</p>${d ? detail("Decision evidence and usage",d) : ""}${raw(a)}`;
    }
    if (stage === "validation") return `<h3>Whole-plan composition check</h3><p>${view.validation ? view.validation.valid ? 'Composition validation passed.' : 'Composition validation failed.' : 'No composition-validation event recorded.'}</p><p>${esc(view.validation?.scope || view.validation?.error || "")}</p>${raw(view.validation)}<p class="inspection-muted">A valid composition does not establish the factual quality of its outputs. Pre-execution governance is a separate control.</p>`;
    return `<h3>Accepted binding</h3><p>${view.accepted ? `<code>${esc(taskId)} → ${esc(view.accepted.accepted_choice)}</code>` : "No accepted-binding event recorded for this task."}</p>
      ${view.accepted ? `<p>${view.validatedBeforeAcceptance ? 'Whole-plan validation is recorded before this acceptance.' : 'A passing composition check before acceptance is not established by these records.'}</p>` : ""}
      ${view.held ? `<p class="inspection-warning">Selection held: ${esc(view.held.reason || "inspect the recorded event")}</p>` : ""}
      <p>${view.execution ? 'Application invocation is recorded for this task.' : 'No application invocation is recorded for this task.'}</p>${raw(view.accepted)}${raw(view.held)}`;
  }

  function paintSelection() {
    const ids = taskIds(records);
    if (!taskPinned || !ids.includes(taskId)) taskId = records.find(r=>r.step==='allocation' && r.model_called)?.task || ids[0] || "";
    const view = allocationEvidence(records, taskId);
    const eligible = view.candidates.filter(c=>c.eligible);
    if (!eligible.some(c=>c.id===candidateId)) candidateId = view.allocation?.choice || eligible[0]?.id || "";
    updatePanel($("inspection-task-tabs"), ids.map(id=>`<button type="button" data-inspect-task="${esc(id)}" data-focus-key="task-${esc(id)}" aria-pressed="${id===taskId}">${esc(id.replaceAll('-',' '))}</button>`).join("") || '<p class="inspection-muted">Run a workflow or open a saved case to inspect its planning evidence.</p>');
    $("inspection-selection-content").hidden = !ids.length;
    updatePanel($("inspection-candidates"), `<h3>Eligible candidates</h3>${eligible.map(c=>`<button type="button" class="inspection-candidate" data-inspect-candidate="${esc(c.id)}" data-focus-key="candidate-${esc(c.id)}" aria-pressed="${c.id===candidateId}"><strong>${esc(c.id)}</strong><span>${c.id===view.allocation?.choice?'Returned choice':'Eligible alternative'}</span></button>`).join("") || '<p class="inspection-muted">No eligible-candidate list recorded.</p>'}`);
    for (const b of $("inspection-stages").querySelectorAll("[data-inspect-stage]")) b.setAttribute("aria-pressed",String(b.dataset.inspectStage===stage));
    updatePanel($("inspection-stage-body"),stageBody(view));
    const holds = records.filter(r=>['allocation-held','plan-rejected'].includes(r.step) || r.step==='composition-validation' && r.valid===false);
    $("inspection-plan-notice").textContent = holds.length ? "This trace contains a hold or rejection. Inspect the recorded check; a model choice alone does not authorise execution." : "Recorded order: proposed task → eligibility → choice → composition validation → accepted binding → execution.";
    $("inspection-plan-notice").classList.toggle("inspection-warning",holds.length>0);
  }
  $("allocation-inspector").addEventListener("click",event=>{
    const b=event.target.closest('button'); if(!b)return;
    if(b.dataset.inspectTask){taskId=b.dataset.inspectTask;candidateId="";taskPinned=true;}
    if(b.dataset.inspectStage)stage=b.dataset.inspectStage;
    if(b.dataset.inspectCandidate)candidateId=b.dataset.inspectCandidate;
    if(b.dataset.inspectTask || b.dataset.inspectStage || b.dataset.inspectCandidate)paintSelection();
  });

  function paintOutput() {
    const outputs=runOutputs(records);
    if(!outputPinned || !outputs.some(r=>(r.task||r.capability)===outputId))outputId=outputs.at(-1)?.task||outputs.at(-1)?.capability||"";
    const selected=outputs.find(r=>(r.task||r.capability)===outputId);
    $("inspection-run-status").textContent=runEvidenceStatus(life);
    $("inspection-run-status").classList.toggle("inspection-warning",["draft-held","draft","rejected","quarantined","error"].includes(life.status));
    updatePanel($("inspection-output-tabs"),outputs.map(r=>`<button type="button" data-inspect-output="${esc(r.task||r.capability)}" data-focus-key="output-${esc(r.task||r.capability)}" aria-pressed="${(r.task||r.capability)===outputId}">${esc(r.task||r.capability)}<small>${esc(r.capability||'')}</small></button>`).join("") || '<p class="inspection-muted">No application output is recorded yet. Held selections and rejected plans can be inspected in AU selection.</p>');
    $("inspection-output-content").hidden=!selected;
    if(!selected)return;
    const output=selected.outputs||{};
    const heading=$("inspection-output-heading");heading.textContent=`Recorded output · ${selected.capability||selected.task}`;
    const markdown=output.report_markdown||output.answer_markdown||output.ingest_markdown||output.findings_markdown||"";
    const summary=$("inspection-output-summary");
    const summaryKey=JSON.stringify({output,markdown});
    if(summary.dataset.rendered!==summaryKey){
      summary.replaceChildren();
      if(markdown)summary.appendChild(renderMarkdown(markdown));
      else {
        const fields=Object.entries(output).filter(([,v])=>typeof v==='string');
        summary.innerHTML=fields.length ? fields.map(([key,v])=>`<h4>${esc(key.replaceAll('_',' '))}</h4><p>${esc(v)}</p>`).join('') : '<p>Structured output is available in the complete JSON below.</p>';
      }
      summary.dataset.rendered=summaryKey;
    }
    $("inspection-output-json").textContent=JSON.stringify(output,null,2);
    const inputs=recordedInputs(records,selected);
    updatePanel($("inspection-input-evidence"),inputs===null?'<p class="inspection-muted">Invocation inputs are not present in these records.</p>':Object.entries(inputs).map(([key,v])=>detail(key,v)).join(''));
    updatePanel($("inspection-output-signals"),detail("Observed signals",selected.signals||{})+detail("Recorded response",selected));
    const prompt = ['cv-fit','cv-fit-interview'].includes(life.workflow) ? 'Which claims in the assessment are supported by the CV and job description? Does the evidence establish duration, responsibilities and missing information?' : 'Which claims are supported by the recorded inputs and cited passages? What is absent, inferred or contradicted?';
    $("inspection-review-prompt").textContent=prompt;
    $("inspection-review-link").hidden=life.status!=="draft-held";
  }
  $("run-inspector").addEventListener('click',event=>{
    const b=event.target.closest('button');
    if(b?.dataset.inspectOutput){outputId=b.dataset.inspectOutput;outputPinned=true;paintOutput();}
    if(b?.id==='inspection-review-link')$("result-review-section").scrollIntoView({behavior:'smooth',block:'start'});
  });

  $("inspection-follow-live").addEventListener('click',()=>window.dispatchEvent(new CustomEvent('aoa-follow-live')));
  $("inspection-refresh-case").addEventListener('click',async()=>{
    if(!traceId)return;
    const id=traceId;const button=$("inspection-refresh-case");button.disabled=true;
    try {
      const response=await fetch('/api/course-traces/'+encodeURIComponent(id));
      if(!response.ok)throw new Error('Could not refresh this saved case.');
      const body=await response.json();
      if(id===traceId)window.dispatchEvent(new CustomEvent('aoa-course-replay',{detail:body.records}));
    } catch(error){$("inspection-evidence-status").textContent=error.message;}
    finally{button.disabled=false;}
  });

  return {
    showCard(value) { if(card?.id!==value.id){cardReadable.dataset.rendered="";cardReadable.replaceChildren();}card=value;$("card-copy-status").textContent="";paintCard(); },
    clearCard() { card=null;paintCard(); },
    renderRun(nextRecords,nextLife,isSaved) {
      const nextId=nextRecords[0]?.trace_id || null;
      if(nextId!==traceId){taskId="";candidateId="";outputId="";taskPinned=false;outputPinned=false;}
      traceId=nextId;records=nextRecords;life=nextLife;saved=isSaved;
      $("inspection-evidence-banner").hidden=!traceId;
      $("inspection-evidence-status").textContent=`${saved?'Saved case · recorded evidence':'Live trace'} · ${traceId||''}${records[0]?.ts?' · '+records[0].ts:''}`;
      $("inspection-evidence-help").textContent=saved ? 'Opening this view does not execute agents. Refresh to fetch newer evidence; review controls still act on this exact result.' : 'Following live events. Inspecting cards and outputs does not execute agents.';
      $("inspection-follow-live").hidden=!saved;$("inspection-refresh-case").hidden=!saved;
      paintSelection();paintOutput();
    },
  };
}
