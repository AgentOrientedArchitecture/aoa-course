"""Exercise the actual shell/batch entry points with harmless Docker stand-ins.

No daemon, provider keys or course data are used. Windows runs native cmd.exe
and an executable stand-in (a .cmd would change batch control flow).
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = os.name == 'nt'
EXT = '.bat' if WINDOWS else '.sh'


class Launchers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools_dir = tempfile.TemporaryDirectory(prefix='aoa launcher tools ')
        tools = Path(cls.tools_dir.name)
        if WINDOWS:
            source = tools / 'mock.cs'
            source.write_text(r'''
using System;
using System.IO;
using System.Diagnostics;
using System.Web.Script.Serialization;
public class Mock {
  public static int Main(string[] args) {
    string tool = Path.GetFileNameWithoutExtension(Process.GetCurrentProcess().MainModule.FileName);
    var row = new { tool = tool, argv = args, cwd = Directory.GetCurrentDirectory(),
      registry = Environment.GetEnvironmentVariable("COURSE_REGISTRY_ALLOWLIST") ?? "",
      evaluator = Environment.GetEnvironmentVariable("COURSE_EVALUATOR_ALLOWLIST") ?? "",
      discovery = Environment.GetEnvironmentVariable("COURSE_DISCOVERY_BACKEND") ?? "",
      workflows = Environment.GetEnvironmentVariable("COURSE_STUDIO_WORKFLOWS") ?? "",
      governance = Environment.GetEnvironmentVariable("COURSE_PLAN_GOVERNANCE_CAPABILITY") ?? "" };
    File.AppendAllText(Environment.GetEnvironmentVariable("MOCK_LOG"), new JavaScriptSerializer().Serialize(row) + "\n");
    string fail = Environment.GetEnvironmentVariable("MOCK_FAIL_COMMAND");
    return tool == "docker" && Array.IndexOf(args, fail) >= 0 ? 17 : 0;
  }
}
''')
            ps = tools / 'compile.ps1'
            ps.write_text("$ErrorActionPreference='Stop'\nAdd-Type -Path $env:MOCK_SOURCE -OutputAssembly $env:MOCK_EXE -OutputType ConsoleApplication -ReferencedAssemblies System.dll,System.Core.dll,System.Web.Extensions.dll\n")
            env = {**os.environ, 'MOCK_SOURCE': str(source), 'MOCK_EXE': str(tools/'docker.exe')}
            subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps)], env=env, check=True)
            shutil.copy2(tools/'docker.exe', tools/'curl.exe')
        else:
            source = '''#!%s
import json,os,sys
row={'tool':os.path.basename(sys.argv[0]),'argv':sys.argv[1:],'cwd':os.getcwd(),'registry':os.getenv('COURSE_REGISTRY_ALLOWLIST',''),'evaluator':os.getenv('COURSE_EVALUATOR_ALLOWLIST',''),'discovery':os.getenv('COURSE_DISCOVERY_BACKEND',''),'workflows':os.getenv('COURSE_STUDIO_WORKFLOWS',''),'governance':os.getenv('COURSE_PLAN_GOVERNANCE_CAPABILITY','')}
with open(os.environ['MOCK_LOG'],'a') as f:f.write(json.dumps(row)+'\\n')
sys.exit(17 if row['tool']=='docker' and os.getenv('MOCK_FAIL_COMMAND') in sys.argv[1:] else 0)
''' % sys.executable
            for name in ('docker', 'curl'):
                p = tools/name
                p.write_text(source)
                p.chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        cls.tools_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aoa course with spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT/'scripts', self.root/'scripts')
        self.log = self.root/'commands.jsonl'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('AOA_', 'COURSE_', 'MOCK_'))}
        self.env.update(PATH=self.tools_dir.name + os.pathsep + os.environ['PATH'], MOCK_LOG=str(self.log))
        (self.root/'.env').write_text('MODEL=old-model\n')

    def invoke(self, name, *args, expect=0):
        script = self.root/'scripts'/(name+EXT)
        if WINDOWS:
            result = subprocess.run(subprocess.list2cmdline([str(script), *args]), shell=True,
                                    cwd=self.tools_dir.name, env=self.env, capture_output=True, text=True, timeout=20)
        else:
            result = subprocess.run(['bash', str(script), *args], cwd=self.tools_dir.name,
                                    env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def clean_log(self):
        self.log.write_text('')

    def assert_current(self, row):
        argv = row['argv']
        self.assertEqual([a for a in argv if a.endswith('.yml')], ['system/docker-compose.yml'])
        self.assertIn('system/docker-compose.yml', argv)
        self.assertIn('.env', argv)
        self.assertEqual(Path(row['cwd']).resolve(), self.root.resolve())

    def test_session_starts_select_current_and_forward_arguments(self):
        for session in (1, 2, 4):
            with self.subTest(session=session):
                self.clean_log()
                rows = self.invoke(f'session{session}-up', '--wait', '--wait-timeout', '90')
                self.assertEqual(len(rows), 2 if session == 4 else 1)
                row = rows[0]
                self.assert_current(row)
                self.assertIn(f'session{session}', row['argv'])
                self.assertEqual(row['argv'][-3:], ['--wait', '--wait-timeout', '90'])
                self.assertIn('evaluator-cv-data', row['registry'])
                self.assertEqual(row['discovery'], 'agntcy' if session == 4 else 'local')
                self.assertEqual(row['governance'], 'evaluator-plan-governance' if session == 4 else '')
                self.assertEqual(row['workflows'], {1:'cv-fit', 2:'cv-fit,knowledge-ingest,wiki-graph,knowledge-query', 4:'agent-card-check,cv-fit,flow-audit,wiki-graph,knowledge-query'}[session])
                self.assertEqual('evaluator-plan-governance' in row['evaluator'], session == 4)
                if session == 4:
                    self.assertIn('directory', row['argv'])
                    self.assertEqual(rows[-1]['argv'][-3:], ['sync', '--wait', '120'])

    def test_current_course_is_the_default_without_mode_flags(self):
        for launcher in ('session1-up', 'session2-up', 'session4-up', 'test_model_provider'):
            self.clean_log()
            rows = self.invoke(launcher)
            self.assert_current(rows[-1] if launcher == 'test_model_provider' else rows[0])

    def test_existing_overlay_remains_readable_but_is_not_required(self):
        (self.root/'.env.revised').write_text('MODEL=course-model\n')
        row = self.invoke('session1-up')[0]
        self.assert_current(row)
        self.assertLess(row['argv'].index('.env'), row['argv'].index('.env.revised'))

    def test_local_ollama_option(self):
        self.env['AOA_LOCAL'] = 'true'
        row = self.invoke('session1-up')[0]
        self.assert_current(row)
        self.assertIn('local', row['argv'])
        self.assertNotIn('.env.revised', row['argv'])

    def test_invalid_session_stops_before_docker(self):
        self.assertEqual(self.invoke('session-up', '5', expect=2), [])
        self.assertEqual(self.invoke('session-up', '3', expect=2), [])

    def test_down_and_logs_include_every_service_without_deleting_data(self):
        sentinel = self.root/'system/services/planner/traces/cases.sqlite3'
        sentinel.parent.mkdir(parents=True)
        sentinel.write_bytes(b'preserve this saved case')
        for name in ('down', 'logs'):
            with self.subTest(name=name):
                self.clean_log()
                row = self.invoke(name)[0]
                self.assert_current(row)
                self.assertIn('*', row['argv'])
                self.assertNotIn('-v', row['argv'])
                self.assertNotIn('--volumes', row['argv'])
                self.assertEqual(sentinel.read_bytes(), b'preserve this saved case')

    def test_shutdown_retains_explicit_user_options_and_exit_code(self):
        self.env['MOCK_FAIL_COMMAND'] = 'down'
        rows = self.invoke('down', '--timeout', '30', expect=17)
        self.assertEqual(rows[0]['argv'][-2:], ['--timeout','30'])

    def test_eve_prebuild_does_not_create_or_run_agent(self):
        row = self.invoke('session3-build', '--no-cache')[0]
        self.assert_current(row)
        self.assertEqual(row['argv'][-2:], ['build','--no-cache'])
        self.assertFalse((self.root/'system/agents-eve/workshop').exists())

    def test_eve_native_stops_estate_then_builds_and_runs(self):
        rows = self.invoke('session3-up')
        self.assertEqual(len(rows), 3)
        self.assertIn('down', rows[0]['argv'])
        self.assertEqual(rows[1]['argv'][-2:], ['build','eve-workshop-native'])
        self.assertIn('run', rows[2]['argv'])
        self.assertIn('HOME=/tmp', rows[2]['argv'])
        self.assertEqual(rows[2]['argv'][-1], 'eve-workshop-native')
        self.assertEqual(rows[2]['discovery'], 'agntcy')
        self.assertEqual(rows[2]['workflows'], 'cv-fit,cv-fit-interview')
        self.assertFalse((self.root/'system/agents-eve/workshop/capability-card.yaml').exists())

    def test_failed_build_never_enters_workshop(self):
        self.env['MOCK_FAIL_COMMAND'] = 'build'
        rows = self.invoke('session3-up', expect=17)
        self.assertEqual(len(rows), 2)
        self.assertFalse(any('run' in row['argv'] for row in rows))

    def test_adopt_requires_authored_files_and_preserves_existing_card(self):
        self.assertEqual(self.invoke('session3-adopt', expect=1), [])
        workspace = self.root/'system/agents-eve/workshop'
        for name in ('agent/agent.ts','agent/instructions.md','agent/channels/eve.ts'):
            p = workspace/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('learner-authored content')
        card = workspace/'capability-card.yaml'
        card.write_text('custom learner contract')
        rows = self.invoke('session3-adopt')
        self.assertEqual(rows[0]['argv'][-2:], ['build','eve-workshop-native'])
        self.assertIn('npm', rows[1]['argv'])
        self.assertIn('--force-recreate', rows[2]['argv'])
        self.assertEqual([r['tool'] for r in rows[3:]], ['curl','curl','docker'])
        self.assertEqual(rows[-1]['argv'][-3:], ['sync', '--wait', '120'])
        self.assertEqual(card.read_text(), 'custom learner contract')
        self.assertEqual((workspace/'agent/agent.ts').read_text(), 'learner-authored content')

    def test_provider_check_uses_revised_overlay_with_only_revised_env(self):
        (self.root/'.env').unlink()
        (self.root/'.env.revised').write_text('MODEL=course-model\n')
        rows = self.invoke('test_model_provider')
        row = rows[-1]
        self.assertIn('system/docker-compose.yml', row['argv'])
        self.assertIn('.env.revised', row['argv'])
        self.assertIn('_base.provider_test', row['argv'])

    def test_single_example_works_for_provider_and_eve_launchers(self):
        (self.root/'.env').write_bytes((ROOT/'.env.example').read_bytes())
        for launcher in ('test_model_provider', 'session3-build', 'session3-up'):
            self.clean_log()
            rows = self.invoke(launcher)
            self.assert_current(rows[-1])
            self.assertNotIn('.env.revised', rows[-1]['argv'])

    def test_env_values_are_data_not_shell_commands(self):
        (self.root/'.env').write_text(
            'MODEL=$(touch should-not-exist)\n'
            'AOA_UNUSED=& echo unsafe > should-not-exist\n'
            'DECISION_PROVIDER=typesafe\n')
        row = self.invoke('session1-up')[0]
        self.assert_current(row)
        self.assertFalse((self.root/'should-not-exist').exists())

    def test_directory_is_container_only_and_preserves_records(self):
        data = self.root / '.course-data'
        data.mkdir()
        record = data / 'interviewer.oasf.json'
        record.write_text('existing record')
        row = self.invoke('directory', 'up')[0]
        self.assertIn('system/docker-compose.yml', row['argv'])
        self.assertIn('--wait', row['argv'])
        self.assertEqual(row['argv'][-1], 'agntcy-directory')
        self.assertNotIn('--remove-orphans', row['argv'])
        self.clean_log()
        row = self.invoke('directory', 'pull', '--cid-file', 'record with spaces.cid', '--out', 'retrieved record.json')[0]
        self.assertEqual(row['argv'][-7:], ['python', '/app/directory-lab.py', 'pull', '--cid-file', 'record with spaces.cid', '--out', 'retrieved record.json'])
        self.assertIn('-T', row['argv'])
        self.clean_log()
        row = self.invoke('directory', 'cli', 'version')[0]
        self.assertEqual(row['argv'][-1], 'version')
        self.assertIn('dirctl', row['argv'])
        self.clean_log()
        row = self.invoke('directory', 'stop')[0]
        self.assertIn('stop', row['argv'])
        self.assertNotIn('down', row['argv'])
        self.assertEqual(record.read_text(), 'existing record')

    def test_directory_errors_propagate_and_invalid_commands_do_not_run(self):
        self.assertEqual(self.invoke('directory', 'unknown', expect=2), [])
        self.env['MOCK_FAIL_COMMAND'] = 'up'
        self.invoke('directory', 'up', expect=17)
        self.clean_log()
        self.env['MOCK_FAIL_COMMAND'] = 'exec'
        self.invoke('directory', 'check', 'missing.json', expect=17)


if __name__ == '__main__':
    unittest.main()
