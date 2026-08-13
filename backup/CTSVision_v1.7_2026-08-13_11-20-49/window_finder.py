from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass(slots=True)
class WindowInfo:
    window_id: int
    title: str
    x: int
    y: int
    width: int
    height: int
    screen: int
    desktop: int
    is_visible: bool = True


def _run_xdotool(*args: str) -> str:
    return subprocess.check_output(
        ["xdotool", *args],
        stderr=subprocess.PIPE,
        text=True,
    ).strip()


def _read_geometry(window_id: int) -> dict[str, int]:
    output = _run_xdotool(
        "getwindowgeometry",
        "--shell",
        str(window_id),
    )

    values: dict[str, int] = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key in {"WINDOW", "X", "Y", "WIDTH", "HEIGHT", "SCREEN"}:
            values[key] = int(value)

    return values


def find_elite_windows() -> list[WindowInfo]:
    try:
        output = _run_xdotool(
            "search",
            "--onlyvisible",
            "--name",
            "Elite",
        )
    except subprocess.CalledProcessError:
        return []

    results: list[WindowInfo] = []

    for raw_id in output.splitlines():
        raw_id = raw_id.strip()

        if not raw_id:
            continue

        try:
            window_id = int(raw_id)
            title = _run_xdotool(
                "getwindowname",
                str(window_id),
            )

            # Nur das eigentliche Spielfenster übernehmen.
            if title.strip() != "Elite - Dangerous (CLIENT)":
                continue

            geometry = _read_geometry(window_id)

            results.append(
                WindowInfo(
                    window_id=window_id,
                    title=title,
                    x=geometry["X"],
                    y=geometry["Y"],
                    width=geometry["WIDTH"],
                    height=geometry["HEIGHT"],
                    screen=geometry["SCREEN"],
                    desktop=get_window_desktop(window_id),
                )
            )

        except (
            ValueError,
            KeyError,
            subprocess.CalledProcessError,
        ):
            continue

    return results


def find_elite_window() -> WindowInfo | None:
    windows = find_elite_windows()
    return windows[0] if windows else None


def get_current_desktop() -> int:
    """Liefert die aktuell aktive Arbeitsfläche."""

    output = subprocess.check_output(
        ["xprop", "-root", "_NET_CURRENT_DESKTOP"],
        text=True,
    ).strip()

    return int(output.rsplit("=", 1)[1].strip())


def get_window_desktop(window_id: int) -> int:
    """Liefert die Arbeitsfläche eines Fensters."""

    output = subprocess.check_output(
        ["xprop", "-id", str(window_id), "_NET_WM_DESKTOP"],
        text=True,
    ).strip()

    return int(output.rsplit("=", 1)[1].strip())


def get_active_window_id() -> int | None:
    """Liefert die Fenster-ID des aktuell aktiven Fensters."""

    try:
        output = _run_xdotool("getactivewindow")
    except subprocess.CalledProcessError:
        return None

    if not output:
        return None

    try:
        return int(output)
    except ValueError:
        return None


def activate_window(
    window: WindowInfo,
    *,
    timeout: float = 2.0,
    poll_interval: float = 0.05,
) -> bool:
    """
    Aktiviert das angegebene Fenster und prüft,
    ob es anschließend wirklich den Fokus besitzt.

    Rückgabe:
        True, wenn das Fenster aktiv wurde.
        False, wenn das Zeitlimit abgelaufen ist.
    """

    current_desktop = get_current_desktop()

    if window.desktop != current_desktop:
        raise RuntimeError(
            f"Elite läuft auf Arbeitsfläche {window.desktop + 1}, "
            f"aktuell aktiv ist Arbeitsfläche {current_desktop + 1}."
        )

    try:
        _run_xdotool(
            "windowactivate",
            "--sync",
            str(window.window_id),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Elite-Fenster konnte nicht aktiviert werden.") from exc

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        active_window_id = get_active_window_id()

        if active_window_id == window.window_id:
            return True

        time.sleep(poll_interval)

    return False


def elite_is_on_current_desktop() -> bool:
    window = find_elite_window()

    if window is None:
        return False

    return window.desktop == get_current_desktop()
