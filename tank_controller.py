from __future__ import annotations

from enum import Enum

import re
import time

import numpy as np

from collections.abc import Callable
from pathlib import Path

from capture import capture_window_region
from menu_controller import MenuController
from navigator import Navigator
from ocr import PaddleEngine
from project_store import load_config
from settings_manager import load_settings
from vision import Vision
from window_finder import (
    find_elite_window,
    get_current_desktop,
)


class TankStatus(Enum):
    IDLE = "Bereit"
    RUNNING = "Tankvorgang läuft"
    SUCCESS = "Erfolgreich"
    ERROR = "Fehler"


class TankControllerError(RuntimeError):
    """Fehler während des automatischen Tankablaufs."""


class TankController:
    """
    Steuert den Tankablauf des Fleet Carriers.

    Aktueller Entwicklungsstand:
        1. Menü 1 sicher erreichen
        2. Carrier-Dienste anwählen
        3. Menü 2 öffnen
        4. Tritiumdepot anwählen
        5. Tritiumdepot öffnen
        6. geöffnetes Depot per Vision bestätigen
        7. Carrier-Tankfüllstand per OCR lesen
        8. Tankfüllstand mit dem GUI-Schwellenwert vergleichen

    Tritiumspende und Schiffstransfer werden anschließend ergänzt.
    """

    TANK_LEVEL_REFERENCE = "ocr_tank_fuel_level"
    TRANSFER_LIST_REFERENCE = "ocr_transfer_item_list"
    SELECTION_ARROW_REFERENCE = "tank_auswahlpfeil_links"

    def __init__(
        self,
        *,
        menu_controller: MenuController,
        navigator: Navigator,
        press_key: Callable[..., None],
        log_message: Callable[[str], None] | None = None,
        status_changed: Callable[[TankStatus], None] | None = None,
    ) -> None:
        self.menu_controller = menu_controller
        self.navigator = navigator
        self.press_key = press_key
        self.log_message = log_message or print
        self.status_changed = status_changed

        self.status = TankStatus.IDLE

        self.vision = Vision()

        # Dieselbe Einstellungsdatei, die auch automation_gui.py benutzt.
        self.settings = load_settings()

        self.refuel_threshold = self._load_refuel_threshold()
        self.tritium_list_position = self._load_tritium_list_position()

        # PaddleOCR wird erst dann geladen, wenn es tatsächlich
        # für die Tankprüfung benötigt wird.
        self.ocr_engine: PaddleEngine | None = None

    def _log(self, text: str) -> None:
        """Gibt eine Statusmeldung aus."""

        self.log_message(text)

    def _set_status(self, status: TankStatus) -> None:
        """Setzt den Status und meldet ihn an die Oberfläche."""

        self.status = status

        if self.status_changed is not None:
            self.status_changed(status)

    def _load_refuel_threshold(self) -> int:
        """
        Liest den in der GUI eingestellten Mindestfüllstand.

        Der zulässige Bereich entspricht der GUI:
            1 bis 100 Prozent
        """

        try:
            threshold = int(
                self.settings.get(
                    "carrier_refuel_threshold",
                    20,
                )
            )

        except (TypeError, ValueError):
            threshold = 20

        return max(
            1,
            min(
                105,
                threshold,
            ),
        )

    def _load_tritium_list_position(self) -> int:
        """Liest die erwartete Tritium-Position aus den GUI-Einstellungen.

        Positive Werte bewegen die Auswahl nach oben (W), negative Werte
        nach unten (S). Der Wert 0 prüft zunächst die aktuelle Zeile.
        """

        try:
            position = int(self.settings.get("tritium_list_position", 0))
        except (TypeError, ValueError):
            position = 0

        return max(-50, min(50, position))

    def _move_transfer_selection(self, steps: int) -> None:
        """Bewegt die Auswahl um die angegebene Anzahl Listenzeilen."""

        if steps == 0:
            return

        key = "w" if steps > 0 else "s"
        direction = "nach oben" if steps > 0 else "nach unten"
        count = abs(steps)

        self._log(
            "TankController: Transferauswahl wird "
            f"{count}-mal {direction} bewegt (Taste {key.upper()})."
        )

        for step in range(1, count + 1):
            self.press_key(
                key,
                hold_time=0.12,
                after_delay=0.18,
            )
            self._log(
                f"TankController: Taste {key.upper()} wurde gedrückt "
                f"({step}/{count})."
            )

        time.sleep(0.35)

    def _get_ocr_engine(self) -> PaddleEngine:
        """
        Erstellt PaddleOCR beim ersten OCR-Aufruf.

        Dadurch startet die GUI schnell und das größere OCR-Modell
        wird nur geladen, wenn die Tankprüfung tatsächlich läuft.
        """

        if self.ocr_engine is None:
            self._log(
                "TankController: OCR wird geladen. "
                "Der erste Start kann einen Moment dauern."
            )

            self.ocr_engine = PaddleEngine()

            self._log("TankController: OCR ist bereit.")

        return self.ocr_engine

    def _get_elite_window(self):
        """
        Sucht das Elite-Fenster und prüft,
        ob es auf der aktiven Arbeitsfläche liegt.
        """

        window = find_elite_window()

        if window is None:
            raise TankControllerError(
                "Elite-Fenster wurde für die OCR-Aufnahme nicht gefunden."
            )

        current_desktop = get_current_desktop()

        if window.desktop != current_desktop:
            raise TankControllerError(
                "Elite und CTSVision befinden sich nicht auf derselben "
                "aktiven Arbeitsfläche. "
                f"Elite: Arbeitsfläche {window.desktop + 1}, "
                f"aktiv: Arbeitsfläche {current_desktop + 1}."
            )

        return window

    def _capture_reference_region(
        self,
        reference_name: str,
    ):
        """
        Nimmt den aktuell sichtbaren Elite-Bereich einer
        gespeicherten Referenz auf.

        Für den Tankfüllstand ist die Referenz selbst bereits
        der exakt markierte OCR-Bereich.
        """

        config = load_config()

        references = config.get(
            "references",
            {},
        )

        reference = references.get(reference_name)

        if reference is None:
            raise TankControllerError(
                f"OCR-Referenz '{reference_name}' wurde "
                "in der Konfiguration nicht gefunden."
            )

        try:
            x = int(reference["x"])
            y = int(reference["y"])
            width = int(reference["width"])
            height = int(reference["height"])

        except (KeyError, TypeError, ValueError) as exc:
            raise TankControllerError(
                f"OCR-Referenz '{reference_name}' enthält " "ungültige Koordinaten."
            ) from exc

        if width <= 0 or height <= 0:
            raise TankControllerError(
                f"OCR-Referenz '{reference_name}' besitzt " "eine ungültige Größe."
            )

        window = self._get_elite_window()

        return capture_window_region(
            window=window,
            x=x,
            y=y,
            width=width,
            height=height,
        )

    @staticmethod
    def _normalize_tank_text(text: str) -> str:
        """
        Bereinigt typische OCR-Abweichungen.

        Erhalten bleiben nur Zeichen, die für einen Wert wie
        965/1000 benötigt werden.
        """

        normalized = text.upper()

        # Häufige Verwechslungen in reinen Zahlenbereichen.
        normalized = normalized.replace("O", "0")
        normalized = normalized.replace("I", "1")
        normalized = normalized.replace("L", "1")
        normalized = normalized.replace("|", "/")
        normalized = normalized.replace("\\", "/")

        # Verschiedene Trennzeichen vereinheitlichen.
        normalized = normalized.replace(":", "/")
        normalized = normalized.replace("-", "/")

        return normalized

    @classmethod
    def _parse_tank_level(
        cls,
        text: str,
    ) -> tuple[int, int]:
        """
        Liest einen Tankwert wie 965/1000 aus dem OCR-Text.

        Rückgabe:
            aktueller Tankinhalt,
            maximale Tankkapazität
        """

        normalized = cls._normalize_tank_text(text)

        # Standardfall:
        #     965/1000
        match = re.search(
            r"(\d{1,4})\s*/\s*(\d{1,4})",
            normalized,
        )

        if match is None:
            # Falls PaddleOCR Leerzeichen oder Zeilenumbrüche
            # zwischen die Werte gesetzt hat.
            numbers = re.findall(
                r"\d{1,4}",
                normalized,
            )

            if len(numbers) == 2:
                current = int(numbers[0])
                maximum = int(numbers[1])
            else:
                raise TankControllerError(
                    "Der Carrier-Tankfüllstand konnte nicht aus "
                    f"dem OCR-Text gelesen werden: {text!r}"
                )

        else:
            current = int(match.group(1))
            maximum = int(match.group(2))

        if maximum <= 0:
            raise TankControllerError(
                "OCR lieferte eine ungültige maximale Tankkapazität: " f"{maximum}"
            )

        if current < 0:
            raise TankControllerError("OCR lieferte einen negativen Tankfüllstand.")

        if current > maximum:
            raise TankControllerError(
                "OCR lieferte einen unplausiblen Tankfüllstand: " f"{current}/{maximum}"
            )

        return current, maximum

    def reach_main_menu(
        self,
        *,
        max_attempts: int = 5,
    ) -> None:
        """
        Erreicht Menü 1 und wählt dort Carrier-Dienste an.

        Kann Menü 1 nicht erkannt werden, wird mit BACKSPACE
        jeweils eine Menüebene zurückgegangen und anschließend
        erneut geprüft.
        """

        self._log(
            "TankController: Ausgangszustand wird gesucht. "
            "Falls nötig, wird mit BACKSPACE zu Menü 1 zurückgegangen."
        )

        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            self._log(
                "TankController: Menü-1-Erkennung – "
                f"Versuch {attempt}/{max_attempts}."
            )

            try:
                self.navigator.goto(
                    "main_menu",
                    "main_menu_block_carrierdienste",
                    max_actions=14,
                    state_timeout=4.0,
                )

                self._log(
                    "TankController: Menü 1 wurde sicher erkannt. "
                    "Carrier-Dienste sind angewählt."
                )

                return

            except Exception as exc:
                last_error = exc

                self._log("TankController: Menü 1 wurde nicht erkannt: " f"{exc}")

                if attempt >= max_attempts:
                    break

                self._log(
                    "TankController: BACKSPACE wird gedrückt, "
                    "um eine Menüebene zurückzugehen."
                )

                self.press_key(
                    "backspace",
                    hold_time=0.20,
                    after_delay=2.00,
                )

        raise TankControllerError(
            "Menü 1 konnte auch nach "
            f"{max_attempts} Versuchen nicht erreicht werden. "
            f"Letzter Fehler: {last_error}"
        )

    def open_carrier_services(self) -> None:
        """
        Öffnet aus Menü 1 die Carrier-Dienste und bestätigt Menü 2.
        """

        self._log("TankController: Carrier-Dienste werden geöffnet.")

        state, similarity = self.menu_controller.open_menu(
            key="space",
            prefix="carrier_services_",
            loading_time=5.0,
            timeout=8.0,
        )

        self._log(
            "TankController: Menü 2 wurde erkannt: "
            f"{state} ({similarity * 100:.2f} %)."
        )

    def select_tritium_depot(self) -> None:
        """
        Navigiert innerhalb der Carrier-Dienste zum Tritiumdepot.
        """

        self._log("TankController: Menü 2 – Tritiumdepot wird angewählt.")

        self.navigator.goto(
            "carrier_services",
            "carrier_services_block_tritiumdepot",
            max_actions=14,
            state_timeout=4.0,
        )

        self._log("TankController: Tritiumdepot ist sicher angewählt.")

    def open_tritium_depot(self) -> tuple[str, float]:
        """
        Öffnet das angewählte Tritiumdepot und bestätigt,
        dass das Depotfenster sichtbar ist.
        """

        self._log("TankController: Tritiumdepot wird mit SPACE geöffnet.")

        state, similarity = self.menu_controller.open_menu(
            key="space",
            prefix="tank_tritium_depot_open",
            loading_time=3.0,
            timeout=8.0,
            poll_interval=0.25,
            extra_width=200,
            extra_height=200,
        )

        self._log(
            "TankController: Tritiumdepot wurde sicher geöffnet: "
            f"{state} ({similarity * 100:.2f} %)."
        )

        return state, similarity

    def verify_tritium_donate_active(
        self,
    ) -> tuple[str, float]:
        """
        Prüft, ob im geöffneten Tritiumdepot
        die Schaltfläche „TRITIUM SPENDEN“
        bereits aktiv ist.

        Es wird noch keine Taste gedrückt.
        """

        self._log("TankController: Prüfe, ob " "„TRITIUM SPENDEN“ aktiv ist.")

        state, similarity = self.menu_controller.wait_for_menu(
            prefix="tank_tritium_spenden_aktiv",
            timeout=5.0,
            poll_interval=0.25,
            extra_width=100,
            extra_height=100,
        )

        if state != "tank_tritium_spenden_aktiv":
            raise TankControllerError(
                "Die Schaltfläche " "„TRITIUM SPENDEN“ " "wurde nicht erkannt."
            )

        self._log(
            "TankController: "
            "„TRITIUM SPENDEN“ wurde erkannt: "
            f"{similarity * 100:.2f} %."
        )

        return state, similarity

    def wait_for_tritium_donate(
        self,
    ) -> tuple[str, float]:
        """
        Prüft, ob im geöffneten Tritiumdepot
        die Schaltfläche „TRITIUM SPENDEN“ aktiv ist.

        Es wird noch keine Taste gedrückt.
        """

        self._log("TankController: Prüfe, ob „TRITIUM SPENDEN“ aktiv ist.")

        state, similarity = self.menu_controller.wait_for_menu(
            prefix="tank_tritium_spenden_aktiv",
            timeout=5.0,
            poll_interval=0.25,
            extra_width=100,
            extra_height=100,
        )

        if state != "tank_tritium_spenden_aktiv":
            raise TankControllerError(
                "Die aktive Schaltfläche „TRITIUM SPENDEN“ "
                "wurde nicht sicher erkannt. "
                f"Erkannter Zustand: {state}"
            )

        self._log(
            "TankController: „TRITIUM SPENDEN“ ist aktiv: "
            f"{state} ({similarity * 100:.2f} %)."
        )

        return state, similarity

    def detect_ship_tritium(
        self,
    ) -> bool:
        """
        Prüft im geöffneten Tritiumdepot, ob sich Tritium
        im Schiff befindet.

        Rückgabe:
            True:
                „TRITIUM SPENDEN“ ist aktiv.
                Im Schiff befindet sich Tritium.

            False:
                „KEIN TRITIUM VERFÜGBAR“ wird angezeigt.
                Das Schiff muss zunächst beladen werden.

        Es wird keine Taste gedrückt.
        """

        self._log("TankController: Prüfe, ob sich Tritium " "im Schiff befindet.")

        # Zuerst den aktuellen Leerzustand prüfen.
        try:
            state, similarity = self.menu_controller.wait_for_menu(
                prefix="tank_kein_tritium_verfuegbar",
                timeout=2.0,
                poll_interval=0.25,
                extra_width=100,
                extra_height=100,
            )

            if state == "tank_kein_tritium_verfuegbar":
                self._log(
                    "TankController: „KEIN TRITIUM VERFÜGBAR“ "
                    "wurde sicher erkannt: "
                    f"{state} ({similarity * 100:.2f} %)."
                )

                self._log(
                    "TankController: Im Schiff befindet sich "
                    "kein Tritium. Der lange Tankweg ist erforderlich."
                )

                return False

        except Exception:
            # Der Leerzustand wurde nicht erkannt.
            # Anschließend wird geprüft, ob Tritium gespendet werden kann.
            pass

        try:
            state, similarity = self.menu_controller.wait_for_menu(
                prefix="tank_tritium_spenden_aktiv",
                timeout=3.0,
                poll_interval=0.25,
                extra_width=100,
                extra_height=100,
            )

            if state == "tank_tritium_spenden_aktiv":
                self._log(
                    "TankController: „TRITIUM SPENDEN“ "
                    "wurde sicher erkannt: "
                    f"{state} ({similarity * 100:.2f} %)."
                )

                self._log(
                    "TankController: Im Schiff befindet sich Tritium. "
                    "Der direkte Tankweg ist verfügbar."
                )

                return True

        except Exception as exc:
            raise TankControllerError(
                "Es konnte weder „TRITIUM SPENDEN“ noch "
                "„KEIN TRITIUM VERFÜGBAR“ sicher erkannt werden."
            ) from exc

        raise TankControllerError(
            "Der Tritiumzustand des Schiffes konnte nicht " "sicher bestimmt werden."
        )

    def select_ship_inventory(
        self,
        *,
        max_attempts: int = 10,
    ) -> tuple[str, float]:
        """
        Drückt höchstens zehnmal E, bis im rechten Schiffsmenü
        der Reiter „INVENTAR“ sicher erkannt wird.
        """

        self._log(
            "TankController: Im rechten Schiffsmenü wird "
            "der Reiter „INVENTAR“ gesucht."
        )

        last_similarity = 0.0

        for attempt in range(max_attempts + 1):
            try:
                state, similarity = self.menu_controller.wait_for_menu(
                    prefix="tank_inventar_aktiv",
                    timeout=1.0,
                    poll_interval=0.20,
                    extra_width=100,
                    extra_height=100,
                )

                last_similarity = similarity

                if state == "tank_inventar_aktiv":
                    self._log(
                        "TankController: Reiter „INVENTAR“ "
                        "wurde sicher erkannt: "
                        f"{similarity * 100:.2f} %."
                    )

                    return state, similarity

            except Exception:
                # INVENTAR wurde bei diesem Versuch nicht erkannt.
                pass

            if attempt >= max_attempts:
                break

            self._log(
                "TankController: „INVENTAR“ noch nicht aktiv. "
                f"Taste E wird gedrückt "
                f"({attempt + 1}/{max_attempts})."
            )

            self.press_key(
                "e",
                hold_time=0.20,
                after_delay=0.60,
            )

        raise TankControllerError(
            "Der Reiter „INVENTAR“ wurde auch nach "
            f"{max_attempts} Tastendrücken nicht erkannt. "
            f"Bester Wert: {last_similarity * 100:.2f} %."
        )

    def select_transfer(
        self,
        *,
        max_attempts: int = 4,
    ) -> tuple[str, float]:
        """
        Drückt höchstens viermal D, bis im Inventarmenü
        der Button „TRANSFER“ sicher erkannt wird.
        """

        self._log(
            "TankController: Im Inventarmenü wird " "der Button „TRANSFER“ gesucht."
        )

        last_similarity = 0.0

        for attempt in range(max_attempts + 1):
            try:
                state, similarity = self.menu_controller.wait_for_menu(
                    prefix="tank_transfer_aktiv",
                    timeout=1.0,
                    poll_interval=0.20,
                    extra_width=100,
                    extra_height=100,
                )

                last_similarity = similarity

                if state == "tank_transfer_aktiv":
                    self._log(
                        "TankController: „TRANSFER“ wurde sicher erkannt: "
                        f"{similarity * 100:.2f} %."
                    )

                    return state, similarity

            except Exception:
                # TRANSFER wurde bei diesem Versuch nicht erkannt.
                pass

            if attempt >= max_attempts:
                break

            self._log(
                "TankController: „TRANSFER“ noch nicht aktiv. "
                f"Taste D wird gedrückt "
                f"({attempt + 1}/{max_attempts})."
            )

            self.press_key(
                "d",
                hold_time=0.20,
                after_delay=0.60,
            )

        raise TankControllerError(
            "Der Button „TRANSFER“ wurde auch nach "
            f"{max_attempts} Tastendrücken nicht erkannt. "
            f"Bester Wert: {last_similarity * 100:.2f} %."
        )

    def select_transfer_abbrechen(
        self,
        *,
        max_attempts: int = 3,
        threshold: float = 0.75,
    ) -> tuple[str, float]:
        """
        Bewegt die Auswahl nach dem Tritiumtransfer mit S
        auf die Schaltfläche „ABBRECHEN“.

        Die Referenz wird direkt an ihrer gespeicherten Position
        mit Vision geprüft. Die endgültige Übertragung wird noch
        nicht bestätigt.
        """

        reference_name = "tank_transfer_abbrechen_aktiv"

        self._log("TankController: Schaltfläche „ABBRECHEN“ wird angewählt.")

        last_similarity = 0.0

        for attempt in range(max_attempts + 1):
            try:
                matched, similarity = self.vision.check(
                    reference_name,
                    threshold=threshold,
                )

                last_similarity = float(similarity)

                self._log(
                    "TankController: Direkte Vision-Prüfung "
                    "„ABBRECHEN“: "
                    f"{last_similarity * 100:.2f} % "
                    f"({'Treffer' if matched else 'kein Treffer'})."
                )

                if matched:
                    self._log(
                        "TankController: „ABBRECHEN“ wurde mit dem "
                        f"speziellen Schwellenwert von {threshold * 100:.0f} % "
                        "sicher erkannt."
                    )

                    return reference_name, last_similarity

            except Exception as exc:
                raise TankControllerError(
                    "Die direkte Vision-Prüfung für „ABBRECHEN“ "
                    f"ist fehlgeschlagen: {exc}"
                ) from exc

            if attempt >= max_attempts:
                break

            self._log(
                "TankController: „ABBRECHEN“ noch nicht aktiv. "
                f"Taste S wird gedrückt "
                f"({attempt + 1}/{max_attempts})."
            )

            self.press_key(
                "s",
                hold_time=0.20,
                after_delay=0.60,
            )

        raise TankControllerError(
            "Die Schaltfläche „ABBRECHEN“ wurde auch nach "
            f"{max_attempts} Tastendrücken nicht erkannt. "
            f"Bester Wert: {last_similarity * 100:.2f} %."
        )

    def select_transfer_bestaetigen(
        self,
        *,
        max_attempts: int = 4,
        threshold: float = 0.75,
    ) -> tuple[str, float]:
        """
        Bewegt die Auswahl von „ABBRECHEN“ mit D auf
        „TRANSFER BESTÄTIGEN“.

        Die Referenz wird direkt an ihrer gespeicherten Position
        mit Vision geprüft. SPACE wird bewusst noch nicht gedrückt.
        """

        reference_name = "tank_transfer_bestaetigen_aktiv"

        self._log(
            "TankController: Schaltfläche „TRANSFER BESTÄTIGEN“ " "wird angewählt."
        )

        last_similarity = 0.0

        for attempt in range(max_attempts + 1):
            try:
                matched, similarity = self.vision.check(
                    reference_name,
                    threshold=threshold,
                )

                last_similarity = float(similarity)

                self._log(
                    "TankController: Direkte Vision-Prüfung "
                    "„TRANSFER BESTÄTIGEN“: "
                    f"{last_similarity * 100:.2f} % "
                    f"({'Treffer' if matched else 'kein Treffer'})."
                )

                if matched:
                    self._log(
                        "TankController: „TRANSFER BESTÄTIGEN“ wurde mit dem "
                        f"speziellen Schwellenwert von {threshold * 100:.0f} % "
                        "sicher erkannt."
                    )

                    return reference_name, last_similarity

            except Exception as exc:
                raise TankControllerError(
                    "Die direkte Vision-Prüfung für "
                    f"„TRANSFER BESTÄTIGEN“ ist fehlgeschlagen: {exc}"
                ) from exc

            if attempt >= max_attempts:
                break

            self._log(
                "TankController: „TRANSFER BESTÄTIGEN“ noch nicht aktiv. "
                f"Taste D wird gedrückt "
                f"({attempt + 1}/{max_attempts})."
            )

            self.press_key(
                "d",
                hold_time=0.20,
                after_delay=0.60,
            )

        raise TankControllerError(
            "Die Schaltfläche „TRANSFER BESTÄTIGEN“ wurde auch nach "
            f"{max_attempts} Tastendrücken nicht erkannt. "
            f"Bester Wert: {last_similarity * 100:.2f} %."
        )

    @staticmethod
    def _match_value(result, *names: str):
        """Liest einen Positionswert aus unterschiedlichen Match-Ergebnissen."""

        for name in names:
            value = getattr(result, name, None)

            if value is not None:
                return float(value)

        return None

    def _find_selected_row_by_highlight(
        self,
        *,
        list_y: int,
        list_height: int,
        row_height: float,
    ) -> tuple[float, float]:
        """
        Ermittelt die aktive Listenzeile anhand des hellen orangefarbenen
        Auswahlbalkens.

        Die Auswertung verwendet relative Bildanteile und die per OCR
        ermittelte Zeilenhöhe. Sie ist deshalb nicht an eine feste
        Bildschirmauflösung gebunden.

        Rückgabe:
            absolute Y-Mitte der aktiven Zeile,
            Flächenanteil der erkannten Hervorhebung
        """

        image = self._capture_reference_region(self.TRANSFER_LIST_REFERENCE).convert(
            "RGB"
        )

        pixels = np.asarray(image, dtype=np.uint8)

        if pixels.ndim != 3 or pixels.shape[2] < 3:
            raise TankControllerError(
                "Der Bildausschnitt der Transferliste besitzt "
                "ein ungültiges Farbformat."
            )

        height, width = pixels.shape[:2]

        # Die äußeren Ränder, Mengenfelder und Symbole werden ausgespart.
        # Im mittleren Listenbereich ist der Auswahlbalken großflächig,
        # während unselektierte Zeilen dort überwiegend dunkel bleiben.
        x_start = int(round(width * 0.12))
        x_end = int(round(width * 0.78))

        if x_end <= x_start:
            raise TankControllerError(
                "Der Farbsuchbereich der Transferliste ist ungültig."
            )

        area = pixels[:, x_start:x_end, :3].astype(np.int16)
        red = area[:, :, 0]
        green = area[:, :, 1]
        blue = area[:, :, 2]

        # Elite-Auswahlbalken: kräftiges Orange/Gelb.
        orange_mask = (
            (red >= 120)
            & (green >= 45)
            & (red >= green * 1.15)
            & (green >= blue * 1.40)
        )

        row_scores = orange_mask.mean(axis=1)

        # Über ungefähr eine halbe Textzeile glätten. Dadurch dominieren
        # flächige Auswahlbalken gegenüber einzelnen orangefarbenen Zeichen.
        smooth_size = max(3, int(round(row_height * 0.55)))
        kernel = np.ones(smooth_size, dtype=float) / smooth_size
        smooth_scores = np.convolve(row_scores, kernel, mode="same")

        best_y = int(np.argmax(smooth_scores))
        best_score = float(smooth_scores[best_y])

        # Einzelne Schriftzeichen erzeugen nur einen kleinen Flächenanteil.
        # Unterhalb dieser Grenze ist keine aktive Zeile sicher bestimmbar.
        minimum_score = 0.18

        self._log(
            "TankController: Auswahlbalken-Farberkennung: " f"{best_score * 100:.2f} %."
        )

        if best_score < minimum_score:
            raise TankControllerError(
                "Weder der Auswahlpfeil noch der orangefarbene "
                "Auswahlbalken konnten sicher erkannt werden. "
                "Es wird keine Richtungstaste gedrückt."
            )

        return list_y + float(best_y), best_score

    def get_tritium_selection_direction(
        self,
        *,
        tritium_x: int,
        tritium_y: int,
        tritium_width: int,
        tritium_height: int,
        image_scale: int = 2,
        threshold: float = 0.90,
    ) -> tuple[bool, str | None, float]:
        """
        Bestimmt die aktive Transferzeile ausschließlich anhand des
        orangefarbenen Auswahlbalkens.

        OCR liefert die Position der Tritiumzeile. Die Farberkennung
        liefert die Position der aktuell ausgewählten Zeile. Nur wenn
        beide Zeilen übereinstimmen, gilt TRITIUM als sicher angewählt.

        Rückgabe:
            ausgewählt,
            erforderliche Taste ("w", "s" oder None),
            Flächenanteil der erkannten Hervorhebung

        Das bisherige Referenzbild des kleinen Auswahlpfeils wird für
        diese Entscheidung nicht mehr verwendet.
        """

        config = load_config()

        reference = config.get(
            "references",
            {},
        ).get(self.TRANSFER_LIST_REFERENCE)

        if reference is None:
            raise TankControllerError(
                f"OCR-Referenz '{self.TRANSFER_LIST_REFERENCE}' "
                "wurde nicht gefunden."
            )

        try:
            list_y = int(reference["y"])
            list_height = int(reference["height"])

        except (KeyError, TypeError, ValueError) as exc:
            raise TankControllerError(
                "Die OCR-Referenz der Transferliste enthält " "ungültige Koordinaten."
            ) from exc

        row_y = tritium_y / image_scale
        row_height = max(1.0, tritium_height / image_scale)
        tritium_center_y = list_y + row_y + row_height / 2.0

        self._log(
            "TankController: Aktive Transferzeile wird über den "
            "orangefarbenen Auswahlbalken bestimmt."
        )
        self._log(
            "TankController: Tritium-Zeile: "
            f"Y-Mitte={tritium_center_y:.1f}, "
            f"Zeilenhöhe={row_height:.1f}."
        )

        highlight_center_y, highlight_score = self._find_selected_row_by_highlight(
            list_y=list_y,
            list_height=list_height,
            row_height=row_height,
        )

        delta_y = highlight_center_y - tritium_center_y

        # Die OCR-Textbox liegt nicht immer exakt mittig im Auswahlbalken.
        # Eine Toleranz von 60 % der erkannten Zeilenhöhe bleibt deutlich
        # kleiner als der Abstand zweier benachbarter Listenzeilen.
        row_tolerance = row_height * 0.60

        self._log(
            "TankController: Position über Auswahlbalken: "
            f"Y-Mitte={highlight_center_y:.1f}; "
            f"Abstand zu TRITIUM={delta_y:+.1f}; "
            f"Toleranz=±{row_tolerance:.1f}."
        )

        if abs(delta_y) <= row_tolerance:
            self._log(
                "TankController: Der orangefarbene Auswahlbalken liegt "
                "auf der Tritiumzeile. „TRITIUM“ ist sicher angewählt."
            )
            return True, None, highlight_score

        if highlight_center_y < tritium_center_y:
            self._log(
                "TankController: Der Auswahlbalken steht oberhalb von "
                "TRITIUM. Die Auswahl muss mit S nach unten bewegt werden."
            )
            return False, "s", highlight_score

        self._log(
            "TankController: Der Auswahlbalken steht unterhalb von "
            "TRITIUM. Die Auswahl muss mit W nach oben bewegt werden."
        )
        return False, "w", highlight_score

    def find_tritium_in_transfer_menu(self) -> str:
        """Sucht TRITIUM rund um eine einstellbare Listenposition.

        Zuerst wird die in der GUI gespeicherte Position blind angefahren:
        positive Werte mit W nach oben, negative Werte mit S nach unten.
        Danach wird die erwartete Position geprüft. Bleibt die OCR ohne
        Treffer, werden zusätzlich zwei Positionen nach oben und fünf
        Positionen nach unten relativ zum Startwert kontrolliert.
        """

        self._log(
            "TankController: Im Transfermenü wird per OCR nach „TRITIUM“ gesucht."
        )

        ocr_engine = self._get_ocr_engine()
        debug_dir = Path(__file__).resolve().parent / "references" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        base_position = self.tritium_list_position
        self._log(
            "TankController: Eingestellte Tritium-Position: "
            f"{base_position:+d} (positiv = W/oben, negativ = S/unten)."
        )

        # Zuerst die erwartete Position blind anfahren.
        self._move_transfer_selection(base_position)

        # Suchpositionen relativ zur erwarteten Position:
        # aktuelle Position, 1/2 nach oben, anschließend 1..5 nach unten.
        search_offsets = (0, 1, 2, -1, -2, -3, -4, -5)
        current_offset = 0
        last_movement_key: str | None = None
        scan_number = 0

        for target_offset in search_offsets:
            movement = target_offset - current_offset
            if movement:
                self._move_transfer_selection(movement)
                current_offset = target_offset

            absolute_position = base_position + target_offset
            self._log(
                "TankController: Prüfe Tritium-Suchposition "
                f"{absolute_position:+d} (Abweichung {target_offset:+d})."
            )

            # Sobald TRITIUM sichtbar ist, darf die vorhandene Pfeil-/
            # Balkenerkennung die Auswahl zeilenweise exakt ausrichten.
            for alignment_attempt in range(12):
                scan_number += 1
                image = self._capture_reference_region(self.TRANSFER_LIST_REFERENCE)
                image = image.resize((image.width * 2, image.height * 2))

                debug_file = debug_dir / (
                    f"ocr_transfer_item_list_{scan_number:02d}.png"
                )
                image.save(debug_file)

                self._log(
                    "TankController: Transferliste wird per OCR gelesen "
                    f"(Prüfung {scan_number})."
                )

                result = ocr_engine.read_image(str(debug_file))

                if not result.success:
                    self._log(
                        "TankController: OCR hat an dieser Position "
                        "keinen lesbaren Text erkannt."
                    )
                    break

                self._log("TankController: OCR-Text Transferliste: " f"{result.text!r}")
                self._log(
                    "TankController: OCR-Konfidenz Transferliste: "
                    f"{result.confidence * 100:.2f} %."
                )

                tritium_line = next(
                    (
                        line
                        for line in result.lines
                        if "TRITIUM" in line.text.upper() and line.box is not None
                    ),
                    None,
                )

                if tritium_line is None:
                    self._log(
                        "TankController: „TRITIUM“ wurde an dieser "
                        "Suchposition nicht gefunden."
                    )
                    break

                self._log(
                    "TankController: Der Eintrag „TRITIUM“ wurde in der "
                    "Transferliste gefunden."
                )
                self._log(
                    "TankController: Position von „TRITIUM“: "
                    f"X={tritium_line.box.x}, Y={tritium_line.box.y}, "
                    f"Breite={tritium_line.box.width}, "
                    f"Höhe={tritium_line.box.height}."
                )

                tritium_selected, movement_key, _ = (
                    self.get_tritium_selection_direction(
                        tritium_x=tritium_line.box.x,
                        tritium_y=tritium_line.box.y,
                        tritium_width=tritium_line.box.width,
                        tritium_height=tritium_line.box.height,
                        image_scale=2,
                    )
                )

                if tritium_selected:
                    self._log(
                        "TankController: Der Auswahlpfeil steht auf der "
                        "Tritiumzeile. „TRITIUM“ ist angewählt."
                    )
                    self._log(
                        "TankController: Taste A wird 5 Sekunden gehalten, "
                        "um so viel Tritium wie möglich ins Schiff zu übertragen."
                    )
                    self.press_key(
                        "a",
                        hold_time=5.20,
                        after_delay=1.00,
                    )
                    self._log("TankController: Tritium wurde in das Schiff übertragen.")
                    self._log(
                        "TankController: BACKSPACE wird gedrückt, um die "
                        "Bearbeitung zu verlassen und direkt zur Schaltfläche "
                        "„ABBRECHEN“ zu wechseln."
                    )
                    self.press_key(
                        "backspace",
                        hold_time=0.20,
                        after_delay=0.80,
                    )
                    return result.text

                if movement_key not in {"w", "s"}:
                    raise TankControllerError(
                        "Für die Bewegung zur Tritiumzeile wurde keine "
                        "sichere Richtung ermittelt."
                    )

                if last_movement_key is not None and movement_key != last_movement_key:
                    raise TankControllerError(
                        "Die Auswahl würde zwischen zwei Listenzeilen pendeln. "
                        f"Zuletzt wurde {last_movement_key.upper()} verwendet, "
                        f"jetzt wäre {movement_key.upper()} erforderlich."
                    )

                last_movement_key = movement_key
                self._log(
                    f"TankController: „TRITIUM“ ist sichtbar. Taste "
                    f"{movement_key.upper()} wird einmal zur exakten "
                    "Ausrichtung gedrückt."
                )
                self.press_key(
                    movement_key,
                    hold_time=0.12,
                    after_delay=0.40,
                )
            else:
                raise TankControllerError(
                    "TRITIUM wurde erkannt, konnte aber nach 12 Schritten "
                    "nicht sicher angewählt werden."
                )

            last_movement_key = None

        checked_min = base_position - 5
        checked_max = base_position + 2
        raise TankControllerError(
            "Der Eintrag „TRITIUM“ wurde im eingestellten Suchbereich "
            f"nicht gefunden. Ausgangsposition: {base_position:+d}; "
            f"geprüfter Bereich: {checked_min:+d} bis {checked_max:+d}."
        )

    def donate_ship_tritium_to_carrier(
        self,
    ) -> None:
        """
        Spendet das im Schiff vorhandene Tritium an den Carrier.

        Ablauf:
            1. „TRITIUM SPENDEN“ sicher erkennen
            2. mit SPACE den Spendendialog öffnen
            3. „DEPOT BESTÄTIGEN“ sicher erkennen
            4. mit SPACE endgültig bestätigen
        """

        self._log("TankController: Tritiumspende an den Carrier wird gestartet.")

        self.wait_for_tritium_donate()

        self._log(
            "TankController: „TRITIUM SPENDEN“ ist aktiv. "
            "Der Spendendialog wird mit SPACE geöffnet."
        )

        self.press_key(
            "space",
            hold_time=0.20,
            after_delay=2.00,
        )

        self._log(
            "TankController: Spendendialog wurde geöffnet. "
            "Auswahl zwischen „DEPOT BESTÄTIGEN“ und „ABBRECHEN“ wird geprüft."
        )

        depot_active = False
        depot_similarity = 0.0

        try:
            state, similarity = self.menu_controller.wait_for_menu(
                prefix="tank_depot_bestaetigen_aktiv",
                timeout=1.5,
                poll_interval=0.25,
                extra_width=100,
                extra_height=100,
            )

            if state == "tank_depot_bestaetigen_aktiv":
                depot_active = True
                depot_similarity = similarity

        except Exception:
            pass

        if not depot_active:
            try:
                state, similarity = self.menu_controller.wait_for_menu(
                    prefix="tank_abbrechen_aktiv",
                    timeout=1.5,
                    poll_interval=0.25,
                    extra_width=100,
                    extra_height=100,
                )

                if state != "tank_abbrechen_aktiv":
                    raise TankControllerError(
                        "Im Spendendialog wurde weder „DEPOT BESTÄTIGEN“ "
                        "noch „ABBRECHEN“ sicher erkannt."
                    )

                self._log(
                    "TankController: „ABBRECHEN“ ist aktiv: "
                    f"{state} ({similarity * 100:.2f} %)."
                )

                self._log(
                    "TankController: Taste W wird gedrückt, "
                    "um „DEPOT BESTÄTIGEN“ anzuwählen."
                )

                self.press_key(
                    "w",
                    hold_time=0.20,
                    after_delay=0.80,
                )

            except Exception as exc:
                raise TankControllerError(
                    "Die Auswahl im Spendendialog konnte nicht sicher bestimmt werden."
                ) from exc

            state, similarity = self.menu_controller.wait_for_menu(
                prefix="tank_depot_bestaetigen_aktiv",
                timeout=4.0,
                poll_interval=0.25,
                extra_width=100,
                extra_height=100,
            )

            if state != "tank_depot_bestaetigen_aktiv":
                raise TankControllerError(
                    "„DEPOT BESTÄTIGEN“ wurde nach Taste W " "nicht sicher erkannt."
                )

            depot_similarity = similarity

        self._log(
            "TankController: „DEPOT BESTÄTIGEN“ wurde sicher erkannt: "
            f"tank_depot_bestaetigen_aktiv ({depot_similarity * 100:.2f} %)."
        )

        self._log("TankController: Tritiumspende wird mit SPACE bestätigt.")

        self.press_key(
            "space",
            hold_time=0.20,
            after_delay=2.00,
        )

        self._log("TankController: Tritium wurde erfolgreich an den Carrier gespendet.")

        self._log("TankController: BACKSPACE wird gedrückt.")

        self.press_key(
            "backspace",
            hold_time=0.20,
            after_delay=1.00,
        )

        self._log("TankController: BACKSPACE wird ein zweites Mal gedrückt.")

        self.press_key(
            "backspace",
            hold_time=0.20,
            after_delay=1.00,
        )

        self._log(
            "TankController: Spendenvorgang wurde abgeschlossen "
            "und das Tritiumdepot verlassen."
        )

    def check_carrier_tank(
        self,
    ) -> tuple[int, int, float, bool]:
        """
        Liest den Carrier-Tankfüllstand und vergleicht ihn
        mit dem in der GUI eingestellten Schwellenwert.

        Rückgabe:
            aktueller Tankinhalt,
            maximale Tankkapazität,
            Füllstand in Prozent,
            Nachtanken erforderlich
        """

        self._log("TankController: Carrier-Tankfüllstand wird per OCR gelesen.")

        image = self._capture_reference_region(self.TANK_LEVEL_REFERENCE)
        image = image.resize(
            (
                image.width * 3,
                image.height * 3,
            )
        )
        debug_dir = Path(__file__).resolve().parent / "references" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

        debug_file = debug_dir / "ocr_tank_fuel_level_current.png"
        image.save(debug_file)

        self._log("TankController: OCR-Ausschnitt gespeichert unter: " f"{debug_file}")

        ocr_engine = self._get_ocr_engine()

        self._log("TankController: OCR liest den gespeicherten Bildausschnitt.")

        result = ocr_engine.read_image(str(debug_file))

        if not result.success:
            raise TankControllerError(
                "OCR konnte im Bereich des Carrier-Tankfüllstands "
                "keinen Text erkennen."
            )

        self._log("TankController: OCR-Text Tankfüllstand: " f"{result.text!r}")

        self._log("TankController: OCR-Konfidenz: " f"{result.confidence * 100:.2f} %.")

        current, maximum = self._parse_tank_level(result.text)

        percent = current / maximum * 100.0

        # Laut GUI-Tooltip wird erst unterhalb des
        # Schwellenwertes nachgetankt.
        needs_refuel = percent < self.refuel_threshold

        self._log(
            "TankController: Carrier-Tank: " f"{current}/{maximum} ({percent:.1f} %)."
        )

        self._log(
            "TankController: Eingestellter Schwellenwert: "
            f"{self.refuel_threshold} %."
        )

        if needs_refuel:
            self._log(
                "TankController: Der Tankfüllstand liegt unter "
                "dem Schwellenwert. Nachtanken ist erforderlich."
            )
        else:
            self._log(
                "TankController: Der Tankfüllstand liegt nicht unter "
                "dem Schwellenwert. Nachtanken ist nicht erforderlich."
            )

        return (
            current,
            maximum,
            percent,
            needs_refuel,
        )

    def run(self) -> bool:
        """
        Führt den aktuellen TankController-Prüflauf aus.

        Der Prüflauf:
            - öffnet das Tritiumdepot,
            - liest den Tankfüllstand per OCR,
            - berücksichtigt den GUI-Schwellenwert,
            - protokolliert die Entscheidung.

        Es wird noch kein Tritium übertragen.
        """

        self._set_status(TankStatus.RUNNING)

        try:
            self._log("--------------------------------")
            self._log("TankController: Testlauf wird gestartet.")

            self.reach_main_menu()
            self.open_carrier_services()
            self.select_tritium_depot()
            self.open_tritium_depot()

            _, _, _, needs_refuel = self.check_carrier_tank()

            if needs_refuel:

                self._log("TankController: Nachtanken erforderlich.")

                ship_has_tritium = self.detect_ship_tritium()

                if ship_has_tritium:
                    self._log(
                        "TankController: Direkter Tankweg erkannt. "
                        "Das Schiff enthält Tritium."
                    )

                    self.donate_ship_tritium_to_carrier()

                else:
                    self._log(
                        "TankController: Langer Tankweg erkannt. "
                        "Das Schiff muss zunächst über Menü T4 "
                        "mit Tritium beladen werden."
                    )

                    self._log(
                        "TankController: Rechtes Schiffsmenü "
                        "wird mit Taste 4 geöffnet."
                    )

                    self.press_key(
                        "4",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

                    self._log(
                        "TankController: Taste 4 wurde gedrückt. "
                        "Das rechte Schiffsmenü ist geöffnet."
                    )

                    self.select_ship_inventory()

                    self._log("TankController: Der Reiter „INVENTAR“ ist aktiv.")

                    self.select_transfer()

                    self._log("TankController: Der Button „TRANSFER“ ist aktiv.")

                    self._log("TankController: Transfermenü wird mit SPACE geöffnet.")

                    self.press_key(
                        "space",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

                    self._log("TankController: Transfermenü wurde geöffnet.")

                    self._log(
                        "TankController: Taste W wird einmal gedrückt, "
                        "um den Fokus von den unteren Schaltflächen "
                        "in die Transferliste zu setzen."
                    )

                    self.press_key(
                        "w",
                        hold_time=0.12,
                        after_delay=0.60,
                    )

                    self._log(
                        "TankController: Der Fokus wurde in die Transferliste bewegt."
                    )

                    self.find_tritium_in_transfer_menu()

                    self.select_transfer_abbrechen()

                    self._log("TankController: „ABBRECHEN“ ist aktiv.")

                    self.select_transfer_bestaetigen()

                    self._log("TankController: „TRANSFER BESTÄTIGEN“ ist aktiv.")

                    self._log("TankController: Übertragung wird mit SPACE bestätigt.")

                    self.press_key(
                        "space",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

                    self._log("TankController: Übertragung wurde bestätigt.")

                    self._log(
                        "TankController: Taste 4 wird gedrückt, "
                        "um das rechte Schiffsmenü wieder zu öffnen."
                    )

                    self.press_key(
                        "4",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

                    self._log(
                        "TankController: Rechtes Schiffsmenü wurde geöffnet. "
                        "Die Tritiumanzeige im Depot ist noch nicht aktualisiert."
                    )

                    self._log(
                        "TankController: BACKSPACE wird gedrückt, "
                        "damit Elite den Tritiumzustand des Schiffes aktualisiert."
                    )

                    self.press_key(
                        "backspace",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

                    self._log(
                        "TankController: Der lange Tankweg ist abgeschlossen. "
                        "Die Tankroutine wird jetzt erneut von vorne gestartet."
                    )

                    self.reach_main_menu()
                    self.open_carrier_services()
                    self.select_tritium_depot()
                    self.open_tritium_depot()

                    _, _, _, restart_needs_refuel = self.check_carrier_tank()

                    if not restart_needs_refuel:
                        self._log(
                            "TankController: Nach dem Neustart ist kein weiteres "
                            "Nachtanken erforderlich."
                        )

                        self._log(
                            "TankController: Tritiumdepot wird mit BACKSPACE verlassen."
                        )

                        self.press_key(
                            "backspace",
                            hold_time=0.20,
                            after_delay=1.00,
                        )

                        self._log("TankController: Tritiumdepot wurde verlassen.")
                    else:
                        self._log(
                            "TankController: Nach dem Neustart ist weiterhin "
                            "Nachtanken erforderlich."
                        )

                        restart_ship_has_tritium = self.detect_ship_tritium()

                        if not restart_ship_has_tritium:
                            raise TankControllerError(
                                "Nach dem langen Tankweg wurde im Schiff "
                                "kein Tritium erkannt. Ein zweiter langer Tankweg "
                                "wird aus Sicherheitsgründen nicht gestartet."
                            )

                        self._log(
                            "TankController: Das Tritium im Schiff wurde erkannt. "
                            "Der direkte Spendenweg wird ausgeführt."
                        )

                        self.donate_ship_tritium_to_carrier()

            else:

                self._log("TankController: Carrier besitzt ausreichend Tritium.")

                self._log("TankController: Tritiumdepot wird mit BACKSPACE verlassen.")

                self.press_key(
                    "backspace",
                    hold_time=0.20,
                    after_delay=1.00,
                )

                self._log("TankController: Tritiumdepot wurde verlassen.")

            self._log(
                "TankController: Test erfolgreich beendet. "
                "Der Tankvorgang wurde vollständig ausgeführt."
            )

            self._set_status(TankStatus.SUCCESS)

            return True

        except Exception:
            self._set_status(TankStatus.ERROR)
            raise
