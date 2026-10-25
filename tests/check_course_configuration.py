"""Compare the consolidated course with the preserved, working overlay stack.

Real Compose parsing, both model routes, all four sessions. No containers or
providers are started; fixtures contain dummy keys only.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'archive/configuration-before-consolidation/system'


def config(files, profiles, env, env_file):
    args = ['docker', 'compose', '--project-directory', str(ROOT/'system'), '--env-file', str(env_file)]
    for file in files:
        args += ['-f', str(file)]
    for profile in profiles:
        args += ['--profile', profile]
    return json.loads(subprocess.check_output(args+['config', '--format', 'json'], cwd=ROOT, env=env, text=True))


def normalise(services):
    services = copy.deepcopy(services)
    if 'estate-filesystem' in services:
        service = services.pop('estate-filesystem')
        service['container_name'] = 'aoa-tool-filesystem'
        service['networks'] = {'default': None}
        services['tool-filesystem'] = service
        depends = services['estate-parser']['depends_on']
        depends['tool-filesystem'] = depends.pop('estate-filesystem')
    for service in services.values():
        service.pop('profiles', None)
        env = service.get('environment', {})
        # These explicit current defaults equal the existing application defaults.
        if env.get('PLAN_GOVERNANCE_CAPABILITY') == '': env.pop('PLAN_GOVERNANCE_CAPABILITY')
        if env.get('STUDIO_ALLOW_WIKI_RESET') == 'true': env.pop('STUDIO_ALLOW_WIKI_RESET')
        if env.get('RESULT_REVIEWER_ID') == 'urn:aoa:human:course-result-reviewer': env.pop('RESULT_REVIEWER_ID')
        for key in ('volumes','ports','extra_hosts'):
            if key in service: service[key] = sorted(service[key], key=lambda item: json.dumps(item, sort_keys=True))
    return services


def main():
    with tempfile.TemporaryDirectory(prefix='aoa compose check ') as tmp:
        env_file = Path(tmp)/'.env'
        for route in ('hosted','local'):
            values = {'PROVIDER':'openai', 'MODEL':'gpt-oss-120b',
                      'OPENAI_BASE_URL':'https://api.cerebras.ai/v1',
                      'CEREBRAS_API_KEY':'fixture-generation-key', 'TYPESAFE_API_KEY':'fixture-decision-key',
                      'AOA_OPENAI_API_KEY':'fixture-old-key', 'ANTHROPIC_API_KEY':'',
                      'DECISION_PROVIDER':'typesafe','DECISION_MODEL':'jev-1.13.0',
                      'DECISION_BASE_URL':'https://api.typesafe.ai',
                      'OLLAMA_HOST':'http://host.docker.internal:11434'}
            if route == 'local':
                values.update(PROVIDER='ollama',MODEL='gpt-oss:20b',
                              OPENAI_BASE_URL='http://host.docker.internal:11434/v1',
                              DECISION_PROVIDER='ollama',DECISION_MODEL='gpt-oss:20b',
                              DECISION_BASE_URL='http://host.docker.internal:11434')
            env_file.write_text(''.join(f'{key}={value}\n' for key,value in values.items()))
            for session in (1,2,3,4):
                env = {k:v for k,v in os.environ.items() if not k.startswith(('COURSE_','AOA_','DIRECTORY_'))}
                env.update(values)
                shell = 'session="$1"; source ./scripts/compose.sh; "$2" -c '\
                        "'import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith((\"COURSE_\",\"DIRECTORY_\"))}))'"
                env.update(json.loads(subprocess.check_output(['bash','-c',shell,'check',str(session),sys.executable],cwd=ROOT,env=env,text=True)))
                files = [ARCHIVE/'docker-compose.yml', ARCHIVE/'docker-compose.directory.yml']
                if session == 1: files += [ARCHIVE/'docker-compose.session1.yml']
                if session == 3: files += [ARCHIVE/'docker-compose.session3.yml',ARCHIVE/'docker-compose.session3-lab.yml']
                if session == 4: files += [ARCHIVE/'docker-compose.session4.yml']
                files += [ARCHIVE/'docker-compose.revised.yml']
                if session == 3: files += [ARCHIVE/'docker-compose.revised-eve.yml']
                profiles = [f'session{session}']
                if session == 3: profiles += ['session3-lab-wrapped']
                if session in (3,4): profiles += ['directory']
                expected = normalise(config(files,profiles,env,env_file)['services'])
                actual = normalise(config([ROOT/'system/docker-compose.yml'],profiles,env,env_file)['services'])
                assert actual.keys() == expected.keys(), (route,session,actual.keys() ^ expected.keys())
                for name in expected:
                    assert actual[name] == expected[name], (route,session,name,
                        {k:(expected[name].get(k),actual[name].get(k)) for k in expected[name].keys() | actual[name].keys() if expected[name].get(k)!=actual[name].get(k)})
                assert actual['evaluator']['environment']['OPENAI_API_KEY'] == 'fixture-generation-key'
                print(f'PASS: {route}, session {session}: services, mounts, endpoints and runtime settings match')
        # Native authoring must mount the same real learner folder.
        native = config([ROOT/'system/docker-compose.yml'],['session3-lab-native'],env,env_file)['services']['eve-workshop-native']
        mount = next(v for v in native['volumes'] if v['target']=='/workshop')
        assert mount['source'] == str(ROOT/'system/agents-eve/workshop') and not mount.get('read_only',False)
        print('PASS: native EVE uses the writable learner workshop')

if __name__ == '__main__': main()
