"""Boot the actual EVE workshop as a non-root learner, without provider calls.

This catches package-cache permission errors hidden by root-only rehearsals.
Uses isolated synthetic files and a container with no network access.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def command(args, timeout=180):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError(' '.join(args)+'\n'+(result.stdout+result.stderr)[-5000:])
    return result.stdout + result.stderr if args[1] == "logs" else result.stdout


def main():
    image='aoa-course/eve-workshop-check:0.17.1'
    command(['docker','build','-t',image,'-f','system/agents-eve/runtime/Dockerfile','system/agents-eve'],timeout=600)
    with tempfile.TemporaryDirectory(prefix='aoa eve learner ') as tmp:
        workspace=Path(tmp)
        for name in ('package.json','package-lock.json','tsconfig.json'):
            shutil.copy2(ROOT/'system/agents-eve/workshop'/name, workspace/name)
        agent=workspace/'agent'; (agent/'channels').mkdir(parents=True)
        walkthrough=(ROOT/'course/sessions/session-03-eve/WALKTHROUGH.md').read_text()
        (agent/'agent.ts').write_text(re.search(r'```ts\n(.*?)\n```',walkthrough,re.S).group(1)+'\n')
        (agent/'instructions.md').write_text('Return a short answer to the supplied question.\n')
        (agent/'channels/eve.ts').write_text('import { eveChannel } from "eve/channels/eve";\nimport { none } from "eve/channels/auth";\nexport default eveChannel({ auth: none() });\n')
        # Install from the image's offline cache into the writable learner mount,
        # exactly as eve init does. A symlink to root-owned image dependencies
        # would conceal a different authored-module-cache permission boundary.
        name=f'aoa-eve-workshop-check-{os.getpid()}'
        try:
            command(['docker','run','--detach','--name',name,'--network','none',
                     '--user',f'{os.getuid()}:{os.getgid()}', '--workdir','/workshop',
                     '--mount',f'type=bind,source={workspace},target=/workshop',
                     '-e','HOME=/tmp','-e','MODEL=gpt-oss-120b',
                     '-e','LLM_BASE_URL=http://127.0.0.1:1/v1','-e','LLM_API_KEY=fixture-not-a-real-key',
                     image,'sh','-c','npm install --offline --no-audit --no-fund && exec eve dev --no-ui --host 127.0.0.1 --port 3000'])
            for _ in range(180):
                state=command(['docker','inspect',name,'--format','{{.State.Status}}']).strip()
                if state!='running':
                    raise AssertionError('EVE stopped before readiness:\n'+command(['docker','logs',name]))
                probe=subprocess.run(['docker','exec',name,'node','-e',
                    "fetch('http://127.0.0.1:3000/eve/v1/info',{signal:AbortSignal.timeout(1000)}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"],capture_output=True,timeout=5)
                if probe.returncode==0: break
                time.sleep(1)
            else: raise AssertionError('EVE did not become ready:\n'+command(['docker','logs',name]))
            command(['docker','exec',name,'sh','-c','test -d /app/node_modules/eve/.eve/workflow-cache && test -d /workshop/.eve'])
            assert (workspace/'.eve').is_dir()
            print('PASS: non-root EVE dev boots, writes its package cache and keeps application state in the mounted workshop.')
        finally:
            subprocess.run(['docker','rm','--force',name],capture_output=True)

if __name__=='__main__': main()
