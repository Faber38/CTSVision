"""Gezielte Release-/Update-Tests mit echten Dateien in temporären Installationen."""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import project_store
import update


def load_module(name, source):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / (name + '.py'))
    sys.modules[name] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


builder = load_module('release_builder_test', (ROOT / 'tools/build_release.py').read_bytes())


class CatalogTests(unittest.TestCase):
    def test_old_catalog_migrates_without_writes_or_duplicates(self):
        original = json.loads((ROOT / 'config/reference_catalog.json').read_text())
        old = [e for e in original if e['name'] != 'galaxiekarte_carrier_symbol']
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / 'reference_catalog.json'
            catalog.write_text(json.dumps(old))
            before = catalog.read_bytes()
            with patch.object(project_store, 'REFERENCE_CATALOG_PATH', catalog):
                for _ in range(2):
                    result = project_store.load_reference_catalog()
                    symbol = [e for e in result if e['name'] == 'galaxiekarte_carrier_symbol']
                    self.assertEqual(symbol, [project_store.CARRIER_SYMBOL_REFERENCE])
                    self.assertEqual(len(result), len(old) + 1)
            self.assertEqual(catalog.read_bytes(), before)

    def test_existing_entry_preserved(self):
        entry = dict(project_store.CARRIER_SYMBOL_REFERENCE, title='Eigener Titel')
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / 'reference_catalog.json'
            catalog.write_text(json.dumps([entry]))
            with patch.object(project_store, 'REFERENCE_CATALOG_PATH', catalog):
                self.assertEqual(project_store.load_reference_catalog(), [entry])


class ReleaseUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_zip = ROOT / 'release/CTSVision_v1.9.4.zip'
        cls.new_zip = ROOT / 'release/CTSVision_v1.9.5.zip'
        if not cls.old_zip.is_file() or not cls.new_zip.is_file():
            raise RuntimeError('Für Integrationstests sind die lokalen ZIPs v1.9.4 und v1.9.5 erforderlich.')
        digest = hashlib.sha256(cls.old_zip.read_bytes()).hexdigest()
        if digest != 'bde30e01aef3dc8ae62d633463a2baabb81492849bb7b8b08adbc88735ef2573':
            raise RuntimeError('v1.9.4-ZIP entspricht nicht dem veröffentlichten Original.')
        with zipfile.ZipFile(cls.old_zip) as z:
            cls.old = load_module('old_update_test', z.read('CTSVision_v1.9.4/update.py'))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        with zipfile.ZipFile(self.old_zip) as z:
            z.extractall(self.root)
        self.install = self.root / 'CTSVision_v1.9.4'
        self.personal = {
            'venv/pyvenv.cfg': b'original python environment',
            'venv/bin/python': b'original interpreter',
            '.venv/keep': b'alternative environment',
            'config.json': b'{"references":{"my_reference":{"x":123,"y":456}}}',
            'settings.json': b'{"last_route":"routes/private.csv"}',
            'route_state.json': b'{"completed_jumps":7}',
            'references/personal.png': b'personal image bytes',
            'references/galaxiekarte_carrier_symbol.png': b'existing carrier capture',
            'logs/carrier_history.csv': b'personal history\r\n',
            'logs/other.log': b'personal log',
            'route.csv': b'root route',
            'routes/deep/private.CSV': b'nested route',
            'assets/private.csv': b'route in a managed directory',
        }
        for name, data in self.personal.items():
            file = self.install / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        self.old_catalog = (self.install / 'config/reference_catalog.json').read_bytes()
        self.download = self.root / 'download'
        self.download.mkdir()
        self.package = self.download / 'v1.9.5.zip'
        self.package.write_bytes(self.new_zip.read_bytes())

    def assert_personal_unchanged(self):
        for name, data in self.personal.items():
            with self.subTest(name=name):
                self.assertEqual((self.install / name).read_bytes(), data)
        self.assertEqual((self.install / 'config/reference_catalog.json').read_bytes(), self.old_catalog)

    def apply(self, module, fail=False):
        original_copy = module._copy_release
        def copy_then_fail(source, destination):
            original_copy(source, destination)
            if source.name == 'CTSVision_v1.9.5' and fail:
                raise OSError('simulierter Updatefehler nach Kopieren')
        with patch.object(module, '_wait_for_parent_exit'), \
                patch.object(module, '_restart_ctsvision') as restart, \
                patch.object(module, '_copy_release', side_effect=copy_then_fail):
            result = module.apply_update(
                zip_path=self.package, install_dir=self.install,
                current_version='1.9.4', latest_version='1.9.5', parent_pid=123)
            restart.assert_called_once_with(self.install)
            return result

    def test_old_updater_success_and_wizard_migration(self):
        self.assertEqual(self.apply(self.old), 0)
        self.assert_personal_unchanged()
        self.assertIn('CURRENT_VERSION = "1.9.5"', (self.install / 'update.py').read_text())
        installed_store = load_module('installed_store_test', (self.install / 'project_store.py').read_bytes())
        with patch.object(installed_store, 'REFERENCE_CATALOG_PATH', self.install / 'config/reference_catalog.json'):
            names = [e['name'] for e in installed_store.load_reference_catalog()]
        self.assertEqual(names.count('galaxiekarte_carrier_symbol'), 1)
        self.assert_personal_unchanged()
        self.assertTrue((self.install / 'start.sh').stat().st_mode & 0o111)

    def test_old_updater_rollback(self):
        original = (self.install / 'automation_gui.py').read_bytes()
        self.assertEqual(self.apply(self.old, fail=True), 2)
        self.assert_personal_unchanged()
        self.assertEqual((self.install / 'automation_gui.py').read_bytes(), original)
        self.assertIn('CURRENT_VERSION = "1.9.4"', (self.install / 'update.py').read_text())

    def add_unwanted_personal_files(self):
        with zipfile.ZipFile(self.package, 'a') as z:
            for name in self.personal:
                z.writestr('CTSVision_v1.9.5/' + name, b'must never overwrite user data')

    def test_new_updater_protects_even_bad_package(self):
        self.add_unwanted_personal_files()
        self.assertEqual(self.apply(update), 0)
        self.assert_personal_unchanged()

    def test_new_updater_rollback_protects_user_files(self):
        self.add_unwanted_personal_files()
        original = (self.install / 'automation_gui.py').read_bytes()
        self.assertEqual(self.apply(update, fail=True), 2)
        self.assert_personal_unchanged()
        self.assertEqual((self.install / 'automation_gui.py').read_bytes(), original)
        with zipfile.ZipFile(self.old_zip) as archive:
            self.assertEqual(
                (self.install / 'assets/templates/galaxiekarte_carrier_symbol.png').read_bytes(),
                archive.read('CTSVision_v1.9.4/assets/templates/galaxiekarte_carrier_symbol.png'))

    def test_rollback_keeps_new_or_changed_nested_route(self):
        backup = self.install / 'backup/test'
        update._backup_managed_files(self.install, backup)
        changed = self.install / 'assets/private.csv'
        changed.write_bytes(b'route changed after backup')
        new = self.install / 'new_dir/new.csv'
        new.parent.mkdir()
        new.write_bytes(b'new route after backup')
        (new.parent / 'new_code.py').write_text('new code')
        update._restore_backup(backup, self.install)
        self.assertEqual(changed.read_bytes(), b'route changed after backup')
        self.assertEqual(new.read_bytes(), b'new route after backup')
        self.assertFalse((new.parent / 'new_code.py').exists())

    def test_archive_complete_and_no_personal_data(self):
        # Build only a disposable test fixture, never a project release artifact.
        names = json.loads((ROOT / 'tools/release_manifest.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in names + ['tools/release_manifest.json']:
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, destination)
            archive = builder.build_release(root, update.CURRENT_VERSION)
            builder.validate_archive(archive, names, update.CURRENT_VERSION)
            with zipfile.ZipFile(archive) as z:
                for name in names:
                    self.assertEqual(z.read('CTSVision_v' + update.CURRENT_VERSION + '/' + name),
                                     (ROOT / name).read_bytes(), name)

    def test_updated_scripts_arrive_and_environment_is_preserved(self):
        names = json.loads((ROOT / 'tools/release_manifest.json').read_text())
        with zipfile.ZipFile(self.package, 'w') as archive:
            for name in names:
                archive.write(ROOT / name, 'CTSVision_v1.9.5/' + name)
        self.assertEqual(self.apply(update), 0)
        self.assert_personal_unchanged()
        for name in ('install.sh', 'start.sh', 'python_runtime.py', 'python_runtime.sh',
                     'README.md', 'README_DE.md'):
            self.assertEqual((self.install / name).read_bytes(), (ROOT / name).read_bytes())

    def test_required_readmes_and_runtime_files(self):
        names = json.loads((ROOT / 'tools/release_manifest.json').read_text())
        for required in ('README.md', 'README_DE.md', 'python_runtime.py', 'python_runtime.sh'):
            with self.subTest(required=required), self.assertRaisesRegex(ValueError, 'Pflichtdateien'):
                builder.validate_archive(self.new_zip, [n for n in names if n != required], '1.9.5')

    def test_readme_language_links_and_instructions(self):
        for name in ('README.md', 'README_DE.md'):
            text = (ROOT / name).read_text()
            self.assertEqual(text.splitlines()[0], '**[English](README.md) | [Deutsch](README_DE.md)**')
            for term in ('CTSVISION_PYTHON=/usr/bin/python3.12', 'Fedora 44',
                         'sudo dnf install python3.12', '3.11–3.13', '2.34', '2.39'):
                self.assertIn(term, text)

    def test_manifest_rejects_personal_data(self):
        for name in self.personal:
            with self.subTest(name=name), self.assertRaises(ValueError):
                builder.validate_paths([name])

    def test_build_refuses_overwrite(self):
        before = self.new_zip.read_bytes()
        with self.assertRaises(FileExistsError):
            builder.build_release(ROOT, '1.9.5')
        self.assertEqual(self.new_zip.read_bytes(), before)

    def test_protected_paths(self):
        for name in self.personal:
            with self.subTest(name=name):
                self.assertTrue(update._is_protected(Path(name)))
        self.assertFalse(update._is_protected(Path('automation_gui.py')))


if __name__ == '__main__':
    unittest.main()
