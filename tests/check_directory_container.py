"""Real Directory round trip and restart, with an isolated real course registry.

Requires Docker. Uses no model keys or learner data. Linux CI runs amd64;
the same check can run on an Apple Silicon teaching laptop.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='aoa directory check ') as folder:
        temp = Path(folder)
        data = temp / 'data'
        data.mkdir()
        env = {**os.environ, 'COMPOSE_PROJECT_NAME': f'aoa-directory-check-{os.getpid()}',
               'COURSE_DIRECTORY_DATA_ROOT': str(data), 'COURSE_DIRECTORY_PORT': '18890', 'COURSE_DIRECTORY_UI_PORT': '18891',
               'DIRECTORY_UID': str(os.getuid()), 'DIRECTORY_GID': str(os.getgid())}
        # This separate registry has no published host port or learner volume.
        fixture = temp / 'registry.yml'
        agent = temp / 'agent'
        agent.mkdir()
        (agent / 'agent-card.json').write_text(json.dumps({
            'protocolVersion': '0.3.0', 'name': 'synthetic-course-au', 'description': 'Synthetic integration fixture',
            'url': 'http://agent-fixture:8888/a2a', 'version': '0.1.0',
            'capabilities': {'streaming': False}, 'defaultInputModes': ['application/json'],
            'defaultOutputModes': ['application/json'],
            'skills': [{'id': name, 'name': name, 'description': 'Synthetic integration fixture', 'tags': ['test']}
                       for name in ('interviewer-questions', 'evaluator-test')]}))
        fixture.write_text(json.dumps({'services': {'registry': {
            'build': {'context': str(ROOT / 'system/services/registry')},
            'environment': {'REGISTRY_DATA_DIR': '/data'},
            'tmpfs': ['/data'],
            'healthcheck': {'test': ['CMD', 'python', '-c',
                "import urllib.request; urllib.request.urlopen('http://localhost:7100/healthz',timeout=2)"],
                'interval': '2s', 'timeout': '3s', 'retries': 30}},
            'agent-fixture': {'image': 'python:3.12-slim', 'command': ['python', '-m', 'http.server', '8888', '--directory', '/fixture'],
                              'volumes': [str(agent) + ':/fixture:ro']},
            'directory-bridge': {'ports': ['127.0.0.1:18892:8892']}}}))
        compose = ['docker', 'compose', '-f', str(ROOT / 'system/docker-compose.directory.yml'), '-f', str(fixture)]

        def run(args, timeout=300):
            result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            if result.returncode:
                raise RuntimeError(f'{args}\n{result.stdout}\n{result.stderr}')
            return result.stdout

        def lab(*args):
            return run(['bash', str(ROOT / 'scripts/directory.sh'), *args])

        try:
            run([*compose, 'up', '--build', '-d', '--wait', 'registry'])
            lab('up')
            print('Real Directory daemon and isolated course registry are healthy.', flush=True)
            with urllib.request.urlopen('http://127.0.0.1:18891/', timeout=10) as response:
                page = response.read().decode()
                assert response.status == 200 and '<html' in page.lower(), page[:500]
            # Register a synthetic contract using the real registry endpoint.
            register = """
import json,urllib.request,yaml
card=yaml.safe_load(open('/course-templates/interviewer-questions.yaml'))
card['endpoint']='http://fixture.invalid/invoke'
card['a2a_endpoint']='http://agent-fixture:8888/a2a'
card['agent_card_url']='http://agent-fixture:8888/agent-card.json'
request=urllib.request.Request('http://registry:7100/register',data=json.dumps(card).encode(),headers={'Content-Type':'application/json'})
urllib.request.urlopen(request,timeout=10).read()
"""
            run([*compose, 'exec', '-T', 'agntcy-directory', 'python', '-c', register])
            lab('export', 'interviewer-questions', '--out', 'record with spaces.json')
            lab('push', 'record with spaces.json', '--out', 'record.cid')
            cid = (data / 'record.cid').read_text().strip()
            assert cid and '\n' not in cid, cid
            lab('pull', '--cid-file', 'record.cid', '--out', 'retrieved.json')
            record = json.loads((data / 'retrieved.json').read_text())
            assert record['name'] == 'aoa-course/interviewer-questions'
            for _ in range(30):
                result = lab('search', 'aoa-course/*')
                if cid in result or 'aoa-course/interviewer-questions' in result:
                    break
                time.sleep(1)
            else:
                raise AssertionError('Published record never appeared in search')
            checked = json.loads(lab('check', 'retrieved.json'))
            assert checked['matching_local_contract'] and checked['local_lifecycle_approved'], checked
            assert not checked['execution_authorised'] and not checked['identity_verified_by_directory_record'], checked
            record['annotations']['aoa/contract-sha256'] = '0' * 64
            (data / 'mismatch.json').write_text(json.dumps(record))
            mismatch = json.loads(lab('check', 'mismatch.json'))
            assert not mismatch['locally_eligible'] and not mismatch['execution_authorised'], mismatch
            # Failed operations must not overwrite a previous successful output.
            sentinel = data / 'keep.json'
            sentinel.write_text('keep existing output')
            failure = subprocess.run(['bash', str(ROOT / 'scripts/directory.sh'), 'pull', 'invalid-cid', '--out', 'keep.json'],
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            assert failure.returncode != 0 and sentinel.read_text() == 'keep existing output'
            run([*compose, '--profile', 'directory', 'up', '-d', '--wait', 'agent-fixture', 'directory-bridge'])
            sync = json.loads(lab('sync', '--wait', '30'))
            assert sync['ready'] and sync['published'][0]['capability'] == 'interviewer-questions', sync
            published_cid = sync['published'][0]['cid']
            # Publication is idempotent and visible in the actual upstream catalogue.
            assert json.loads(lab('sync'))['published'][0]['cid'] == published_cid
            for _ in range(30):
                with urllib.request.urlopen('http://127.0.0.1:18892/records', timeout=30) as response:
                    discovered = json.load(response)['records']
                if any(item['cid'] == published_cid for item in discovered):
                    break
                time.sleep(1)
            else:
                raise AssertionError('Bridge did not discover its published A2A record')
            published = next(item['record'] for item in discovered if item['cid'] == published_cid)
            assert published['modules'][0]['data']['card_data']['url'] == 'http://agent-fixture:8888/a2a'
            with urllib.request.urlopen('http://127.0.0.1:18891/v1/agents', timeout=10) as response:
                assert 'aoa-course/interviewer-questions' in response.read().decode()
            lab('stop')
            try:
                urllib.request.urlopen('http://127.0.0.1:18892/records', timeout=40)
                raise AssertionError('Discovery silently succeeded while Directory was stopped')
            except urllib.error.HTTPError as error:
                assert error.code == 503
            lab('up')
            lab('pull', '--cid-file', 'record.cid', '--out', 'after-restart.json')
            assert json.loads((data / 'after-restart.json').read_text()) == json.loads((data / 'retrieved.json').read_text())
            print('PASS: publication, catalogue, discovery bridge, no fallback, contract checks and restart recovery.', flush=True)
        finally:
            subprocess.run([*compose, '--profile', 'directory', 'down', '--remove-orphans'], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=60)


if __name__ == '__main__':
    main()
