import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace as NS

import httpx
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'system/services/planner'), str(ROOT/'system/services/decision'), str(ROOT/'system/agents')]
from decision import decide, normalise_answer, validate_request
from allocation import allocate, eligibility, validate_composition
from case_store import CaseStore, CaseConflict, result_digest
from _base.decisions import promote


def run(coro):
    return asyncio.run(coro)


def card(identifier='evaluator-cv'):
    base = yaml.safe_load((ROOT/'system/agents/evaluator/capabilities/cv/capability-card.yaml').read_text())
    return {**base, 'id': identifier, 'lifecycle': {'status': 'approved'}}


def test_explicit_choice_survives_rounded_tie():
    answer = normalise_answer({'choice': 'b', 'probabilities': {'a': .5, 'b': .5}}, {'a': '', 'b': ''}, probabilities_required=True)
    assert answer['choice'] == 'b'


@pytest.mark.parametrize('answer', [
    {'choice': 'outside', 'probabilities': {'a': .5, 'b': .5}},
    {'choice': 'b', 'probabilities': {'a': .9, 'b': .1}},
    {'choice': 'a', 'probabilities': {'a': float('nan'), 'b': 0}},
    {'choice': 'a', 'probabilities': {'a': 1}},
])
def test_invalid_decisions_rejected(answer):
    with pytest.raises(ValueError):
        normalise_answer(answer, {'a': '', 'b': ''}, probabilities_required=True)


def test_local_does_not_invent_probability():
    answer = normalise_answer({'choice': 'a', 'probabilities': {'a': .99, 'b': .01}}, {'a': '', 'b': ''}, probabilities_required=False)
    assert answer['winner_probability'] is None


def test_typesafe_wire_contract(monkeypatch):
    monkeypatch.setenv('DECISION_PROVIDER', 'typesafe'); monkeypatch.setenv('TYPESAFE_API_KEY', 'unit-test-placeholder')
    monkeypatch.setenv('DECISION_MODEL', 'jev-1.13.0')
    def handler(request):
        body = json.loads(request.content)
        assert body['questions']['decision']['type'] == 'choice'
        assert body['model'] == 'jev-1.13.0'
        return httpx.Response(200, json={'answers': {'decision': {'choice': 'b', 'probabilities': {'a': .1, 'b': .9}}}, 'usage': {'input_tokens': 100}})
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            answer = await decide({'state': {}, 'instructions': 'Select', 'criteria': {'a': 'A', 'b': 'B'}}, client)
            assert answer['choice'] == 'b' and answer['estimated_cost_usd'] > 0
    run(exercise())


def test_contract_eligibility():
    ref = card(); good = card('specialist')
    assert not eligibility(good, ref)
    bad = copy.deepcopy(good); bad['outputs'][0]['type'] = 'string'
    assert eligibility(bad, ref)
    bad = copy.deepcopy(good); bad['inputs'].append({'name': 'secret', 'type': 'string', 'required': True})
    assert eligibility(bad, ref)
    bad = copy.deepcopy(good); bad['lifecycle']['status'] = 'pending'
    assert eligibility(bad, ref)


def test_allocator_chooses_real_alternative_and_holds_uncertainty(monkeypatch):
    monkeypatch.setenv('DECISION_ALLOW_UNSCORED', 'false')
    ref, alt = card(), card('specialist')
    task = NS(id='evaluate-cv-fit', purpose='Assess data engineering')
    async def exercise(prob):
        def handler(request):
            assert set(json.loads(request.content)['criteria']) == {'evaluator-cv', 'specialist', 'no_suitable_capability'}
            return httpx.Response(200, json={'choice': 'specialist', 'winner_probability': prob})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await allocate(task, ref, [ref, alt], {}, client)
    selected, evidence = run(exercise(.9)); assert selected['id'] == 'specialist'
    selected, evidence = run(exercise(.4)); assert selected is None and evidence['outcome'] == 'selection-held'


def test_single_eligible_does_not_call_model():
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail('unexpected model call'))) as client:
            return await allocate(NS(id='task'), card(), [card()], {}, client)
    selected, evidence = run(exercise()); assert selected and not evidence['model_called']


def test_final_composition_rejects_wrong_business_edge_and_missing_task(monkeypatch):
    monkeypatch.setenv('DURABLE_CASES', 'false')
    import planner
    workflow = planner.WORKFLOWS['cv-fit']
    cards = {}
    for path in (ROOT/'system/agents').glob('*/capabilities/*/capability-card.yaml'):
        item = yaml.safe_load(path.read_text()); item['lifecycle']={'status':'approved'}; cards[item['id']]=item
    steps = [planner.ResolvedStep(copy.deepcopy(task), planner._deterministic_capability_for_task(task), cards[planner._deterministic_capability_for_task(task)]) for task in workflow.tasks]
    inputs={'cv_path':'/data/cv.txt','jd_path':'/data/jd.txt'}
    assert validate_composition(steps, workflow, cards, planner._deterministic_capability_for_task, inputs)['valid']
    with pytest.raises(ValueError, match='responsibility'):
        validate_composition(steps[:-1], workflow, cards, planner._deterministic_capability_for_task, inputs)
    steps[-1].task.input_map['evaluation']='parse-cv.outputs'
    with pytest.raises(ValueError, match='business evidence'):
        validate_composition(steps, workflow, cards, planner._deterministic_capability_for_task, inputs)


