from __future__ import annotations

import json
from typing import Any

from app_paths import SETTINGS_FILE
from journal_monitor import DEFAULT_JOURNAL_DIRECTORY

DEFAULT_SETTINGS: dict[str, Any] = {
    "journal_directory": str(DEFAULT_JOURNAL_DIRECTORY),
    "last_route": "",
}


def load_settings() -> dict[str, Any]:
    """
    Lädt die gespeicherten Programmeinstellungen.

    Fehlt die Datei oder ist sie beschädigt, werden die
    Standardeinstellungen zurückgegeben.
    """

    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with SETTINGS_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            loaded_settings = json.load(handle)

    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    if not isinstance(loaded_settings, dict):
        return DEFAULT_SETTINGS.copy()

    settings = DEFAULT_SETTINGS.copy()
    settings.update(loaded_settings)

    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """
    Speichert die Programmeinstellungen als JSON-Datei.
    """

    try:
        SETTINGS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with SETTINGS_FILE.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                settings,
                handle,
                indent=4,
                ensure_ascii=False,
            )

    except OSError as exc:
        raise RuntimeError(
            f"Einstellungen konnten nicht gespeichert werden: {exc}"
        ) from exc
