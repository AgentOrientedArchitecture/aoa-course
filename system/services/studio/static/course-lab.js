/* Plan, decision and saved-case inspection for the course. */
(() => {
  const host = document.createElement("section");
  host.className = "lifecycle-section course-inspector";
  host.innerHTML = `<div class="section-head"><span class="section-label">Plan and decisions</span><button type="button" id="course-saved">Open a saved case</button></div>
    <p class="course-help">Inspect the proposed work, eligible AUs and the accepted bindings. A model choice becomes executable only after the whole plan passes validation.</p>
    <div id="course-diagram" class="course-diagram">Run a workflow to see its recorded plan.</div>
    <details class="course-raw-allocations"><summary>Full allocation and promotion evidence</summary><div id="course-decisions"></div></details><div id="course-cases"></div>`;
  document.getElementById("allocation-inspector").after(host);
  // Session 4 uses one CV evaluator so the exercise can focus on governance.
  const workflows = window.STUDIO_CONFIG?.workflows || [];
  const governanceSession = workflows.includes("agent-card-check") && workflows.includes("flow-audit");
  if (!governanceSession) {
    const brief = document.createElement("label");
    brief.className = "drop-field";
    brief.innerHTML = `<span class="drop-label"><strong>Assessment emphasis</strong></span><textarea id="allocation-brief" rows="2" placeholder="For example: assess production data pipelines and data reliability, or frontend accessibility and design systems."></textarea><small>The planner uses this brief to choose among compatible assessment AUs. Candidate descriptions are declarations; the exercise measures their results.</small>`;
    document.querySelector('[data-mode-panel="cv-fit"]').append(brief);
  }

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  let active = null, records = [];
  window.addEventListener("aoa-course-reset", () => {
    active = null; records = [];
    document.getElementById("course-diagram").textContent = "No recorded plan in this case.";
    document.getElementById("course-decisions").replaceChildren();
  });
  window.addEventListener("aoa-course-record", ({detail: record}) => {
    if (record.step === "start") { active = record.trace_id; records = []; }
    if (record.trace_id !== active) return;
    records.push(record);
    render();
  });

  function render() {
    const plan = records.find(record => record.step === "plan")?.plan;
    const breakdown = records.find(record => record.step === "breakdown")?.tasks || [];
    const steps = plan || breakdown.map(task => ({task:task.id, capability:task.selected_capability || "unbound", input_map:task.input_map}));
    const allocations = records.filter(record => record.step === "allocation");
    const accepted = new Map(records.filter(record => record.step === "allocation-accepted").map(record => [record.task, record.accepted_choice]));
    const complete = new Set(records.filter(record => record.step === "response" && !record.outputs?.error && !record.signals?.exception).map(record => record.task));
    if (steps.length) {
      const width = Math.max(660, steps.length * 230);
      const aliases = new Map(steps.map(step => [step.capability, step.task]));
      const indices = new Map(steps.map((step,index)=>[step.task,index]));
      let svg = `<svg viewBox="0 0 ${width} 180" role="img" aria-label="Recorded task plan and evidence dependencies"><defs><marker id="course-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#517568"/></marker></defs>`;
      steps.forEach((step,index) => {
        const sources = new Set(Object.values(step.input_map || {}).map(path => {const id=path.split('.')[0];return aliases.get(id)||id;}).filter(id=>indices.has(id)));
        for (const source of sources) {
          const from=indices.get(source), x1=from*230+218, x2=index*230+12;
          const path=index-from===1 ? `M${x1} 76 L${x2} 76` : `M${x1} 76 C${x1+20} 12,${x2-20} 12,${x2} 76`;
          svg+=`<path d="${path}" fill="none" stroke="#517568" stroke-width="2" marker-end="url(#course-arrow)"/>`;
        }
      });
      steps.forEach((step,index) => {
        const x=index*230+12, status=complete.has(step.task)?"Output recorded":accepted.has(step.task)?"Binding accepted":plan?"Resolved binding":"Proposed work";
        svg+=`<g><rect x="${x}" y="40" width="206" height="90" rx="10" fill="${complete.has(step.task)?'#dceee5':'#f2f5f3'}" stroke="#517568"/><text x="${x+103}" y="66" text-anchor="middle" font-size="14" font-weight="600">${esc(step.task.replaceAll('-',' '))}</text><text x="${x+103}" y="91" text-anchor="middle" font-size="11">${esc(step.capability)}</text><text x="${x+103}" y="114" text-anchor="middle" font-size="11">${esc(status)}</text></g>`;
      });
      document.getElementById("course-diagram").innerHTML=svg+"</svg>";
    }
    let content=allocations.map(record=>{
      const decision=record.decision, candidates=record.candidates || [];
      const eligibleCount = candidates.filter(candidate => candidate.eligible).length;
      const noModelReason = eligibleCount === 0 ? 'No eligible capability; no decision-model call.' : eligibleCount === 1 ? 'Only one eligible capability; no decision-model call.' : 'No decision-model call recorded; inspect the allocation outcome.';
      return `<details class="course-decision" ${record.model_called?'open':''}><summary>${esc(record.task.replaceAll('-',' '))} · ${record.model_called?'model selection':'contract selection'}</summary>
        <p>${record.model_called?`${esc(decision?.provider || 'provider not recorded')} / ${esc(decision?.model || 'model not recorded')} · ${Number.isFinite(decision?.latency_seconds) ? decision.latency_seconds.toFixed(2)+' s' : 'Latency not recorded'} · ${decision?.winner_probability==null?'No probability estimate':`Model probability ${(decision?.winner_probability*100).toFixed(1)}%`}`:noModelReason}</p>
        <div class="course-table-scroll"><table><thead><tr><th>Eligible AU</th><th>Declared purpose</th><th>Model probability</th></tr></thead><tbody>${candidates.filter(c=>c.eligible).map(c=>`<tr><td>${esc(c.id)}</td><td>${esc(c.purpose)}</td><td>${decision?.probabilities?.[c.id]==null?'—':`${(decision.probabilities[c.id]*100).toFixed(1)}%`}</td></tr>`).join('')}</tbody></table></div>
        ${decision?.probabilities?.no_suitable_capability==null?'':`<p>No suitable capability: ${(decision.probabilities.no_suitable_capability*100).toFixed(1)}%. Model probability is not a guarantee of correctness.</p>`}
        <p>Returned choice: <strong>${esc(record.choice||'none')}</strong>. Accepted binding: <strong>${esc(accepted.get(record.task)||'none')}</strong>.</p>
        <details><summary>Excluded capabilities (${candidates.filter(c=>!c.eligible).length})</summary><ul>${candidates.filter(c=>!c.eligible).map(c=>`<li>${esc(c.id)}: ${esc(c.reasons.join('; '))}</li>`).join('')}</ul></details>
        ${decision?`<details><summary>Decision evidence and usage</summary><pre>${esc(JSON.stringify(decision,null,2))}</pre></details>`:''}</details>`;
    }).join('');
    for (const record of records.filter(r=>r.step==='response' && r.outputs?.promotion?.decision_evidence)) {
      const promotion=record.outputs.promotion;
      content+=`<details class="course-decision" open><summary>Wiki promotion · ${esc(promotion.decision_outcome)}</summary><p>The decision model supplies the judgement. The retained quotes come from the parsed source.</p><p>${esc(promotion.rejection_reason||'Source passages accepted for promotion.')}</p><pre>${esc(JSON.stringify(promotion.decision_evidence,null,2))}</pre></details>`;
    }
    const held=records.find(r=>r.step==='allocation-held');
    if(held)content+=`<p role="status">${esc(held.message || `Selection held: ${held.reason}. No application AU has run.`)}</p>`;
    document.getElementById("course-decisions").innerHTML=content;
  }

  document.getElementById("course-saved").addEventListener("click", async()=>{
    const target=document.getElementById("course-cases");
    try {
      const response=await fetch('/api/saved-cases'); if(!response.ok)throw new Error('Saved cases are unavailable');
      const body=await response.json();
      target.innerHTML=`<p>${body.durable?'Cases are persisted on disk and survive a planner restart.':'Persistence is disabled in this running service; cases are held in memory.'} Opening a case replays evidence without executing it.</p><ul>${body.runs.map(run=>`<li><button type="button" data-case="${esc(run.trace_id)}">${esc(run.workflow)} · ${esc(run.status)} · ${esc(run.trace_id)}</button></li>`).join('')||'<li>No cases yet.</li>'}</ul>`;
      for(const button of target.querySelectorAll('[data-case]'))button.addEventListener('click', async()=>{
        try {
          const response=await fetch('/api/course-traces/'+encodeURIComponent(button.dataset.case));
          if(!response.ok)throw new Error('Could not load saved evidence');
          const body=await response.json();
          window.dispatchEvent(new CustomEvent("aoa-course-replay", {detail:body.records}));
          let notice=target.querySelector('.course-case-status');
          if(!notice){notice=document.createElement('p');notice.className='course-case-status';notice.setAttribute('role','status');target.prepend(notice);}
          notice.textContent='Saved evidence loaded. Exact-result controls are available in Run review when this case has a held draft.';
        } catch(error){target.textContent=error.message;}
      });
    } catch(error){target.textContent=error.message;}
  });
})();
