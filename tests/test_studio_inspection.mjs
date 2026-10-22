import test from 'node:test';
import assert from 'node:assert/strict';
import { cardSections, escapeText, taskIds, allocationEvidence, probabilityLabel,
  runOutputs, recordedInputs, runEvidenceStatus } from '../system/services/studio/static/inspection-model.mjs';

test('readable projection keeps unknown metadata and complete original JSON', () => {
  const card={id:'an-au',purpose:'Decide',inputs:[{name:'case',type:'object',required:true}],outputs:[],constraints:[],evaluation_signals:[],identity:{agent_id:'urn:agent'},extension:{nested:[false,0,null]}};
  const original=structuredClone(card), view=cardSections(card);
  assert.deepEqual(JSON.parse(view.json),original);
  assert.deepEqual(view.metadata.extension,original.extension);
  assert.deepEqual(view.metadata.identity,original.identity);
  assert.deepEqual(card,original);
});
test('partial and tool cards remain inspectable without invented fields',()=>{
  const view=cardSections({id:'tool-x',kind:'tool',provenance:{model:'none'}});
  assert.deepEqual(view.inputs,[]);assert.deepEqual(view.signals,[]);
  assert.equal(JSON.parse(view.json).lifecycle,undefined);
});
test('untrusted card and trace strings are escaped',()=>{
  assert.equal(escapeText('<img onerror="bad()">&\''),'&lt;img onerror=&quot;bad()&quot;&gt;&amp;&#39;');
});
test('task order is deduplicated across proposal, plan and live events',()=>{
  assert.deepEqual(taskIds([{step:'breakdown',tasks:[{id:'parse'},{id:'decide'}]},{step:'plan',plan:[{task:'parse'},{task:'decide'}]},{step:'response',task:'report'}]),['parse','decide','report']);
});
test('choice alone never becomes an accepted binding',()=>{
  const view=allocationEvidence([{step:'allocation',task:'decide',choice:'a',outcome:'proposed'}],'decide');
  assert.equal(view.accepted,undefined);assert.equal(view.validatedBeforeAcceptance,false);
});
test('passing composition check must precede accepted binding',()=>{
  const validation={step:'composition-validation',valid:true};
  const accepted={step:'allocation-accepted',task:'decide',accepted_choice:'a'};
  assert.equal(allocationEvidence([validation,accepted],'decide').validatedBeforeAcceptance,true);
  assert.equal(allocationEvidence([accepted,validation],'decide').validatedBeforeAcceptance,false);
  assert.equal(allocationEvidence([{...validation,valid:false},accepted],'decide').validatedBeforeAcceptance,false);
});
test('abstention and composition rejection preserve absent execution',()=>{
  const records=[{step:'allocation',task:'decide',choice:'no_suitable_capability',model_called:true,outcome:'held',candidates:[]},{step:'allocation-held',task:'decide',reason:'uncertain'},{step:'composition-validation',valid:false,error:'missing required work'}];
  const view=allocationEvidence(records,'decide');
  assert.equal(view.held.reason,'uncertain');assert.equal(view.validation.valid,false);
  assert.equal(view.execution,undefined);assert.equal(view.accepted,undefined);
});
test('probabilities distinguish zero from absent and unscored decisions',()=>{
  assert.equal(probabilityLabel(0),'0.0%');assert.equal(probabilityLabel(1),'100.0%');
  for(const value of [null,undefined,NaN,'0.9'])assert.equal(probabilityLabel(value),'Not reported');
});
test('allocations are task scoped and keep excluded candidates',()=>{
  const view=allocationEvidence([{step:'allocation',task:'parse',choice:'parser'},{step:'allocation',task:'decide',choice:'a',candidates:[{id:'a',eligible:true},{id:'tool',eligible:false,reasons:['not an AU']}]}],'decide');
  assert.equal(view.allocation.choice,'a');assert.equal(view.candidates[1].eligible,false);
});
test('outputs are task scoped and use the latest recorded response',()=>{
  const first={step:'response',task:'parse',outputs:{value:1}},latest={...first,outputs:{value:2}};
  assert.deepEqual(runOutputs([first,{step:'tool-response',task:'parse',outputs:{}},latest]),[latest]);
});
test('input evidence comes from the matching invocation before the output',()=>{
  const out={step:'response',task:'decide',outputs:{verdict:'fit'}};
  const records=[{step:'invoke',task:'other',inputs:{wrong:true}},{step:'invoke',task:'decide',inputs:{cv:{years:4}}},out,{step:'invoke',task:'decide',inputs:{cv:{years:9}}}];
  assert.deepEqual(recordedInputs(records,out),{cv:{years:4}});
  assert.equal(recordedInputs([out],out),null);
});
test('held, quarantined and rejected evidence is never labelled released',()=>{
  assert.match(runEvidenceStatus({status:'draft-held'}),/^Held draft/);
  assert.match(runEvidenceStatus({status:'quarantined'}),/^Quarantined/);
  assert.match(runEvidenceStatus({status:'rejected'}),/^Plan rejected/);
  assert.match(runEvidenceStatus({status:'done'}),/quality still needs review/);
  assert.equal(runEvidenceStatus({status:'released'}),'Released result');
});
