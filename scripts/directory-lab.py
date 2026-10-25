#!/usr/bin/env python3
"""Real local AGNTCY Directory; discovery never mutates AOA acceptance state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CLI = Path(os.getenv('COURSE_DIRECTORY_CLI', str(ROOT / '.course-tools/dirctl-1.8.0')))
sys.path.insert(0, str(ROOT / 'system/services/planner'))
from directory_contract import fingerprint, binding_fingerprint


def registry_card(identifier):
    from urllib.parse import urlencode
    url = os.getenv('COURSE_REGISTRY_URL', 'http://localhost:7100') + '/find?' + urlencode({'id': identifier})
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def export_record(card, agent_card=None):
    # Verified against the pinned OASF v1.0.0 taxonomy; not a performance claim.
    if card['id'] == 'interviewer-questions':
        skill = {'id': 10205, 'name': 'natural_language_processing/natural_language_generation/question_generation'}
    elif card['id'].startswith('parser-'):
        skill = {'id': 10301, 'name': 'natural_language_processing/information_retrieval_synthesis/fact_extraction'}
    else:
        # Other AUs retain their precise purpose and A2A skills. Do not invent
        # an OASF taxonomy equivalence for an unreviewed course capability.
        skill = None
    modules = []
    if agent_card is not None:
        if agent_card.get('url') != card.get('a2a_endpoint') or not any(
            skill.get('id') == card['id'] for skill in agent_card.get('skills', [])
        ):
            raise ValueError('The live A2A Agent Card does not match the local AU binding')
        modules = [{'name': 'integration/a2a', 'data': {
            'card_schema_version': agent_card['protocolVersion'], 'card_data': agent_card}}]
    return {
        'schema_version': '1.0.0', 'name': 'aoa-course/' + card['id'],
        'version': card.get('version', '0.1.0'), 'authors': ['AOA course workshop'],
        'description': card['purpose'].strip(),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'skills': [skill] if skill else [], 'domains': [], 'modules': modules,
        'annotations': {'aoa/capability-id': card['id'], 'aoa/contract-sha256': fingerprint(card),
                        'aoa/binding-sha256': binding_fingerprint(card),
                        'aoa/taxonomy-mapping': 'reviewed' if skill else 'not-yet-mapped',
                        'aoa/acceptance': 'Directory discovery is not local execution approval.'},
    }


def compare(record, local):
    annotations = record.get('annotations', {})
    same = fingerprint(local) == annotations.get('aoa/contract-sha256')
    approved = (local.get('lifecycle') or {}).get('status') == 'approved'
    return {'capability': annotations.get('aoa/capability-id'), 'matching_local_contract': same,
            'local_lifecycle_approved': approved, 'locally_eligible': same and approved,
            'execution_authorised': False,
            'next_boundary': 'Planner eligibility, task fit, composition validation and use-context governance still apply.',
            'identity_verified_by_directory_record': False}


def emit(text, output=None):
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.rstrip() + '\n', encoding='utf-8')
    else:
        print(text.rstrip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ex = sub.add_parser('export'); ex.add_argument('capability'); ex.add_argument('--card', help='Unadopted workshop YAML card, using PyYAML')
    sub.add_parser('start')
    sync = sub.add_parser('sync', help='Publish the current adopted AU estate through the course Directory bridge')
    sync.add_argument('--wait', type=int, default=0, help='Wait up to this many seconds for all active AUs')
    push = sub.add_parser('push'); push.add_argument('record')
    pull = sub.add_parser('pull'); pull.add_argument('cid', nargs='?'); pull.add_argument('--cid-file')
    search = sub.add_parser('search'); search.add_argument('name', nargs='?', default='aoa-course/*')
    check = sub.add_parser('check'); check.add_argument('record')
    for command in (ex, push, pull, search, check):
        command.add_argument('--out', help='Write output as UTF-8; paths are inside .course-data when using Docker')
    args = parser.parse_args()
    if args.command == 'sync':
        url = os.getenv('COURSE_DIRECTORY_BRIDGE_URL', 'http://directory-bridge:8892') + '/sync?wait=' + str(args.wait)
        request = urllib.request.Request(url, data=b'', method='POST')
        with urllib.request.urlopen(request, timeout=max(30, args.wait + 10)) as response:
            print(json.dumps(json.load(response), indent=2))
        return
    if args.command == 'pull':
        if bool(args.cid) == bool(args.cid_file):
            parser.error('Provide a CID or --cid-file, but not both')
        if args.cid_file:
            args.cid = Path(args.cid_file).read_text(encoding='utf-8-sig').strip()
        if not args.cid:
            parser.error('CID file is empty')
    if args.command == 'export':
        if args.card:
            import yaml
            card = yaml.safe_load(Path(args.card).read_text())
            if card['id'] != args.capability:
                parser.error('Card ID differs from requested capability')
        else:
            card = registry_card(args.capability)
        emit(json.dumps(export_record(card), indent=2), args.out); return
    if args.command == 'check':
        record = json.loads(Path(args.record).read_text())
        try:
            local = registry_card(record['annotations']['aoa/capability-id'])
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            emit(json.dumps({'locally_eligible': False, 'reason': 'Not adopted into the local AOA registry', 'execution_authorised': False}, indent=2), args.out); return
        emit(json.dumps(compare(record, local), indent=2), args.out); return
    if not CLI.exists():
        parser.error('Run scripts/directory-install.sh first')
    if args.command == 'start':
        os.environ['DIRECTORY_DAEMON_SERVER_LISTEN_ADDRESS'] = '127.0.0.1:8890'
        os.execv(str(CLI), [str(CLI), 'daemon', 'start', '--data-dir', str(ROOT / '.course-data/directory')])
    extra = {'push': ['push', getattr(args, 'record', ''), '--output', 'raw'],
             'pull': ['pull', getattr(args, 'cid', '')],
             'search': ['search', '--name', getattr(args, 'name', ''), '--output', 'json']}[args.command]
    command = [str(CLI), '--server-addr', os.getenv('COURSE_DIRECTORY_ADDR', '127.0.0.1:8890'), '--auth-mode', 'insecure', *extra]
    if args.out:
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
        emit(result.stdout, args.out)
    else:
        subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
