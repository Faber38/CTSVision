from __future__ import annotations

import time

from Xlib import X, XK, display
from Xlib.ext import xtest

from window_finder import (
    activate_window,
    find_elite_window,
    get_active_window_id,
)


class KeyboardError(RuntimeError):
    """Fehler beim Senden von Tastatureingaben."""


KEY_ALIASES: dict[str, str] = {
    "up": "Up",
    "arrowup": "Up",
    "pfeiloben": "Up",
    "down": "Down",
    "arrowdown": "Down",
    "pfeilunten": "Down",
    "left": "Left",
    "arrowleft": "Left",
    "pfeillinks": "Left",
    "right": "Right",
    "arrowright": "Right",
    "pfeilrechts": "Right",
    "space": "space",
    "backspace": "BackSpace",
    "enter": "Return",
    "return": "Return",
    "escape": "Escape",
    "esc": "Escape",
}


TEXT_CHARACTER_KEYS: dict[str, str] = {
    " ": "space",
    "-": "minus",
    ".": "period",
    ",": "comma",
    "/": "slash",
}


def _ensure_elite_focus() -> None:
    """
    Sucht das Elite-Fenster und stellt sicher,
    dass es den Tastaturfokus besitzt.
    """

    window = find_elite_window()

    if window is None:
        raise KeyboardError("Elite-Fenster wurde nicht gefunden.")

    if get_active_window_id() != window.window_id:
        activated = activate_window(window)

        if not activated:
            raise KeyboardError("Elite-Fenster konnte nicht aktiviert werden.")

        time.sleep(0.15)

    if get_active_window_id() != window.window_id:
        raise KeyboardError("Elite-Fenster besitzt nicht den Tastaturfokus.")


def _get_keycode(
    connection: display.Display,
    key_name: str,
) -> int:
    """
    Ermittelt für einen X11-Tastennamen den Keycode.
    """

    keysym = XK.string_to_keysym(key_name)

    if keysym == 0:
        keysym = XK.string_to_keysym(key_name.lower())

    if keysym == 0:
        raise KeyboardError(f"Unbekannte Taste: '{key_name}'.")

    keycode = connection.keysym_to_keycode(keysym)

    if keycode == 0:
        raise KeyboardError(f"Für Taste '{key_name}' " "wurde kein Keycode gefunden.")

    return keycode


def _send_keycode(
    connection: display.Display,
    keycode: int,
    *,
    hold_time: float,
    use_shift: bool = False,
) -> None:
    """
    Sendet einen einzelnen Keycode.

    Bei use_shift=True wird gleichzeitig die
    linke Umschalttaste gehalten.
    """

    shift_keycode = 0

    if use_shift:
        shift_keycode = _get_keycode(
            connection,
            "Shift_L",
        )

        xtest.fake_input(
            connection,
            X.KeyPress,
            shift_keycode,
        )

    xtest.fake_input(
        connection,
        X.KeyPress,
        keycode,
    )

    connection.sync()
    time.sleep(hold_time)

    xtest.fake_input(
        connection,
        X.KeyRelease,
        keycode,
    )

    if use_shift:
        xtest.fake_input(
            connection,
            X.KeyRelease,
            shift_keycode,
        )

    connection.sync()


def press_key(
    key: str,
    *,
    hold_time: float = 0.20,
    after_delay: float = 0.10,
) -> None:
    """
    Aktiviert zuerst sicher das Elite-Fenster
    und sendet danach genau einen Tastendruck.

    Beispiele:
        press_key("w")
        press_key("up")
        press_key("left")
        press_key("space")
        press_key("backspace")
        press_key("enter")
    """

    if not key or not key.strip():
        raise ValueError("Es wurde keine Taste angegeben.")

    _ensure_elite_focus()

    requested_key = key.strip()
    alias_key = requested_key.lower()

    key_name = KEY_ALIASES.get(
        alias_key,
        requested_key,
    )

    connection = display.Display()

    try:
        keycode = _get_keycode(
            connection,
            key_name,
        )

        _send_keycode(
            connection,
            keycode,
            hold_time=hold_time,
        )

        if after_delay > 0:
            time.sleep(after_delay)

    finally:
        connection.close()


def type_text(
    text: str,
    *,
    character_hold_time: float = 0.04,
    character_delay: float = 0.04,
    after_delay: float = 0.30,
) -> None:
    """
    Schreibt Text Zeichen für Zeichen in das aktuell
    aktive Eingabefeld von Elite Dangerous.

    Unterstützt werden:
        - Groß- und Kleinbuchstaben
        - Ziffern
        - Leerzeichen
        - Bindestrich
        - Punkt
        - Komma
        - Schrägstrich

    Beispiel:
        type_text("Smojai JG-Y b1-0")
    """

    if not text:
        raise ValueError("Es wurde kein Text zum Schreiben angegeben.")

    _ensure_elite_focus()

    connection = display.Display()

    try:
        for character in text:

            use_shift = False

            if character.isalpha():
                key_name = character.lower()
                use_shift = character.isupper()

            elif character.isdigit():
                key_name = character

            elif character in TEXT_CHARACTER_KEYS:
                key_name = TEXT_CHARACTER_KEYS[character]

            else:
                raise KeyboardError(
                    "Nicht unterstütztes Zeichen im Text: " f"{character!r}"
                )

            keycode = _get_keycode(
                connection,
                key_name,
            )

            _send_keycode(
                connection,
                keycode,
                hold_time=character_hold_time,
                use_shift=use_shift,
            )

            if character_delay > 0:
                time.sleep(character_delay)

        if after_delay > 0:
            time.sleep(after_delay)

    finally:
        connection.close()