def held_case():
    outputs={'report':'Málaga – exact result'}
    return {'trace_id':'held123', 'workflow':'cv-fit','status':'draft-held','plan_digest':'plan1','draft_outputs':outputs,'result_digest':result_digest('plan1',outputs),'review':None}


def test_restart_and_idempotent_review(tmp_path):
    db=tmp_path/'cases.sqlite3'; case=held_case(); store=CaseStore(db)
    store.record_many([{'trace_id':case['trace_id'],'step':'result-draft'}, {'trace_id':case['trace_id'],'step':'result-hold'}],case)
    store=CaseStore(db); assert store.get('held123')['draft_outputs']==case['draft_outputs']
    args=('held123','approve',case['result_digest'],'Checked the exact result','reviewer','today')
    released,events=store.review(*args); assert len(events)==3 and released['status']=='released'
    assert CaseStore(db).review(*args)[1]==[]
    assert len(store.events('held123'))==5
    with pytest.raises(CaseConflict): store.review('held123','reject',case['result_digest'],'Changed mind','reviewer','later')


def test_wrong_digest_and_changed_payload_cannot_release(tmp_path):
    store=CaseStore(tmp_path/'cases.sqlite3'); case=held_case();store.record({'trace_id':'held123','step':'hold'},case)
    with pytest.raises(CaseConflict): store.review('held123','approve','wrong','Reviewed','reviewer','now')
    case['draft_outputs']['report']='changed';store.record({'trace_id':'held123','step':'tamper-test'},case)
    with pytest.raises(CaseConflict): store.review('held123','approve',case['result_digest'],'Reviewed','reviewer','now')


def test_review_transaction_rolls_back_on_event_failure(tmp_path):
    store=CaseStore(tmp_path/'cases.sqlite3');case=held_case();store.record({'trace_id':'held123','step':'hold'},case)
    with store.connect() as db:
        db.execute("CREATE TRIGGER fail_review BEFORE INSERT ON events WHEN NEW.body LIKE '%result-release%' BEGIN SELECT RAISE(ABORT, 'failure'); END")
    with pytest.raises(sqlite3.IntegrityError): store.review('held123','approve',case['result_digest'],'Reviewed','reviewer','now')
    assert store.get('held123')['status']=='draft-held' and len(store.events('held123'))==1


@pytest.mark.parametrize('choice,prob,passages,expected', [('promote',.9,True,'promote'),('reject',.9,True,'reject'),('promote',.4,True,'review'),('promote',.9,False,'review')])
def test_wiki_decision_preserves_source_and_gates_publication(choice,prob,passages,expected):
    note={'title':'Architecture','summary':'Summary','passages':[{'passage_id':'p1','quote':'Original exact quote.'}] if passages else []}
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'choice':choice,'winner_probability':prob}))) as client:
            return await promote(note,'note.txt','AOA rubric',client)
    result=run(exercise())['outputs']['promotion'];assert result['decision_outcome']==expected
    assert result['promote']==(expected=='promote')
    if result['promote']:assert result['promoted_passages'][0]['quote']==note['passages'][0]['quote']


def test_directory_discovery_does_not_approve_execution():
    spec=importlib.util.spec_from_file_location('directory_lab',ROOT/'scripts/directory-lab.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    local=card('interviewer-questions');record=module.export_record(local)
    result=module.compare(record,local);assert result['locally_eligible'] and not result['execution_authorised']
    local['purpose']='A different job';assert not module.compare(record,local)['locally_eligible']


def test_invalid_whole_plan_never_reaches_execution(monkeypatch):
    import planner
    from fastapi import HTTPException
    workflow = planner.WORKFLOWS['cv-fit']
    cards = []
    for path in (ROOT/'system/agents').glob('*/capabilities/*/capability-card.yaml'):
        item=yaml.safe_load(path.read_text());item['lifecycle']={'status':'approved'};cards.append(item)
    async def listing(client):return cards
    async def build(*args):return planner.PlanBuildResult(tasks=copy.deepcopy(workflow.tasks[:-1]),source='test-proposal')
    async def record(event):pass
    async def execution(run):pytest.fail('invalid composition reached execution')
    async def selection(task,reference,*args):return reference,{'task':task.id,'outcome':'test-selection'}
    monkeypatch.setattr(planner,'ALLOCATION_MODE','decision')
    monkeypatch.setattr(planner,'_registry_list',listing)
    monkeypatch.setattr(planner,'_build_plan',build)
    monkeypatch.setattr(planner,'_record',record)
    monkeypatch.setattr(planner,'_execute_prepared_run',execution)
    monkeypatch.setattr(planner,'allocate',selection)
    with pytest.raises(HTTPException) as error:
        run(planner._run_workflow(workflow,{'kind':'cv-fit','inputs':{'cv_path':'/cv.txt','jd_path':'/jd.txt'}}))
    assert error.value.status_code==409


def test_concurrent_identical_reviews_emit_one_release(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    store=CaseStore(tmp_path/'cases.sqlite3');case=held_case();store.record({'trace_id':'held123','step':'hold'},case)
    def review(_):return store.review('held123','approve',case['result_digest'],'Checked','reviewer','now')
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(review,range(4)))
    assert all(result[0]['status']=='released' for result in results)
    assert sum(event['step']=='result-release' for event in store.events('held123'))==1
