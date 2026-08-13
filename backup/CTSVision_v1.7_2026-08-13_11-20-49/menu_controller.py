from __future__ import annotations

import time
from collections.abc import Callable

from mouse_control import click_reference_center
from navigator import Navigator
from vision import Vision


class MenuControllerError(RuntimeError):
    """Fehler beim Öffnen oder Schließen eines Elite-Menüs."""


class MenuController:
    """
    Steuert Wechsel zwischen verschiedenen Elite-Menüs.

    Aufgaben:
        - Öffnungstasten wie SPACE oder BACKSPACE senden
        - Ladezeiten abwarten
        - neue Menüs per Bilderkennung bestätigen
        - bei Fehlern sicher zurückgehen und erneut versuchen
    """

    def __init__(
        self,
        vision: Vision,
        navigator: Navigator,
        press_key: Callable[[str], None],
    ) -> None:
        self.vision = vision
        self.navigator = navigator
        self.press_key = press_key

    def wait_for_menu(
        self,
        *,
        prefix: str,
        timeout: float = 8.0,
        poll_interval: float = 0.25,
        extra_width: int = 200,
        extra_height: int = 200,
    ) -> tuple[str, float]:
        """
        Wartet, bis ein Zustand der gewünschten Referenzgruppe
        sicher erkannt wurde.
        """

        if not prefix:
            raise ValueError("Für die Menüerkennung wurde kein Präfix angegeben.")

        if timeout <= 0:
            raise ValueError("Das Zeitlimit muss größer als 0 sein.")

        if poll_interval <= 0:
            raise ValueError("Das Prüfintervall muss größer als 0 sein.")

        if extra_width < 0 or extra_height < 0:
            raise ValueError("Die zusätzlichen Suchgrößen dürfen nicht negativ sein.")

        deadline = time.monotonic() + timeout
        last_similarity = 0.0

        while time.monotonic() < deadline:
            state, similarity = self.vision.get_state(
                prefix=prefix,
                extra_width=extra_width,
                extra_height=extra_height,
            )

            last_similarity = similarity

            if state is not None:
                print(
                    f"MenuController: Zustand erkannt: {state} "
                    f"({similarity * 100:.2f} %)"
                )
                return state, similarity

            time.sleep(poll_interval)

        raise MenuControllerError(
            f"Kein Zustand mit Präfix '{prefix}' wurde innerhalb "
            f"von {timeout:.1f} Sekunden sicher erkannt. "
            f"Bester Wert: {last_similarity * 100:.2f} %"
        )

    def open_menu(
        self,
        *,
        key: str,
        prefix: str,
        loading_time: float = 5.0,
        timeout: float = 8.0,
        poll_interval: float = 0.25,
        extra_width: int = 200,
        extra_height: int = 200,
    ) -> tuple[str, float]:
        """
        Sendet eine Taste und wartet anschließend,
        bis das neue Menü sicher erkannt wurde.
        """

        if not key or not key.strip():
            raise ValueError("Für den Menüwechsel wurde keine Taste angegeben.")

        if loading_time < 0:
            raise ValueError("Die Ladezeit darf nicht negativ sein.")

        print(f"MenuController: Taste '{key.upper()}' senden.")

        self.press_key(key)

        if loading_time > 0:
            print(
                f"MenuController: warte {loading_time:.1f} Sekunden "
                "auf den Menüaufbau ..."
            )
            time.sleep(loading_time)

        return self.wait_for_menu(
            prefix=prefix,
            timeout=timeout,
            poll_interval=poll_interval,
            extra_width=extra_width,
            extra_height=extra_height,
        )

    def close_menu(
        self,
        *,
        expected_prefix: str,
        key: str = "BackSpace",
        loading_time: float = 2.0,
        timeout: float = 8.0,
        poll_interval: float = 0.25,
        extra_width: int = 200,
        extra_height: int = 200,
    ) -> tuple[str, float]:
        """Geht mit BACKSPACE zum vorherigen Menü zurück."""

        return self.open_menu(
            key=key,
            prefix=expected_prefix,
            loading_time=loading_time,
            timeout=timeout,
            poll_interval=poll_interval,
            extra_width=extra_width,
            extra_height=extra_height,
        )

    def open_galaxy_map(
        self,
        *,
        max_attempts: int = 3,
        action_timeout: float = 3.0,
    ) -> bool:
        """
        Öffnet aus dem Carrier-Management die Galaxiekarte.

        Ablauf:
            1. NAVIGATION sicher erreichen
            2. SPACE drücken
            3. unteren Galaxiekarten-Button prüfen
            4. bei A oder B erneut SPACE drücken
            5. bei Fehler BACKSPACE und neuen Versuch starten

        Die beiden gültigen Aktionszustände sind:
            galaxiekarte_action_button_a
            galaxiekarte_action_button_b
        """

        valid_action_states = {
            "galaxiekarte_action_button_a",
            "galaxiekarte_action_button_b",
        }

        for attempt in range(1, max_attempts + 1):
            print()
            print(
                f"MenuController: Galaxiekarte öffnen – "
                f"Versuch {attempt}/{max_attempts}"
            )

            # Zuerst den linken Menüpunkt NAVIGATION sicher erreichen.
            self.navigator.goto(
                "carrier_management",
                "carrier_management_navigation",
                max_actions=14,
                state_timeout=4.0,
            )

            # Erster SPACE: Fokus auf den unteren Button setzen
            # beziehungsweise die Navigationsseite aktivieren.
            print("MenuController: erster SPACE für " "GALAXIEKARTE AUFRUFEN.")
            self.press_key("space")

            try:
                action_state, similarity = self.wait_for_menu(
                    prefix="galaxiekarte_action_button_",
                    timeout=action_timeout,
                    poll_interval=0.20,
                    extra_width=0,
                    extra_height=0,
                )

            except MenuControllerError as exc:
                print("MenuController: Galaxiekarten-Button " "nicht sicher erkannt.")
                print(f"MenuController: {exc}")

                self._recover_carrier_management()
                continue

            if action_state not in valid_action_states:
                print("MenuController: unerwarteter Aktionszustand: " f"{action_state}")

                self._recover_carrier_management()
                continue

            print(
                "MenuController: gültiger Galaxiekarten-Button "
                f"erkannt: {action_state} "
                f"({similarity * 100:.2f} %)"
            )

            # Beide Zustände A und B dürfen mit SPACE bestätigt werden.
            print("MenuController: zweiter SPACE – " "Galaxiekarte wird geöffnet.")
            self.press_key("space")

            return True

        raise MenuControllerError(
            "Die Galaxiekarte konnte nach "
            f"{max_attempts} Versuchen nicht geöffnet werden."
        )

    def open_galaxy_search(
        self,
        *,
        max_attempts: int = 3,
        search_timeout: float = 3.0,
    ) -> tuple[str, float]:
        """
        Aktiviert in der geöffneten Galaxiekarte das Suchfeld.

        Ablauf:
            1. Pfeiltaste nach oben drücken
            2. SPACE drücken
            3. aktives Suchfeld anhand der Referenzen A/B prüfen
            4. bei Fehler mit BACKSPACE zu Menü 3 zurückkehren
            5. Galaxiekarte erneut öffnen und neuen Versuch starten

        Rückgabe:
            - erkannter Suchfeldzustand
            - Ähnlichkeit
        """

        valid_search_states = {
            "galaxiekarte_search_input_active_a",
            "galaxiekarte_search_input_active_b",
        }

        for attempt in range(1, max_attempts + 1):
            print()
            print(
                "MenuController: Suchfeld öffnen – " f"Versuch {attempt}/{max_attempts}"
            )

            # Suchfeld direkt per Maus anklicken.
            print("MenuController: Suchfeld wird per Maus aktiviert.")

            click_x, click_y = click_reference_center(
                "galaxiekarte_search_input_active_a",
                move_delay=0.30,
                after_delay=0.75,
            )

            print(
                "MenuController: Suchfeld angeklickt bei " f"X={click_x}, Y={click_y}."
            )

            try:
                state, similarity = self.wait_for_menu(
                    prefix="galaxiekarte_search_input_active_",
                    timeout=search_timeout,
                    poll_interval=0.15,
                    extra_width=0,
                    extra_height=0,
                )

            except MenuControllerError as exc:
                print("MenuController: Suchfeld wurde nicht " "sicher erkannt.")
                print(f"MenuController: {exc}")

                if attempt >= max_attempts:
                    break

                self._restart_galaxy_map()
                continue

            if state in valid_search_states:
                print(
                    "MenuController: Suchfeld ist aktiv: "
                    f"{state} ({similarity * 100:.2f} %)"
                )

                return state, similarity

            print("MenuController: unerwarteter Suchzustand: " f"{state}")

            if attempt < max_attempts:
                self._restart_galaxy_map()

        raise MenuControllerError(
            "Das Suchfeld der Galaxiekarte konnte nach "
            f"{max_attempts} Versuchen nicht aktiviert werden."
        )

    def _restart_galaxy_map(self) -> None:
        """
        Verlässt die Galaxiekarte mit BACKSPACE,
        erkennt Menü 3 erneut und öffnet anschließend
        die Galaxiekarte wieder.
        """

        print("MenuController: BACKSPACE – " "zurück zum Carrier-Management.")

        self.press_key("backspace")

        # Rückkehr und Aufbau von Menü 3 abwarten.
        time.sleep(5.0)

        self.wait_for_menu(
            prefix="carrier_management_",
            timeout=8.0,
            poll_interval=0.25,
            extra_width=0,
            extra_height=0,
        )

        # NAVIGATION erneut ansteuern und Galaxiekarte öffnen.
        self.open_galaxy_map(
            max_attempts=3,
            action_timeout=3.0,
        )

        # Der Aufbau der Galaxiekarte benötigt etwas Zeit.
        time.sleep(5.0)

    def _recover_carrier_management(self) -> None:
        """
        Bricht die fehlerhafte Aktion mit BACKSPACE ab,
        wartet auf Menü 3 und erkennt es anschließend neu.
        """

        print(
            "MenuController: Abbruch mit BACKSPACE und "
            "Rückkehr zum Carrier-Management."
        )

        self.press_key("BackSpace")

        # Kurze Rückkehranimation abwarten.
        time.sleep(2.0)

        self.wait_for_menu(
            prefix="carrier_management_",
            timeout=6.0,
            poll_interval=0.25,
            extra_width=0,
            extra_height=0,
        )
