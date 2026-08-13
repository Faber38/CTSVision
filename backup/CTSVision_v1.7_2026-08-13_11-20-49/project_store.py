from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app_paths import (
    APP_DIR,
    CONFIG_FILE,
    NAVIGATION_DIR,
    NAVIGATION_FILE,
    REFERENCE_CATALOG_FILE,
)

PROJECT_DIR = APP_DIR

CONFIG_PATH = CONFIG_FILE
REFERENCE_CATALOG_PATH = REFERENCE_CATALOG_FILE

NAVIGATION_PATH = NAVIGATION_FILE


def create_empty_config() -> dict[str, Any]:
    """Erzeugt eine leere CTS-Vision-Konfiguration."""

    return {
        "version": 1,
        "references": {},
    }


def create_empty_navigation() -> dict[str, Any]:
    """Erzeugt eine leere Navigationskonfiguration."""

    return {}


def _load_json_file(
    path: Path,
    *,
    description: str,
) -> dict[str, Any]:
    """Lädt eine JSON-Datei und prüft deren Grundstruktur."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"{description} konnte nicht geladen werden: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} enthält kein gültiges JSON-Objekt.")

    return data


def _save_json_file(
    path: Path,
    data: dict[str, Any],
) -> None:
    """Speichert ein Dictionary formatiert als JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def load_reference_catalog() -> list[dict[str, Any]]:
    """Lädt und validiert den Katalog aller benötigten Referenzbilder."""

    try:
        catalog = json.loads(
            REFERENCE_CATALOG_PATH.read_text(
                encoding="utf-8",
            )
        )

    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Referenzkatalog wurde nicht gefunden: " f"{REFERENCE_CATALOG_PATH}"
        ) from exc

    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"Referenzkatalog konnte nicht geladen werden: {exc}"
        ) from exc

    if not isinstance(catalog, list):
        raise RuntimeError("reference_catalog.json muss eine JSON-Liste enthalten.")

    valid_entries: list[dict[str, Any]] = []

    for index, entry in enumerate(
        catalog,
        start=1,
    ):
        if not isinstance(entry, dict):
            raise RuntimeError(f"Katalogeintrag {index} ist kein JSON-Objekt.")

        name = str(
            entry.get(
                "name",
                "",
            )
        ).strip()

        filename = str(
            entry.get(
                "filename",
                "",
            )
        ).strip()

        template = str(
            entry.get(
                "template",
                "",
            )
        ).strip()

        description = str(
            entry.get(
                "description",
                "",
            )
        ).strip()

        group = (
            str(
                entry.get(
                    "group",
                    "Sonstige",
                )
            ).strip()
            or "Sonstige"
        )

        title = (
            str(
                entry.get(
                    "title",
                    name,
                )
            ).strip()
            or name
        )

        try:
            group_order = int(
                entry.get(
                    "group_order",
                    99,
                )
            )

        except (TypeError, ValueError):
            group_order = 99

        if not name:
            raise RuntimeError(f"Katalogeintrag {index} enthält keinen Namen.")

        if not filename:
            raise RuntimeError(f"Katalogeintrag '{name}' enthält keinen Dateinamen.")

        if not template:
            raise RuntimeError(f"Katalogeintrag '{name}' enthält keinen Template-Pfad.")

        valid_entries.append(
            {
                "name": name,
                "filename": filename,
                "template": template,
                "description": description,
                "group": group,
                "group_order": group_order,
                "title": title,
            }
        )

    valid_entries.sort(
        key=lambda item: (
            item["group_order"],
            item["group"].casefold(),
            item["title"].casefold(),
        )
    )

    return valid_entries


def load_config() -> dict[str, Any]:
    """Lädt die Referenzkonfiguration."""

    if not CONFIG_PATH.exists():
        config = create_empty_config()

        save_config(
            config,
        )

        return config

    data = _load_json_file(
        CONFIG_PATH,
        description="Konfiguration",
    )

    data.setdefault(
        "version",
        1,
    )

    data.setdefault(
        "references",
        {},
    )

    if not isinstance(
        data["references"],
        dict,
    ):
        raise RuntimeError(
            "Der Eintrag 'references' in config.json " "muss ein JSON-Objekt sein."
        )

    return data


def save_config(
    config: dict[str, Any],
) -> None:
    """Speichert die Referenzkonfiguration."""

    _save_json_file(
        CONFIG_PATH,
        config,
    )


def load_navigation() -> dict[str, Any]:
    """Lädt die Navigationsdefinitionen."""

    if not NAVIGATION_PATH.exists():
        navigation = create_empty_navigation()

        save_navigation(
            navigation,
        )

        return navigation

    navigation = _load_json_file(
        NAVIGATION_PATH,
        description="Navigation",
    )

    return navigation


def save_navigation(
    navigation: dict[str, Any],
) -> None:
    """Speichert die Navigationsdefinitionen."""

    _save_json_file(
        NAVIGATION_PATH,
        navigation,
    )


def save_reference(
    *,
    name: str,
    x: int,
    y: int,
    width: int,
    height: int,
    image_filename: str,
) -> None:
    """Speichert oder aktualisiert eine Referenz."""

    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Der Referenzname darf nicht leer sein.")

    if width <= 0 or height <= 0:
        raise ValueError("Breite und Höhe müssen größer als 0 sein.")

    config = load_config()

    config["references"][clean_name] = {
        "x": int(x),
        "y": int(y),
        "width": int(width),
        "height": int(height),
        "image": str(image_filename),
    }

    save_config(
        config,
    )
