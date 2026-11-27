"""Shell integration with isolated fake interpreters; no package/network operations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Execute the real preflight with simulated interpreter/platform properties.
STUB = r'''import builtins, json, os, pathlib, runpy, shutil, sys, types
from unittest.mock import patch
exe = pathlib.Path(sys.argv[0])
cfg = json.loads(exe.with_name(exe.name + '.json').read_text())
args = sys.argv[1:]
with open(os.environ['INSTALL_TEST_LOG'], 'a') as f:
    f.write(json.dumps([str(exe), args]) + '\n')
if any(a.endswith('python_runtime.py') for a in args):
    probe = next(a for a in args if a.endswith('python_runtime.py'))
    mode, root = args[-2:]
    version = tuple(cfg.get('version', [3, 12, 3]))
    prefix = str(exe.parent.parent) if cfg.get('venv') else '/base'
    implementation = types.SimpleNamespace(**{k: getattr(sys.implementation, k) for k in dir(sys.implementation) if not k.startswith('__')})
    implementation.name = cfg.get('implementation', 'cpython')
    real_import = builtins.__import__
    def simulated_import(name, *args, **kwargs):
        if name == cfg.get('missing_module'): raise ImportError('Missing ' + name)
        return real_import(name, *args, **kwargs)
    with patch.object(sys, 'implementation', implementation), \
         patch.object(sys, 'platform', cfg.get('platform', 'linux')), \
         patch('builtins.__import__', side_effect=simulated_import), \
         patch.object(sys, 'argv', [probe, mode, root]), \
         patch.object(sys, 'version_info', version), \
         patch.object(sys, 'prefix', prefix), \
         patch.object(sys, 'base_prefix', '/base'), \
         patch('platform.python_version', return_value='.'.join(map(str, version))), \
         patch('platform.machine', return_value=cfg.get('machine', 'x86_64')), \
         patch('sysconfig.get_config_var', return_value=cfg.get('free_threaded', 0)), \
         patch('os.confstr', return_value=cfg.get('libc', 'glibc 2.39')):
        runpy.run_path(probe, run_name='__main__')
elif '-m' in args and args[args.index('-m') + 1] == 'venv':
    dest = pathlib.Path(args[-1]); (dest / 'bin').mkdir(parents=True)
    shutil.copy2(exe, dest / 'bin/python')
    cfg['venv'] = True
    (dest / 'bin/python.json').write_text(json.dumps(cfg))
    (dest / 'pyvenv.cfg').write_text('test environment')
elif '-m' in args and args[args.index('-m') + 1] == 'pip':
    if cfg.get('broken_pip'): sys.exit(1)
    if '-r' in args and os.environ.get('INSTALL_TEST_FAIL'): sys.exit(17)
elif args == ['automation_gui.py']:
    assert os.environ['VIRTUAL_ENV'] == str(exe.parent.parent)
    assert 'PYTHONHOME' not in os.environ and 'PYTHONPATH' not in os.environ
else:
    sys.exit(98)
'''


class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project with spaces'
        self.project.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        # Keep PATH isolated from real Python installations.
        for utility in ('dirname', 'cat'):
            (self.bin / utility).symlink_to(shutil.which(utility))
        for name in ('install.sh', 'start.sh', 'python_runtime.sh', 'python_runtime.py', 'requirements.txt'):
            shutil.copy2(ROOT / name, self.project / name)
        self.log = self.root / 'calls.jsonl'
        self.env = dict(os.environ, PATH=str(self.bin), INSTALL_TEST_LOG=str(self.log))
        for name in ('CTSVISION_PYTHON', 'VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH', 'INSTALL_TEST_FAIL'):
            self.env.pop(name, None)

    def interpreter(self, name='python3.12', version=(3, 12, 3), **config):
        path = self.bin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!' + sys.executable + '\n' + STUB)
        path.chmod(0o755)
        path.with_name(path.name + '.json').write_text(json.dumps(dict(version=version, **config)))
        return path

    def venv(self, version=(3, 12, 3), **config):
        exe = self.interpreter(str(self.project / 'venv/bin/python'), version, venv=True, **config)
        (self.project / 'venv/pyvenv.cfg').write_text('existing environment')
        return exe

    def run_script(self, name='install.sh'):
        return subprocess.run(['/bin/bash', str(self.project / name)], cwd=self.root,
                              env=self.env, text=True, capture_output=True, timeout=20)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def creation_calls(self):
        return [c for c in self.calls() if '-m' in c[1] and 'venv' in c[1]]

    def test_shell_syntax(self):
        for name in ('install.sh', 'start.sh', 'python_runtime.sh', 'create_release.sh'):
            subprocess.run(['/bin/bash', '-n', str(ROOT / name)], check=True)

    def test_python314_with_compatible_interpreter(self):
        self.interpreter('python3', (3, 14, 0))
        chosen = self.interpreter()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Installation erfolgreich abgeschlossen.', result.stdout)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))
        pip_calls = [c for c in self.calls() if 'pip' in c[1]]
        self.assertTrue(all(c[0] == str(self.project / 'venv/bin/python') for c in pip_calls))
        self.assertEqual((self.bin / 'python3.json').read_text(), json.dumps(dict(version=(3,14,0))))

    def test_python314_without_compatible_interpreter(self):
        self.interpreter('python3', (3, 14, 0))
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('paddlepaddle==3.2.2', result.stderr)
        self.assertIn('CTSVISION_PYTHON=', result.stderr)
        self.assertFalse((self.project / 'venv').exists())

    def test_preference_uses_actual_versions(self):
        self.interpreter('python3.12', (3, 11, 9))
        self.interpreter('python3.13', (3, 13, 1))
        chosen = self.interpreter('python3', (3, 12, 3))
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))

    def test_fallback_313_before_311(self):
        chosen = self.interpreter('python3.13', (3, 13, 1))
        self.interpreter('python3.11', (3, 11, 9))
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))

    def test_fallback_311(self):
        self.interpreter('python3.11', (3, 11, 9))
        self.assertEqual(self.run_script().returncode, 0)

    def test_manual_selection(self):
        self.interpreter()
        chosen = self.interpreter('custom interpreter', (3, 13, 1))
        self.env['CTSVISION_PYTHON'] = str(chosen)
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))

    def test_invalid_manual_selection_does_not_fall_back(self):
        self.interpreter()
        for selection in ('/missing/python', str(self.interpreter('bad', (3,14,0)))):
            with self.subTest(selection=selection):
                self.env['CTSVISION_PYTHON'] = selection
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertFalse(self.creation_calls())

    def test_compatible_existing_environment_is_preserved(self):
        self.venv((3,11,9))
        self.interpreter()
        before = (self.project / 'venv/pyvenv.cfg').read_bytes()
        self.assertEqual(self.run_script().returncode, 0)
        self.assertFalse(self.creation_calls())
        self.assertEqual((self.project / 'venv/pyvenv.cfg').read_bytes(), before)

    def test_incompatible_existing_environment_blocks_both_scripts(self):
        exe = self.venv((3,14,0))
        self.interpreter()
        before = exe.read_bytes()
        for script in ('install.sh', 'start.sh'):
            result = self.run_script(script)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('nicht gelöscht', result.stderr)
        self.assertEqual(exe.read_bytes(), before)
        self.assertFalse(self.creation_calls())

    def test_damaged_environment_is_preserved(self):
        (self.project / 'venv').mkdir()
        marker = self.project / 'venv/keep'; marker.write_text('keep')
        self.interpreter()
        for script in ('install.sh', 'start.sh'):
            self.assertNotEqual(self.run_script(script).returncode, 0)
        self.assertEqual(marker.read_text(), 'keep')

    def test_broken_symlink_is_preserved(self):
        (self.project / 'venv').symlink_to(self.root / 'missing')
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertTrue((self.project / 'venv').is_symlink())

    def test_missing_pip_blocks_both_scripts(self):
        self.venv(broken_pip=True)
        for script in ('install.sh', 'start.sh'):
            self.assertNotEqual(self.run_script(script).returncode, 0)

    def test_foreign_environment_not_used(self):
        foreign = self.interpreter('python3.12', venv=True)
        chosen = self.interpreter('python3.13', (3,13,1))
        self.env['VIRTUAL_ENV'] = str(foreign.parent.parent)
        self.env['PYTHONHOME'] = '/invalid'; self.env['PYTHONPATH'] = '/invalid'
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))

    def test_start_uses_project_interpreter(self):
        exe = self.venv()
        self.interpreter('python', (3,14,0))
        self.env['VIRTUAL_ENV'] = '/foreign'
        self.assertEqual(self.run_script('start.sh').returncode, 0)
        self.assertEqual(self.calls()[-1], [str(exe), ['automation_gui.py']])

    def test_start_without_environment(self):
        result = self.run_script('start.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('./install.sh', result.stdout)

    def test_dotvenv_is_not_modified(self):
        (self.project / '.venv').mkdir()
        marker = self.project / '.venv/keep'; marker.write_text('keep')
        self.interpreter()
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn('.venv bleibt unverändert', result.stdout)
        self.assertEqual(marker.read_text(), 'keep')

    def test_platform_and_free_threaded_rejections(self):
        for config in ({'machine':'i686'}, {'libc':'musl 1.2'}, {'libc':'glibc 2.33'},
                       {'machine':'aarch64','libc':'glibc 2.38'}, {'free_threaded':1},
                       {'implementation':'pypy'}, {'platform':'darwin'}, {'missing_module':'ensurepip'}):
            with self.subTest(config=config):
                self.interpreter(**config)
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertFalse((self.project / 'venv').exists())

    def test_fedora44_error_guidance(self):
        release = self.root / 'os-release'
        release.write_text('ID=fedora\nPRETTY_NAME="Fedora Linux 44"\n')
        helper = self.project / 'python_runtime.sh'
        helper.write_text(helper.read_text().replace('/etc/os-release', str(release)))
        self.interpreter('python3', (3,14,0))
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Fedora Linux 44', result.stderr)
        self.assertIn('sudo dnf install python3.12', result.stderr)
        self.assertFalse(self.creation_calls())

    def test_shadowed_system_interpreter_remains_discoverable(self):
        self.interpreter('python3.12', venv=True)
        system_bin = self.root / 'system-bin'
        system_bin.mkdir()
        chosen = self.interpreter(str(system_bin / 'python3.12'))
        self.env['PATH'] += os.pathsep + str(system_bin)
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.creation_calls()[0][0], str(chosen))

    def test_failed_dependency_install_still_aborts(self):
        self.interpreter()
        self.env['INSTALL_TEST_FAIL'] = '1'
        result = self.run_script()
        self.assertEqual(result.returncode, 17)
        self.assertNotIn('Installation erfolgreich abgeschlossen.', result.stdout)


if __name__ == '__main__':
    unittest.main()
