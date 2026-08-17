from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

GITHUB_OWNER = "Faber38"
GITHUB_REPO = "CTSVision"
CURRENT_VERSION = "1.8"

LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

PROTECTED_NAMES = {
    "config",
    "references",
    "debug",
    "backup",
    "release",
    ".git",
    ".venv",
    "venv",
    "route_state.json",
}
PROTECTED_SUFFIXES = {".csv"}


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    release_name: str
    asset_name: str
    asset_url: str
    release_notes: str


def _version_tuple(version: str) -> tuple[int, ...]:
    version = version.strip().lower().replace("version", "").strip()
    if version.startswith("v"):
        version = version[1:]

    parts: list[int] = []
    for part in version.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)

    return tuple(parts or [0])


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"CTSVision/{CURRENT_VERSION}",
        },
    )


def check_for_update(
    current_version: str = CURRENT_VERSION,
    timeout: float = 5.0,
) -> UpdateInfo:
    with urllib.request.urlopen(
        _request(LATEST_RELEASE_API),
        timeout=timeout,
    ) as response:
        data = json.load(response)

    latest = str(data.get("tag_name", "")).strip().lstrip("vV")
    if not latest:
        raise RuntimeError("Keine gültige Versionsnummer im GitHub-Release gefunden.")

    expected_asset = f"CTSVision_v{latest}.zip"
    assets = data.get("assets", []) or []

    asset_name = ""
    asset_url = ""

    for asset in assets:
        name = str(asset.get("name", "")).strip()
        if name == expected_asset:
            asset_name = name
            asset_url = str(asset.get("browser_download_url", "")).strip()
            break

    if not asset_url:
        zip_assets = [
            asset
            for asset in assets
            if str(asset.get("name", "")).lower().startswith("ctsvision_")
            and str(asset.get("name", "")).lower().endswith(".zip")
        ]
        if len(zip_assets) == 1:
            asset = zip_assets[0]
            asset_name = str(asset.get("name", "")).strip()
            asset_url = str(asset.get("browser_download_url", "")).strip()

    return UpdateInfo(
        current_version=current_version,
        latest_version=latest,
        update_available=_version_tuple(latest) > _version_tuple(current_version),
        release_url=str(data.get("html_url", "")).strip(),
        release_name=str(data.get("name", "")).strip() or f"CTSVision {latest}",
        asset_name=asset_name,
        asset_url=asset_url,
        release_notes=str(data.get("body", "")).strip(),
    )


def open_release_page(url: str) -> bool:
    return bool(url) and bool(webbrowser.open(url))


def _is_protected(relative_path: Path) -> bool:
    if not relative_path.parts:
        return True

    first = relative_path.parts[0]

    if first in PROTECTED_NAMES:
        return True

    if (
        len(relative_path.parts) == 1
        and relative_path.suffix.lower() in PROTECTED_SUFFIXES
    ):
        return True

    return False


def _backup_managed_files(install_dir: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=False)

    for source in install_dir.iterdir():
        relative = Path(source.name)

        if _is_protected(relative):
            continue

        destination = backup_dir / source.name

        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            shutil.copy2(source, destination)


def _copy_release(source_root: Path, install_dir: Path) -> None:
    for source in source_root.rglob("*"):
        relative = source.relative_to(source_root)

        if _is_protected(relative):
            continue

        destination = install_dir / relative

        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _restore_backup(backup_dir: Path, install_dir: Path) -> None:
    for current in install_dir.iterdir():
        relative = Path(current.name)

        if _is_protected(relative):
            continue

        if current.is_dir():
            shutil.rmtree(current)
        else:
            current.unlink()

    for source in backup_dir.iterdir():
        destination = install_dir / source.name

        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def _extract_release_root(zip_path: Path, temp_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(temp_dir)

    entries = [p for p in temp_dir.iterdir() if p.name != "__MACOSX"]

    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]

    return temp_dir


