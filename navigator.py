from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from project_store import load_navigation
from vision import Vision


class NavigationError(RuntimeError):
    """Fehler während einer zustandsbasierten Navigation."""


class Navigator:
    """
    Zustandsbasierte Navigation durch Elite-Menüs.

    Der Navigator:
        1. lädt einen Navigationsbereich aus navigation.json,
        2. erkennt den aktuellen Zustand,
        3. berechnet den kürzesten Weg zum Ziel,
        4. drückt genau eine Taste,
        5. prüft anschließend erneut den Bildschirm,
        6. plant bei Abweichungen neu.
    """

    def __init__(
        self,
        vision: Vision,
        press_key: Callable[[str], None],
    ) -> None:
        self.vision = vision
        self.press_key = press_key
        self.navigation = load_navigation()

    def reload(self) -> None:
        """
        Lädt navigation.json neu.

        Dadurch können Änderungen an der Datei übernommen werden,
        ohne den Navigator-Code zu verändern.
        """

        self.navigation = load_navigation()

    def _get_area(
        self,
        area_name: str,
    ) -> tuple[
        str,
        dict[str, dict[str, str]],
        int,
        int,
    ]:
        """
        Liefert Präfix, Zustandsgraph und Suchränder
        eines Navigationsbereichs.

        Rückgabe:
            tuple:
                - Referenzpräfix
                - Zustandsgraph
                - zusätzlicher Suchbereich in der Breite
                - zusätzlicher Suchbereich in der Höhe
        """

        area = self.navigation.get(area_name)

        if area is None:
            raise NavigationError(f"Navigationsbereich '{area_name}' nicht gefunden.")

        if not isinstance(area, dict):
            raise NavigationError(f"Navigationsbereich '{area_name}' ist ungültig.")

        prefix = area.get("prefix")
        states = area.get("states")

        extra_width = area.get("extra_width", 200)
        extra_height = area.get("extra_height", 200)

        if not isinstance(prefix, str) or not prefix:
            raise NavigationError(
                f"Im Navigationsbereich '{area_name}' " "fehlt ein gültiges Präfix."
            )

        if not isinstance(states, dict) or not states:
            raise NavigationError(
                f"Im Navigationsbereich '{area_name}' "
                "fehlt ein gültiger Zustandsgraph."
            )

        if not isinstance(extra_width, int) or extra_width < 0:
            raise NavigationError(f"'extra_width' in '{area_name}' ist ungültig.")

        if not isinstance(extra_height, int) or extra_height < 0:
            raise NavigationError(f"'extra_height' in '{area_name}' ist ungültig.")

        graph: dict[str, dict[str, str]] = {}

        for state_name, transitions in states.items():
            if not isinstance(state_name, str):
                raise NavigationError(f"Ungültiger Zustandsname in '{area_name}'.")

            if not isinstance(transitions, dict):
                raise NavigationError(
                    f"Übergänge von '{state_name}' " "müssen ein JSON-Objekt sein."
                )

            graph[state_name] = {}

            for key, next_state in transitions.items():
                if not isinstance(key, str) or not isinstance(next_state, str):
                    raise NavigationError(f"Ungültiger Übergang bei '{state_name}'.")

                graph[state_name][key.lower()] = next_state

        return (
            prefix,
            graph,
            extra_width,
            extra_height,
        )

    def _find_path(
        self,
        graph: dict[str, dict[str, str]],
        start_state: str,
        target_state: str,
    ) -> list[tuple[str, str]]:
        """
        Berechnet den kürzesten Weg durch den Zustandsgraphen.

        Rückgabe:
            Liste aus:
                - zu drückende Taste
                - erwarteter Folgezustand
        """

        if start_state == target_state:
            return []

        queue: deque[tuple[str, list[tuple[str, str]]]] = deque()

        queue.append((start_state, []))

        visited = {start_state}

        while queue:
            current_state, current_path = queue.popleft()

            transitions = graph.get(current_state, {})

            for key, next_state in transitions.items():
                if next_state in visited:
                    continue

                new_path = current_path + [(key, next_state)]

                if next_state == target_state:
                    return new_path

                visited.add(next_state)
                queue.append((next_state, new_path))

        raise NavigationError(
            f"Kein Navigationsweg von "
            f"'{start_state}' nach '{target_state}' gefunden."
        )

    def _wait_for_state(
        self,
        *,
        prefix: str,
        expected_state: str,
        extra_width: int,
        extra_height: int,
        timeout: float = 3.0,
        poll_interval: float = 0.15,
    ) -> tuple[str | None, float]:
        """
        Wartet auf eine Zustandsänderung.

        Der erwartete Zustand wird sofort bestätigt.
        Wird stattdessen ein anderer sicherer Zustand erkannt,
        wird dieser ebenfalls sofort zurückgegeben, damit der
        Navigator den Weg neu berechnen kann.
        """

        deadline = time.monotonic() + timeout

        last_state: str | None = None
        last_similarity = 0.0

        while time.monotonic() < deadline:
            state, similarity = self.vision.get_state(
                prefix=prefix,
                extra_width=extra_width,
                extra_height=extra_height,
            )

            last_state = state
            last_similarity = similarity

            if state == expected_state:
                return state, similarity

            # Ein anderer Zustand wurde sicher erkannt.
            # Nicht weiter unnötig prüfen, sondern sofort
            # an goto() zurückgeben und dort neu planen.
            if state is not None:
                return state, similarity

            time.sleep(poll_interval)

        return last_state, last_similarity

    def goto(
        self,
        area_name: str,
        target_state: str,
        *,
        max_actions: int = 12,
        state_timeout: float = 3.0,
    ) -> bool:
        """
        Navigiert innerhalb eines definierten Menübereichs
        sicher zum gewünschten Zustand.

        Beispiel:
            navigator.goto(
                "carrier_management",
                "carrier_management_navigation",
            )
        """

        (
            prefix,
            graph,
            extra_width,
            extra_height,
        ) = self._get_area(area_name)

        if target_state not in graph:
            raise NavigationError(
                f"Unbekannter Zielzustand "
                f"'{target_state}' im Bereich '{area_name}'."
            )

        actions_used = 0

        while actions_used < max_actions:
            current_state, similarity = self.vision.get_state(
                prefix=prefix,
                extra_width=extra_width,
                extra_height=extra_height,
            )

            if current_state is None:
                raise NavigationError(
                    "Der aktuelle Elite-Zustand konnte nicht "
                    f"sicher erkannt werden. "
                    f"Bester Wert: {similarity * 100:.2f} %"
                )

            if current_state not in graph:
                raise NavigationError(
                    f"Der erkannte Zustand '{current_state}' "
                    f"ist im Bereich '{area_name}' "
                    "nicht im Navigationsgraphen eingetragen."
                )

            print(
                f"Navigator [{area_name}]: "
                f"aktueller Zustand: {current_state} "
                f"({similarity * 100:.2f} %)"
            )

            if current_state == target_state:
                print(
                    f"Navigator [{area_name}]: "
                    f"Ziel bereits erreicht: {target_state}"
                )
                return True

            path = self._find_path(
                graph=graph,
                start_state=current_state,
                target_state=target_state,
            )

            if not path:
                return True

            key, expected_state = path[0]

            print(
                f"Navigator [{area_name}]: "
                f"Taste '{key.upper()}' drücken; "
                f"erwartet wird '{expected_state}'."
            )

            self.press_key(key)
            actions_used += 1

            detected_state, detected_similarity = self._wait_for_state(
                prefix=prefix,
                expected_state=expected_state,
                extra_width=extra_width,
                extra_height=extra_height,
                timeout=state_timeout,
            )

            if detected_state == expected_state:
                print(
                    f"Navigator [{area_name}]: "
                    f"Übergang bestätigt: {expected_state} "
                    f"({detected_similarity * 100:.2f} %)"
                )
                continue

            if detected_state is not None:
                print(
                    f"Navigator [{area_name}]: "
                    "anderer bekannter Zustand erkannt: "
                    f"{detected_state}. "
                    "Weg wird neu berechnet."
                )
                continue

            raise NavigationError(
                f"Nach Taste '{key.upper()}' wurde der erwartete "
                f"Zustand '{expected_state}' nicht erkannt. "
                f"Bester Wert: "
                f"{detected_similarity * 100:.2f} %"
            )

        raise NavigationError(
            f"Ziel '{target_state}' wurde nach "
            f"{max_actions} Tastendrücken nicht erreicht."
        )
