from __future__ import annotations

import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    Liefert das Verzeichnis, in dem CTSVision seine Daten erwartet.

    Entwicklung:
        ~/Projekte/CTSVision

    Kompilierte Version:
        das Verzeichnis neben der ausführbaren CTSVision-Datei
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()

CONFIG_FILE = APP_DIR / "config.json"
SETTINGS_FILE = APP_DIR / "settings.json"
ROUTE_STATE_FILE = APP_DIR / "route_state.json"

REFERENCES_DIR = APP_DIR / "references"
ASSETS_DIR = APP_DIR / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"

CONFIG_DIR = APP_DIR / "config"
REFERENCE_CATALOG_FILE = CONFIG_DIR / "reference_catalog.json"

NAVIGATION_DIR = APP_DIR / "navigation"
NAVIGATION_FILE = NAVIGATION_DIR / "navigation.json"

DEBUG_DIR = APP_DIR / "debug"