def download_release(info: UpdateInfo, timeout: float = 30.0) -> Path:
    if not info.asset_url:
        raise RuntimeError(
            f"Im Release v{info.latest_version} wurde kein CTSVision-ZIP gefunden."
        )

    temp_root = Path(tempfile.mkdtemp(prefix="ctsvision_update_"))
    zip_path = temp_root / (info.asset_name or f"CTSVision_v{info.latest_version}.zip")

    request = urllib.request.Request(
        info.asset_url,
        headers={"User-Agent": f"CTSVision/{CURRENT_VERSION}"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        with zip_path.open("wb") as target:
            shutil.copyfileobj(response, target)

    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError("Die heruntergeladene Datei ist kein gültiges ZIP-Archiv.")

    return zip_path


def launch_installer(
    *,
    zip_path: Path,
    install_dir: Path,
    current_version: str,
    latest_version: str,
    parent_pid: int,
) -> None:
    subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--apply",
            str(zip_path),
            "--install-dir",
            str(install_dir),
            "--current-version",
            current_version,
            "--latest-version",
            latest_version,
            "--parent-pid",
            str(parent_pid),
        ],
        cwd=str(install_dir),
        start_new_session=True,
    )


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_parent_exit(pid: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout

    while _pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.25)

    if _pid_exists(pid):
        raise RuntimeError(
            "CTSVision wurde nicht rechtzeitig beendet. Update abgebrochen."
        )


def _ensure_script_permissions(install_dir: Path) -> None:
    """
    Stellt nach einem ZIP-Update die Linux-Ausführungsrechte der
    Start-/Installationsskripte wieder her.
    """

    for script_name in ("start.sh", "install.sh"):
        script = install_dir / script_name

        if not script.exists():
            continue

        current_mode = script.stat().st_mode
        script.chmod(current_mode | 0o111)


def _restart_ctsvision(install_dir: Path) -> None:
    automation = install_dir / "automation.py"
    automation_gui = install_dir / "automation_gui.py"

    target = automation if automation.exists() else automation_gui

    if not target.exists():
        raise RuntimeError("Keine startbare CTSVision-Datei gefunden.")

    subprocess.Popen(
        [sys.executable, str(target)],
        cwd=str(install_dir),
        start_new_session=True,
    )


def apply_update(
    *,
    zip_path: Path,
    install_dir: Path,
    current_version: str,
    latest_version: str,
    parent_pid: int,
) -> int:
    install_dir = install_dir.resolve()
    zip_path = zip_path.resolve()

    _wait_for_parent_exit(parent_pid)

    backup_root = install_dir / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = backup_root / f"CTSVision_v{current_version}_{timestamp}"

    temp_extract = Path(tempfile.mkdtemp(prefix="ctsvision_extract_"))
    backup_created = False

    try:
        _backup_managed_files(install_dir, backup_dir)
        backup_created = True

        release_root = _extract_release_root(zip_path, temp_extract)

        if not (release_root / "automation_gui.py").exists():
            raise RuntimeError("Release-ZIP enthält keine automation_gui.py.")

        _copy_release(release_root, install_dir)

        # ZIP-Archive erhalten Linux-Ausführungsrechte nicht immer zuverlässig.
        # Deshalb setzen wir sie nach jedem Update ausdrücklich wieder.
        _ensure_script_permissions(install_dir)

        _restart_ctsvision(install_dir)
        return 0

    except Exception as exc:
        if backup_created:
            try:
                _restore_backup(backup_dir, install_dir)
            except Exception as rollback_exc:
                print(f"Rollback fehlgeschlagen: {rollback_exc}", file=sys.stderr)
                print(f"Update-Fehler: {exc}", file=sys.stderr)
                return 3

        print(f"Update fehlgeschlagen: {exc}", file=sys.stderr)

        try:
            _restart_ctsvision(install_dir)
        except Exception:
            pass

        return 2

    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)
        shutil.rmtree(zip_path.parent, ignore_errors=True)


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply")
    parser.add_argument("--install-dir")
    parser.add_argument("--current-version")
    parser.add_argument("--latest-version")
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()

    if not args.apply:
        return 0

    return apply_update(
        zip_path=Path(args.apply),
        install_dir=Path(args.install_dir),
        current_version=str(args.current_version),
        latest_version=str(args.latest_version),
        parent_pid=int(args.parent_pid),
    )


if __name__ == "__main__":
    raise SystemExit(_main())
