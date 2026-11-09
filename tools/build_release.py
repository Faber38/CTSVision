"""Lokales Release aus einer expliziten Dateiliste bauen und prüfen."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_DIRS = {
    'references', 'debug', 'backup', 'release', 'logs', '.git',
    'venv', '.venv', '__pycache__', '.aws', '.codex', '.agents',
}
FORBIDDEN_FILES = {'config.json', 'settings.json', 'route_state.json'}


def validate_paths(names: list[str]) -> None:
    for name in names:
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name
                or any(part in FORBIDDEN_DIRS for part in path.parts)
                or path.name in FORBIDDEN_FILES
                or path.suffix.lower() in {'.csv', '.pyc', '.pyo'}):
            raise ValueError(f'Unzulässige Release-Datei: {name}')
    if len(names) != len(set(names)):
        raise ValueError('Doppelte Dateien im Release-Manifest.')


def validate_archive(archive: Path, names: list[str], version: str) -> None:
    validate_paths(names)
    prefix = f'CTSVision_v{version}/'
    with zipfile.ZipFile(archive) as z:
        expected = {prefix + name for name in names}
        expected.update({prefix + 'references/', prefix + 'debug/'})
        if set(z.namelist()) != expected or len(z.namelist()) != len(expected):
            raise ValueError('ZIP-Inhalt entspricht nicht dem Release-Manifest.')
        if z.testzip() is not None:
            raise ValueError('ZIP-Prüfsummenfehler.')
        for name in names:
            if name.endswith('.py'):
                compile(z.read(prefix + name), name, 'exec')
        tree = ast.parse(z.read(prefix + 'update.py'))
        versions = [ast.literal_eval(n.value) for n in tree.body
                    if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'CURRENT_VERSION'
                            for t in n.targets)]
        if versions != [version]:
            raise ValueError('Versionsnummer in update.py stimmt nicht überein.')
        catalog = json.loads(z.read(prefix + 'config/reference_catalog.json'))
        entries = [e for e in catalog if e['name'] == 'galaxiekarte_carrier_symbol']
        if len(entries) != 1 or prefix + entries[0]['template'] not in expected:
            raise ValueError('Carrier-Symbol-Katalogeintrag oder Vorschau fehlt.')


def build_release(root: Path, version: str) -> Path:
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('Ungültige Versionsnummer.')
    names = json.loads((root / 'tools/release_manifest.json').read_text())
    validate_paths(names)
    for name in names:
        source = root / name
        if not source.is_file() or any(p.is_symlink() for p in [source, *source.parents]):
            raise ValueError(f'Release-Datei fehlt oder ist ein Symlink: {name}')

    release_name = f'CTSVision_v{version}'
    output = root / 'release'
    output.mkdir(exist_ok=True)
    archive = output / f'{release_name}.zip'
    if archive.exists() or (output / release_name).exists():
        raise FileExistsError(f'Release {release_name} existiert bereits; unverändert belassen.')

    with tempfile.TemporaryDirectory(prefix='.build-', dir=output) as temporary:
        stage = Path(temporary) / release_name
        stage.mkdir()
        for name in names:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, destination)
        for name in ('references', 'debug'):
            (stage / name).mkdir()
        temporary_zip = Path(temporary) / archive.name
        with zipfile.ZipFile(temporary_zip, 'x', zipfile.ZIP_DEFLATED) as z:
            for name in names:
                z.write(stage / name, f'{release_name}/{name}')
            for name in ('references', 'debug'):
                z.write(stage / name, f'{release_name}/{name}/')
        validate_archive(temporary_zip, names, version)
        # Exklusives Anlegen verhindert auch bei parallelem Aufruf Überschreiben.
        with archive.open('xb') as target, temporary_zip.open('rb') as source:
            shutil.copyfileobj(source, target)
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    print(f'Geprüftes Releasepaket: {build_release(ROOT, args.version)}')
