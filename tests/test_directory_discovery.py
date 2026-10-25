import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import sys

import httpx
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'system/services/planner'))
from directory_contract import bind_records
spec = importlib.util.spec_from_file_location('directory_lab_test', ROOT / 'scripts/directory-lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def estate():
    cards = []
    paths = list((ROOT / 'system/agents').glob('*/capabilities/*/capability-card.yaml'))
    paths.append(ROOT / 'system/agents-eve/runtime/templates/interviewer-questions.yaml')
    for path in paths:
        card = yaml.safe_load(path.read_text())
        card.update(lifecycle={'status': 'approved'}, a2a_endpoint='http://fixture/a2a', agent_card_url='http://fixture/card')
        cards.append(card)
    return cards


def record(card):
    a2a = {'url': card['a2a_endpoint'], 'protocolVersion': '0.3.0', 'skills': [{'id': card['id']}]}
    return {'cid': 'cid-' + card['id'], 'record': lab.export_record(card, a2a)}


def test_every_course_au_exports_real_a2a_module():
    for card in estate():
        item = record(card)
        assert item['record']['modules'][0]['data']['card_data']['skills'][0]['id'] == card['id']
        bound, evidence = bind_records([item], [card])
        assert bound[0]['discovery_evidence']['cid'] == item['cid']
        assert not evidence['missing_current_publication']


@pytest.mark.parametrize('change', ['contract', 'endpoint', 'lifecycle', 'module', 'unadopted'])
def test_directory_record_cannot_override_local_adoption(change):
    local = estate()[0]
    item = record(local)
    if change == 'contract': local['purpose'] = 'different work'
    if change == 'endpoint': local['a2a_endpoint'] = 'http://changed/a2a'
    if change == 'lifecycle': local['lifecycle']['status'] = 'suspended'
    if change == 'module': item['record']['modules'][0]['data']['card_data']['url'] = 'http://unapproved/a2a'
    bound, evidence = bind_records([item], [] if change == 'unadopted' else [local])
    assert not bound and evidence['excluded']


def test_old_revisions_and_local_tools_do_not_become_au_candidates():
    local = estate()[0]
    old = record(local)
    local['purpose'] = 'updated declared responsibility'
    current = record(local)
    tool = {'id': 'tool-document-text', 'kind': 'tool'}
    cards, evidence = bind_records([old, current], [local, tool])
    assert cards[-1] == tool and len(cards) == 2
    assert len(evidence['excluded']) == 1 and len(evidence['accepted']) == 1


@pytest.mark.parametrize('failure', [None, 'unavailable', 'missing-eve', 'stale-eve'])
def test_planner_uses_directory_for_eve_and_never_falls_back(monkeypatch, failure):
    import planner
    from fastapi import HTTPException
    cards = estate()
    records = [record(card) for card in cards]
    if failure == 'missing-eve': records = [row for row in records if row['record']['name'] != 'aoa-course/interviewer-questions']
    if failure == 'stale-eve':
        next(row for row in records if row['record']['name'] == 'aoa-course/interviewer-questions')['record']['annotations']['aoa/binding-sha256'] = 'stale'
    events, invocations, requests = [], [], []
    async def listing(client): return cards
    async def log(event): events.append(event)
    async def build(workflow, *args): return planner.PlanBuildResult(tasks=copy.deepcopy(workflow.tasks), source='test-course-plan')
    async def choice(task, reference, candidates, *args):
        assert reference['discovery_evidence']['source'] == 'agntcy-directory'
        return reference, {'task': task.id, 'outcome': 'single-eligible-capability'}
    async def execute(prepared):
        invocations.extend(prepared.resolved_steps)
        return {'questions': ['synthetic boundary test']}
    async def governance(*args): return {'decision': 'proceed'}
    def handler(request):
        requests.append(str(request.url))
        assert request.url.path == '/records'
        return httpx.Response(503 if failure == 'unavailable' else 200, json={'records': records})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(planner.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(planner, 'DISCOVERY_BACKEND', 'agntcy')
    monkeypatch.setattr(planner, 'ALLOCATION_MODE', 'decision')
    monkeypatch.setattr(planner, '_registry_list', listing)
    monkeypatch.setattr(planner, '_record', log)
    monkeypatch.setattr(planner, '_build_plan', build)
    monkeypatch.setattr(planner, 'allocate', choice)
    monkeypatch.setattr(planner, '_evaluate_prepared_plan', governance)
    monkeypatch.setattr(planner, '_execute_prepared_run', execute)
    call = planner._run_workflow(planner.WORKFLOWS['cv-fit-interview'], {'kind': 'cv-fit-interview', 'inputs': {'cv_path': '/cv', 'jd_path': '/jd'}})
    if failure:
        with pytest.raises(HTTPException) as exc: asyncio.run(call)
        assert exc.value.status_code == 503 and not invocations
    else:
        asyncio.run(call)
        assert invocations[-1].capability == 'interviewer-questions'
        assert invocations[-1].card['discovery_evidence']['cid'] == 'cid-interviewer-questions'
        assert any(event['step'] == 'directory-discovery' for event in events)
        assert all(event['source'] == 'agntcy-directory' for event in events if event['step'] == 'discover')
    assert len(requests) == 1
