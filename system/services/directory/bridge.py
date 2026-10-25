"""Course adapter: publish adopted AUs, read candidates from the real AGNTCY CLI.

This is integration code, not an AGNTCY service. No model keys or authority to
adopt external agents. Discovery only returns records actually pulled from DIR.
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import urllib.request

from fastapi import FastAPI, HTTPException
import uvicorn

spec = importlib.util.spec_from_file_location('directory_lab', Path(__file__).with_name('directory-lab.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
REGISTRY = os.getenv('COURSE_REGISTRY_URL', 'http://registry:7100').rstrip('/')
DIRECTORY = os.getenv('COURSE_DIRECTORY_ADDR', 'agntcy-directory:8890')
lock = threading.Lock()
published = {}
status = {'published': [], 'errors': [], 'ready': False}


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def cli(*args):
    result = subprocess.run([str(lab.CLI), '--server-addr', DIRECTORY, '--auth-mode', 'insecure', *args],
                            capture_output=True, text=True, timeout=30, check=True)
    return result.stdout.strip()


def records():
    cids = []
    for offset in range(0, 10000, 100):
        batch = json.loads(cli('search', '--name', 'aoa-course/*', '--output', 'json',
                               '--limit', '100', '--offset', str(offset)))
        if not isinstance(batch, list) or not all(isinstance(cid, str) for cid in batch):
            raise ValueError('Unexpected Directory search response')
        cids.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError('Directory exceeds the bounded course search limit')
    # dirctl v1.8.0 search emits a JSON array of content IDs.
    return [{'cid': cid, 'record': json.loads(cli('pull', cid))} for cid in cids]


def sync_once():
    global status
    with lock:
        # A warm publication cache must not report readiness during a DIR outage.
        cli('search', '--name', '__aoa_readiness__', '--output', 'json')
        cards = get_json(REGISTRY + '/list').get('capabilities', [])
        aus = [card for card in cards if card.get('kind') == 'au']
        errors, results, agent_cards = [], [], {}
        existing = None
        for card in aus:
            try:
                url = card['agent_card_url']
                if url not in agent_cards:
                    agent_cards[url] = get_json(url)
                record = lab.export_record(card, agent_cards[url])
                stable = {key: value for key, value in record.items() if key != 'created_at'}
                digest = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()
                cached = published.get(card['id'])
                if not cached or cached['digest'] != digest:
                    # Reuse an identical published record across bridge restarts.
                    if existing is None:
                        existing = records()
                    cid = next((item['cid'] for item in existing if
                                item['record'].get('annotations', {}).get('aoa/publication-sha256') == digest), None)
                    if not cid:
                        record['annotations']['aoa/publication-sha256'] = digest
                        with tempfile.TemporaryDirectory() as folder:
                            path = Path(folder) / 'record.json'
                            path.write_text(json.dumps(record), encoding='utf-8')
                            cid = cli('push', str(path), '--output', 'raw')
                    published[card['id']] = {'digest': digest, 'cid': cid}
                results.append({'capability': card['id'], 'cid': published[card['id']]['cid']})
            except Exception as exc:
                detail = exc.stderr.strip()[-1500:] if isinstance(exc, subprocess.CalledProcessError) else str(exc)
                errors.append({'capability': card['id'], 'error': type(exc).__name__, 'detail': detail})
        expected = set(os.getenv('COURSE_DIRECTORY_EXPECTED_AUS', '').split(',')) - {''}
        missing = sorted(expected - {row['capability'] for row in results})
        status = {'published': results, 'errors': errors, 'missing': missing,
                  'ready': bool(aus) and not errors and not missing}
        return status


async def publisher():
    global status
    while True:
        try:
            await asyncio.to_thread(sync_once)
        except Exception as exc:
            logging.warning('Directory publication unavailable: %s', type(exc).__name__)
            status = {**status, 'ready': False, 'errors': [{'error': type(exc).__name__}]}
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(publisher())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get('/healthz')
def health():
    return {'status': 'ok', 'role': 'course-directory-adapter', **status}


@app.post('/sync')
def sync(wait: int = 0):
    deadline = time.monotonic() + min(max(wait, 0), 120)
    while True:
        try:
            result = sync_once()
            if result['ready']:
                indexed = {item['cid'] for item in records()}
                waiting = [row['capability'] for row in result['published'] if row['cid'] not in indexed]
                if waiting:
                    result = {**result, 'ready': False, 'waiting_for_index': waiting}
        except Exception as exc:
            result = {'ready': False, 'error': type(exc).__name__}
        if result['ready']:
            return result
        if time.monotonic() >= deadline:
            raise HTTPException(503, result)
        time.sleep(1)


@app.get('/records')
def discover():
    try:
        return {'source': 'agntcy-directory', 'query': 'aoa-course/*', 'records': records()}
    except Exception as exc:
        raise HTTPException(503, 'AGNTCY Directory search/pull unavailable; no local discovery fallback') from exc


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8892)
