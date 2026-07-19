from __future__ import annotations

import json
import time

from Xlib import X, display
from Xlib.ext import xtest

from app_paths import CONFIG_FILE
from window_finder import find_elite_window


class MouseControlError(RuntimeError):
    """
    Fehler bei der Maussteuerung.
    """


def _load_reference(reference_name: str) -> dict:
    """
    Lädt die Koordinaten eines Referenzbildes aus config.json.
    """

    if not CONFIG_FILE.exists():
        raise MouseControlError(f"config.json wurde nicht gefunden: {CONFIG_FILE}")

    try:
        with CONFIG_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = json.load(file)

    except (OSError, json.JSONDecodeError) as exc:
        raise MouseControlError(
            f"config.json konnte nicht gelesen werden: {exc}"
        ) from exc

    references = config.get("references")

    if not isinstance(references, dict):
        raise MouseControlError("In config.json fehlt der Bereich „references“.")

    reference = references.get(reference_name)

    if not isinstance(reference, dict):
        raise MouseControlError(f"Referenz nicht gefunden: {reference_name}")

    required_keys = (
        "x",
        "y",
        "width",
        "height",
    )

    for key in required_keys:
        if key not in reference:
            raise MouseControlError(f"Bei Referenz „{reference_name}“ fehlt „{key}“.")

    return reference


def _get_window_position(
    window,
) -> tuple[int, int]:
    """
    Ermittelt die absolute Position des Elite-Fensters
    auf dem gesamten virtuellen Desktop.

    Unterstützt sowohl Objekte mit x/y beziehungsweise
    left/top als auch Dictionary-Rückgaben.
    """

    if isinstance(window, dict):
        window_x = window.get(
            "x",
            window.get("left"),
        )

        window_y = window.get(
            "y",
            window.get("top"),
        )

    else:
        window_x = getattr(
            window,
            "x",
            None,
        )

        window_y = getattr(
            window,
            "y",
            None,
        )

        if window_x is None:
            window_x = getattr(
                window,
                "left",
                None,
            )

        if window_y is None:
            window_y = getattr(
                window,
                "top",
                None,
            )

    if window_x is None or window_y is None:
        raise MouseControlError(
            "Die Position des Elite-Fensters konnte " "nicht bestimmt werden."
        )

    return int(window_x), int(window_y)


def get_reference_center(
    reference_name: str,
) -> tuple[int, int]:
    """
    Ermittelt den absoluten Desktop-Mittelpunkt
    eines Referenzbereichs im Elite-Fenster.

    Die Werte aus config.json sind relativ zum Elite-Fenster.
    Für die Mausbewegung wird die absolute Fensterposition
    auf dem virtuellen Desktop addiert.
    """

    reference = _load_reference(reference_name)

    reference_x = int(reference["x"])
    reference_y = int(reference["y"])
    width = int(reference["width"])
    height = int(reference["height"])

    window = find_elite_window()

    if window is None:
        raise MouseControlError("Elite-Fenster wurde nicht gefunden.")

    window_x, window_y = _get_window_position(window)

    center_x = window_x + reference_x + width // 2

    center_y = window_y + reference_y + height // 2

    return center_x, center_y


def move_mouse(
    x: int,
    y: int,
    after_delay: float = 0.50,
) -> None:
    """
    Bewegt den Mauszeiger auf eine absolute
    Bildschirmposition des virtuellen Desktops.
    """

    x_display = display.Display()

    try:
        root = x_display.screen().root

        xtest.fake_input(
            x_display,
            X.MotionNotify,
            x=x,
            y=y,
            root=root,
        )

        x_display.sync()

        time.sleep(after_delay)

    finally:
        x_display.close()


def left_click(
    after_delay: float = 1.00,
) -> None:
    """
    Führt einen linken Mausklick aus.
    """

    x_display = display.Display()

    try:
        xtest.fake_input(
            x_display,
            X.ButtonPress,
            1,
        )

        x_display.sync()

        time.sleep(0.10)

        xtest.fake_input(
            x_display,
            X.ButtonRelease,
            1,
        )

        x_display.sync()

        time.sleep(after_delay)

    finally:
        x_display.close()


def move_to_reference_center(
    reference_name: str,
    after_delay: float = 0.75,
) -> tuple[int, int]:
    """
    Bewegt die Maus in die Mitte eines Referenzbereichs,
    ohne einen Mausklick auszuführen.

    Rückgabewert:
        Absolute X-/Y-Position auf dem virtuellen Desktop.
    """

    x, y = get_reference_center(reference_name)

    move_mouse(
        x=x,
        y=y,
        after_delay=after_delay,
    )

    return x, y


def click_reference_center(
    reference_name: str,
    move_delay: float = 0.75,
    after_delay: float = 3.00,
) -> tuple[int, int]:
    """
    Bewegt die Maus in die Mitte eines Referenzbereichs
    und führt dort einen linken Mausklick aus.

    Rückgabewert:
        Absolute X-/Y-Position auf dem virtuellen Desktop.
    """

    x, y = get_reference_center(reference_name)

    move_mouse(
        x=x,
        y=y,
        after_delay=move_delay,
    )

    left_click(
        after_delay=after_delay,
    )

    return x, y
