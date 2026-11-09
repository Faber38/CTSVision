"""Installationsskript ausführen, Python/Pip-Aufrufe lokal simulieren."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallScriptTests(unittest.TestCase):
    def test_shell_syntax(self):
        for name in ('install.sh', 'create_release.sh'):
            with self.subTest(name=name):
                subprocess.run(['bash', '-n', str(ROOT / name)], check=True)

    def run_install(self, fail=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install = root / 'installation'
            install.mkdir()
            shutil.copy2(ROOT / 'install.sh', install / 'install.sh')
            (install / 'requirements.txt').write_text('test dependency')
            (install / 'start.sh').write_text('exit 99\n')
            fakebin = root / 'bin'
            fakebin.mkdir()
            stub = '''#!/bin/bash
printf '%s %s\\n' "${0##*/}" "$*" >> "$INSTALL_TEST_LOG"
if [ "${0##*/}" = python3 ]; then
    mkdir -p venv/bin
    printf ':\\n' > venv/bin/activate
fi
if [ "${0##*/}" = pip ] && [ "$INSTALL_TEST_FAIL" = yes ]; then
    exit 17
fi
'''
            for name in ('python3', 'python', 'pip'):
                command = fakebin / name
                command.write_text(stub)
                command.chmod(0o755)
            env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ['PATH'],
                       INSTALL_TEST_LOG=str(root / 'commands.log'),
                       INSTALL_TEST_FAIL='yes' if fail else 'no')
            result = subprocess.run(['bash', str(install / 'install.sh')],
                                    cwd=root, env=env, text=True,
                                    capture_output=True, timeout=10)
            log = (root / 'commands.log').read_text().splitlines()
        return result, log

    def test_successful_install_and_completion_message(self):
        result, log = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Installation erfolgreich abgeschlossen.', result.stdout)
        self.assertIn('./start.sh', result.stdout)
        self.assertIn('Viel Spaß!', result.stdout)
        self.assertEqual(log, ['python3 -m venv venv',
                               'python -m pip install --upgrade pip',
                               'pip install -r requirements.txt'])

    def test_failed_dependency_install_still_aborts(self):
        result, _ = self.run_install(fail=True)
        self.assertEqual(result.returncode, 17)
        self.assertNotIn('Installation erfolgreich abgeschlossen.', result.stdout)


if __name__ == '__main__':
    unittest.main()
