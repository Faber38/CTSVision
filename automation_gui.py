from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Qt,
    QDateTime,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDateTimeEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from journal_monitor import JournalMonitor
from keyboard_control import press_key, type_text
from menu_controller import MenuController
from mouse_control import (
    click_reference_center,
    left_click,
    move_to_reference_center,
)
from navigator import Navigator
from route_info_window import RouteInfoWindow
from route_manager import RouteManager, RouteManagerError
from settings_manager import (
    load_settings,
    save_settings,
)
from vision import Vision
from vision_wizard import VisionWizardWindow
from tank_controller import TankController, TankStatus
from tank_wizard import TankWizardWindow


class TankTestWorker(QObject):
    """
    Führt die Tankfunktions-Prüfung außerhalb des GUI-Threads aus.

    Der aktuelle Prüfablauf:
        - Menü 1 sicher erreichen
        - Carrier-Dienste öffnen
        - Tritiumdepot anwählen
        - Tritiumdepot öffnen und per Vision bestätigen
        - anschließend stoppen

    Es wird noch kein Tritium übertragen.
    """

    log_message = Signal(str)
    tank_status_changed = Signal(str)
    completed = Signal()
    failed = Signal(str)
    finished = Signal()

    @Slot()
    def run(self) -> None:
        try:
            vision = Vision()

            navigator = Navigator(
                vision=vision,
                press_key=press_key,
            )

            menu_controller = MenuController(
                vision=vision,
                navigator=navigator,
                press_key=press_key,
            )

            tank_controller = TankController(
                menu_controller=menu_controller,
                navigator=navigator,
                press_key=press_key,
                log_message=self.log_message.emit,
                status_changed=lambda status: self.tank_status_changed.emit(
                    status.value
                ),
            )

            tank_controller.run()

            self.completed.emit()

        except Exception as exc:
            self.failed.emit(str(exc))

        finally:
            self.finished.emit()


class AutomationWorker(QObject):
    """
    Führt den Navigationstest außerhalb des GUI-Threads aus.

    Aktueller Testablauf:
        - aktuelles Ziel aus der Route holen
        - Galaxiekarte öffnen
        - Suchfeld aktivieren
        - Systemnamen eingeben
        - ENTER drücken
        - danach stoppen
    """

    log_message = Signal(str)
    tank_status_changed = Signal(str)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        route_manager: RouteManager,
    ) -> None:
        super().__init__()

        self.settings = load_settings()

        self.route_manager = route_manager
        self.stop_requested = False
        self.carrier_jump_event = threading.Event()

    @Slot()
    def request_stop(self) -> None:
        """
        Fordert das kontrollierte Beenden des Testlaufs an.
        """

        self.stop_requested = True

    def on_carrier_jump(self) -> None:
        """
        Wird vom JournalMonitor aufgerufen, sobald ein CarrierJump
        erkannt wurde.
        """

        self.carrier_jump_event.set()

    def _check_stop(self) -> bool:
        if not self.stop_requested:
            return False

        self.log_message.emit("Stop wurde angefordert.")

        return True

    def _run_tank_routine(
        self,
        *,
        tank_finished_event: threading.Event,
        tank_result: dict[str, object],
    ) -> None:
        """
        Führt die Tankroutine parallel zur Abkühlzeit aus.

        Das Ergebnis wird in tank_result abgelegt. Das Event wird
        unabhängig von Erfolg oder Fehler immer gesetzt.
        """

        try:
            self.log_message.emit(
                "Automatische Tankroutine wird während der Abkühlzeit gestartet."
            )

            vision = Vision()

            navigator = Navigator(
                vision=vision,
                press_key=press_key,
            )

            menu_controller = MenuController(
                vision=vision,
                navigator=navigator,
                press_key=press_key,
            )

            tank_controller = TankController(
                menu_controller=menu_controller,
                navigator=navigator,
                press_key=press_key,
                log_message=self.log_message.emit,
                status_changed=lambda status: self.tank_status_changed.emit(
                    status.value
                ),
            )

            tank_controller.run()

            tank_result["success"] = True

            self.log_message.emit("Automatische Tankroutine wurde erfolgreich beendet.")

        except Exception as exc:
            tank_result["success"] = False
            tank_result["error"] = exc

            self.log_message.emit(
                "Automatische Tankroutine ist fehlgeschlagen: " f"{exc}"
            )

        finally:
            tank_finished_event.set()

    @Slot()
    def run(self) -> None:
        """
        Führt den aktuellen Integrationstest aus.
        """

        try:
            current_jump = self.route_manager.get_current_jump()

            if current_jump is None:
                raise RuntimeError("Die Route ist bereits abgeschlossen.")

            system_name = current_jump.system.strip()

            if not system_name:
                raise RuntimeError(
                    "Das aktuelle Sprungziel besitzt " "keinen Systemnamen."
                )

            self.log_message.emit(f"Aktuelles Ziel: {system_name}")

            if self._check_stop():
                return

            vision = Vision()

            navigator = Navigator(
                vision=vision,
                press_key=press_key,
            )

            controller = MenuController(
                vision=vision,
                navigator=navigator,
                press_key=press_key,
            )

            self.log_message.emit(
                "Ausgangszustand wird gesucht. "
                "Falls nötig, wird mit BACKSPACE "
                "zu Menü 1 zurückgegangen..."
            )

            main_menu_reached = False
            last_error: Exception | None = None

            for attempt in range(1, 6):
                if self._check_stop():
                    return

                self.log_message.emit(f"Menü-1-Erkennung: " f"Versuch {attempt}/5...")

                try:
                    controller.navigator.goto(
                        "main_menu",
                        "main_menu_block_carrierdienste",
                        max_actions=14,
                        state_timeout=4.0,
                    )

                    main_menu_reached = True

                    self.log_message.emit(
                        "Menü 1 wurde sicher erkannt. "
                        "Carrier-Dienste sind angewählt."
                    )

                    break

                except Exception as exc:
                    last_error = exc

                    self.log_message.emit("Menü 1 wurde nicht erkannt: " f"{exc}")

                    if attempt >= 5:
                        break

                    self.log_message.emit(
                        "BACKSPACE wird gedrückt, " "um eine Menüebene zurückzugehen..."
                    )

                    press_key(
                        "backspace",
                        hold_time=0.20,
                        after_delay=2.00,
                    )

            if not main_menu_reached:
                raise RuntimeError(
                    "Menü 1 konnte auch nach 5 Versuchen "
                    "nicht erreicht beziehungsweise erkannt "
                    "werden. "
                    f"Letzter Fehler: {last_error}"
                )

            controller.open_menu(
                key="space",
                prefix="carrier_services_",
                loading_time=5.0,
                timeout=8.0,
            )

            if self._check_stop():
                return

            self.log_message.emit("Menü 2: Carrier-Management " "wird angewählt...")

            controller.navigator.goto(
                "carrier_services",
                "carrier_services_block_carriermanagement",
                max_actions=14,
                state_timeout=4.0,
            )

            controller.open_menu(
                key="space",
                prefix="carrier_management_",
                loading_time=5.0,
                timeout=8.0,
            )

            if self._check_stop():
                return

            self.log_message.emit("Menü 3 erreicht. " "Galaxiekarte wird geöffnet...")

            controller.open_galaxy_map()

            self.log_message.emit(
                "Warte 5 Sekunden auf den Aufbau " "der Galaxiekarte..."
            )

            time.sleep(5.0)

            if self._check_stop():
                return

            self.log_message.emit("Suchfeld wird aktiviert...")

            controller.open_galaxy_search()

            if self._check_stop():
                return

            self.log_message.emit(f"Systemname wird eingegeben: " f"{system_name}")

            type_text(system_name)

            self.log_message.emit("Warte 2 Sekunden auf das Suchergebnis...")

            time.sleep(2.0)

            if self._check_stop():
                return

            self.log_message.emit(
                "Erster Suchtreffer wird mit " "der Maus ausgewählt..."
            )

            click_reference_center(
                "galaxiekarte_erstes_suchergebnis",
                after_delay=1.00,
            )

            self.log_message.emit(
                "Warte 5 Sekunden, bis die Galaxiekarte "
                "vollständig zur Ruhe gekommen ist..."
            )

            time.sleep(5.0)

            self.log_message.emit("Maus wird auf die Schaltfläche " "positioniert...")

            click_x, click_y = move_to_reference_center(
                "galaxiekarte_carrier_target",
                after_delay=0.75,
            )

            self.log_message.emit(
                f"Maus positioniert bei " f"X={click_x}, Y={click_y}."
            )

            self.log_message.emit("Prüfe die Anzeige " "„Carrier-Ziel festlegen“...")

            deadline = time.monotonic() + 10.0
            best_similarity = 0.0
            matched = False

            while time.monotonic() < deadline:
                matched, similarity = vision.check(
                    "galaxiekarte_carrier_target",
                    threshold=0.95,
                )

                best_similarity = max(
                    best_similarity,
                    similarity,
                )

                if matched:
                    break

                time.sleep(0.25)

            self.log_message.emit(
                "Carrier-Ziel-Anzeige: " f"{best_similarity * 100:.2f} %"
            )

            if not matched:
                raise RuntimeError(
                    "Die Anzeige „Carrier-Ziel festlegen“ "
                    "wurde vor dem Mausklick nicht sicher "
                    "erkannt. "
                    f"Bester Wert: "
                    f"{best_similarity * 100:.2f} %"
                )

            self.log_message.emit("Anzeige erkannt. " "Mausklick wird ausgeführt...")

            left_click(
                after_delay=2.00,
            )

            self.log_message.emit("Mausklick erfolgreich ausgeführt.")

            self.log_message.emit(
                "Carrier-Ziel wurde nach dem Mausklick "
                "sicher erkannt. Der Ablauf stoppt für "
                "die Prüfung des nächsten Menüs."
            )

            self.log_message.emit(
                "Sprung wurde angefordert. " "Warte auf CarrierJump im Journal..."
            )

            while not self.carrier_jump_event.wait(timeout=1.0):
                if self._check_stop():
                    return

            self.log_message.emit("CarrierJump wurde vom Journal erkannt.")

            cooldown_seconds = 240

            auto_refuel_enabled = bool(
                self.settings.get(
                    "auto_refuel_enabled",
                    True,
                )
            )

            tank_finished_event: threading.Event | None = None
            tank_result: dict[str, object] | None = None
            tank_thread: threading.Thread | None = None

            if auto_refuel_enabled:
                tank_finished_event = threading.Event()
                tank_result = {
                    "success": False,
                    "error": None,
                }

                tank_thread = threading.Thread(
                    target=self._run_tank_routine,
                    kwargs={
                        "tank_finished_event": tank_finished_event,
                        "tank_result": tank_result,
                    },
                    name="CTSVision-TankRoutine",
                    daemon=True,
                )

                tank_thread.start()

                self.log_message.emit(
                    "Die Tankroutine läuft parallel zur vierminütigen Abkühlzeit."
                )

            else:
                self.log_message.emit(
                    "Automatisches Betanken ist deaktiviert. "
                    "Es wird nur die Abkühlzeit abgewartet."
                )

            self.log_message.emit(
                "Abkühlzeit läuft: 4 Minuten bis zum nächsten Sprung."
            )

            for remaining_seconds in range(
                cooldown_seconds,
                0,
                -1,
            ):
                if self._check_stop():
                    return

                if remaining_seconds == cooldown_seconds or remaining_seconds % 15 == 0:
                    minutes, seconds = divmod(
                        remaining_seconds,
                        60,
                    )

                    if auto_refuel_enabled and tank_finished_event is not None:
                        tank_status = (
                            "Tankroutine beendet"
                            if tank_finished_event.is_set()
                            else "Tankroutine läuft"
                        )

                        self.log_message.emit(
                            f"Abkühlzeit: {minutes:02d}:{seconds:02d} – "
                            f"{tank_status}"
                        )
                    else:
                        self.log_message.emit(
                            f"Abkühlzeit: {minutes:02d}:{seconds:02d}"
                        )

                time.sleep(1)

            self.log_message.emit("Die Abkühlzeit ist beendet.")

            if auto_refuel_enabled:
                if tank_finished_event is None or tank_result is None:
                    raise RuntimeError(
                        "Interner Fehler: Die Tankroutine wurde nicht korrekt vorbereitet."
                    )

                if not tank_finished_event.is_set():
                    self.log_message.emit(
                        "Die Tankroutine läuft noch. "
                        "Der nächste Sprung bleibt gesperrt, bis sie beendet ist."
                    )

                while not tank_finished_event.wait(timeout=1.0):
                    if self._check_stop():
                        return

                    self.log_message.emit(
                        "Warte auf das Ende der Tankroutine. "
                        "Es wird noch kein neuer Sprung gestartet."
                    )

                if tank_thread is not None:
                    tank_thread.join(timeout=1.0)

                if not bool(tank_result.get("success", False)):
                    error = tank_result.get("error")

                    raise RuntimeError(
                        "Der nächste Sprung wurde gesperrt, weil die "
                        f"Tankroutine fehlgeschlagen ist: {error}"
                    )

                self.log_message.emit(
                    "Tankroutine und Abkühlzeit sind beendet. "
                    "Der nächste Sprung ist jetzt freigegeben."
                )

            else:
                self.log_message.emit(
                    "Abkühlzeit beendet. " "Der nächste Sprung ist jetzt freigegeben."
                )

            self.route_manager.mark_current_completed()

            self.log_message.emit(f"Ziel als erledigt markiert: " f"{system_name}")

            self.completed.emit(system_name)

        except Exception as exc:
            self.failed.emit(str(exc))

        finally:
            self.finished.emit()


class AutomationWindow(QMainWindow):
    """
    Hauptfenster der Carrier-Automatik.
    """

    def __init__(self) -> None:
        super().__init__()

        self.route_file: Path | None = None
        self.route_manager: RouteManager | None = None

        self.route_info_window: RouteInfoWindow | None = None

        self.vision_wizard_window: VisionWizardWindow | None = None
        self.tank_wizard_window: TankWizardWindow | None = None

        self.automation_thread: QThread | None = None
        self.automation_worker: AutomationWorker | None = None

        self.tank_test_thread: QThread | None = None
        self.tank_test_worker: TankTestWorker | None = None

        self.start_next_jump = False
        self.settings = load_settings()

        self.scheduled_start_timer = QTimer(self)
        self.scheduled_start_timer.setInterval(1000)
        self.scheduled_start_timer.timeout.connect(self._check_scheduled_start)
        self.scheduled_start_datetime: datetime | None = None
        self.scheduled_start_active = False

        self.setWindowTitle("CTSVision - Carrier Automation | " "CMDR Faber38")

        self.resize(
            800,
            600,
        )

        self._build_ui()
        self._apply_theme()

        journal_directory = str(
            self.settings.get(
                "journal_directory",
                "",
            )
        )

        self.journal_directory_edit.setText(journal_directory)

        last_route = str(
            self.settings.get(
                "last_route",
                "",
            )
        )

        if last_route:
            self.route_file = Path(last_route)
            self.route_edit.setText(last_route)

            if self.route_file.exists():
                try:
                    self.route_manager = RouteManager(self.route_file)

                    self.refresh_route_display()

                    self.log(
                        "Letzte Route automatisch geladen: " f"{self.route_file.name}"
                    )

                except RouteManagerError as exc:
                    self.log("Automatisches Laden der Route " f"fehlgeschlagen: {exc}")

    def _build_ui(self) -> None:

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # --------------------------------------------------
        # Kopfbereich
        # --------------------------------------------------

        header_layout = QHBoxLayout()

        title_block = QVBoxLayout()
        title_block.setSpacing(1)

        title_label = QLabel("CTSVision")
        title_label.setObjectName("appTitle")

        subtitle_label = QLabel("Fleet Carrier Automation  •  CMDR Faber38")
        subtitle_label.setObjectName("appSubtitle")

        title_block.addWidget(title_label)
        title_block.addWidget(subtitle_label)

        header_layout.addLayout(title_block)
        header_layout.addStretch()

        self.version_label = QLabel("Version 1.0.1\nStable")
        self.version_label.setObjectName("versionBadge")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setMinimumWidth(110)

        header_layout.addWidget(self.version_label)
        layout.addLayout(header_layout)

        # Oberer Bereich: Inhalte links, Assistenten rechts
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)

        content_layout = QVBoxLayout()
        top_layout.addLayout(content_layout, 1)

        # --------------------------------------------------
        # Route
        # --------------------------------------------------

        route_box = QGroupBox("Route")
        route_box.setObjectName("routeBox")
        content_layout.addWidget(route_box)

        route_layout = QGridLayout(route_box)

        self.route_edit = QLineEdit()
        self.route_edit.setReadOnly(True)

        self.route_button = QPushButton("Route auswählen...")
        self.route_button.clicked.connect(self.select_route)

        self.route_info_button = QPushButton("Routen-Info")
        self.route_info_button.clicked.connect(self.open_route_info)

        route_layout.addWidget(QLabel("Datei:"), 0, 0)
        route_layout.addWidget(self.route_edit, 0, 1)
        route_layout.addWidget(self.route_button, 0, 2)
        route_layout.addWidget(self.route_info_button, 0, 3)

        # --------------------------------------------------
        # Journal
        # --------------------------------------------------

        self.journal_directory_edit = QLineEdit()
        self.journal_directory_edit.setReadOnly(True)

        self.journal_button = QPushButton("Journalordner...")
        self.journal_button.clicked.connect(self.select_journal_directory)

        route_layout.addWidget(QLabel("Journalordner:"), 1, 0)
        route_layout.addWidget(self.journal_directory_edit, 1, 1, 1, 2)
        route_layout.addWidget(self.journal_button, 1, 3)

        # --------------------------------------------------
        # Geplanter Start
        # --------------------------------------------------

        self.scheduled_start_checkbox = QCheckBox("Startzeit festlegen")
        self.scheduled_start_checkbox.setObjectName("scheduledStartCheck")
        self.scheduled_start_checkbox.setToolTip(
            "Ist diese Option aktiviert, beginnt die Route erst "
            "zum ausgewählten Datum und zur ausgewählten Uhrzeit."
        )

        self.scheduled_start_edit = QDateTimeEdit()
        self.scheduled_start_edit.setObjectName("scheduledStartEdit")
        self.scheduled_start_edit.setDisplayFormat("dd.MM.yyyy  HH:mm")
        self.scheduled_start_edit.setCalendarPopup(True)
        self.scheduled_start_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.scheduled_start_edit.setDateTime(
            QDateTime.currentDateTime().addSecs(5 * 60)
        )
        self.scheduled_start_edit.setEnabled(False)

        self.scheduled_start_status = QLabel("Sofortstart")
        self.scheduled_start_status.setObjectName("scheduledStartStatus")

        self.scheduled_start_checkbox.toggled.connect(self._on_scheduled_start_toggled)
        self.scheduled_start_edit.dateTimeChanged.connect(
            self._update_scheduled_start_preview
        )

        route_layout.addWidget(self.scheduled_start_checkbox, 2, 0)
        route_layout.addWidget(self.scheduled_start_edit, 2, 1, 1, 2)
        route_layout.addWidget(self.scheduled_start_status, 2, 3)

        # --------------------------------------------------
        # Informationen
        # --------------------------------------------------

        info_box = QGroupBox("Informationen")
        info_box.setObjectName("infoBox")
        content_layout.addWidget(info_box)

        info_layout = QGridLayout(info_box)

        self.total_label = QLabel("-")
        self.progress_label = QLabel("-")
        self.target_label = QLabel("-")

        for value_label in (
            self.total_label,
            self.progress_label,
            self.target_label,
        ):
            value_label.setObjectName("infoValue")

        self.target_label.setObjectName("targetValue")

        info_layout.addWidget(QLabel("Anzahl Ziele:"), 0, 0)
        info_layout.addWidget(self.total_label, 0, 1)
        info_layout.addWidget(QLabel("Fortschritt:"), 1, 0)
        info_layout.addWidget(self.progress_label, 1, 1)
        info_layout.addWidget(QLabel("Aktuelles Ziel:"), 2, 0)
        info_layout.addWidget(self.target_label, 2, 1)

        # --------------------------------------------------
        # Tanken
        # --------------------------------------------------

        tank_box = QGroupBox("Tanken")
        tank_box.setObjectName("tankBox")
        content_layout.addWidget(tank_box)

        tank_layout = QGridLayout(tank_box)
        tank_layout.setHorizontalSpacing(12)
        tank_layout.setVerticalSpacing(7)
        tank_layout.setColumnStretch(0, 1)
        tank_layout.setColumnStretch(1, 0)
        tank_layout.setColumnStretch(2, 0)

        self.auto_refuel_checkbox = QCheckBox("Carrier automatisch betanken")
        self.auto_refuel_checkbox.setObjectName("autoRefuelCheck")
        self.auto_refuel_checkbox.setToolTip(
            "Ist diese Option aktiviert, wird die Tankroutine nach einem Sprung "
            "parallel zur vierminütigen Abkühlzeit ausgeführt. "
            "Ein neuer Sprung startet erst, wenn beide Vorgänge beendet sind."
        )

        self.refuel_threshold_spinbox = QSpinBox()
        self.refuel_threshold_spinbox.setObjectName("tankSpinBox")
        self.refuel_threshold_spinbox.setRange(1, 105)
        self.refuel_threshold_spinbox.setSuffix(" %")
        self.refuel_threshold_spinbox.setFixedWidth(118)
        self.refuel_threshold_spinbox.setToolTip(
            "Liegt der Carrier-Tank unter diesem Wert, "
            "wird der Tankvorgang gestartet."
        )

        self.tritium_position_spinbox = QSpinBox()
        self.tritium_position_spinbox.setObjectName("tankSpinBox")
        self.tritium_position_spinbox.setRange(-50, 50)
        self.tritium_position_spinbox.setFixedWidth(105)
        self.tritium_position_spinbox.setToolTip(
            "Erwartete Position von TRITIUM in der Transferliste. "
            "Positive Werte bewegen mit W nach oben, negative Werte "
            "mit S nach unten. Bei 0 wird die aktuelle Position geprüft. "
            "Danach sucht CTSVision zusätzlich 2 Zeilen nach oben und "
            "5 Zeilen nach unten."
        )

        threshold_title = QLabel("Tankgrenze")
        threshold_title.setObjectName("tankOptionTitle")

        threshold_hint = QLabel("105 % = Testmodus ")
        threshold_hint.setObjectName("tankOptionHint")

        position_title = QLabel("Tritium-Position")
        position_title.setObjectName("tankOptionTitle")

        position_hint = QLabel("Positive Werte ↑   •   Negative Werte ↓")
        position_hint.setObjectName("tankOptionHint")

        auto_refuel_enabled = bool(self.settings.get("auto_refuel_enabled", True))

        refuel_threshold = int(self.settings.get("carrier_refuel_threshold", 20))

        refuel_threshold = max(1, min(105, refuel_threshold))

        try:
            tritium_position = int(self.settings.get("tritium_list_position", 0))
        except (TypeError, ValueError):
            tritium_position = 0

        tritium_position = max(-50, min(50, tritium_position))

        self.auto_refuel_checkbox.setChecked(auto_refuel_enabled)
        self.refuel_threshold_spinbox.setValue(refuel_threshold)
        self.tritium_position_spinbox.setValue(tritium_position)
        self.refuel_threshold_spinbox.setEnabled(auto_refuel_enabled)
        self.tritium_position_spinbox.setEnabled(auto_refuel_enabled)

        self.auto_refuel_checkbox.toggled.connect(self._on_auto_refuel_toggled)
        self.refuel_threshold_spinbox.valueChanged.connect(self._save_tank_settings)
        self.tritium_position_spinbox.valueChanged.connect(self._save_tank_settings)

        tank_layout.addWidget(
            self.auto_refuel_checkbox,
            0,
            0,
            2,
            1,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        threshold_card = QWidget()
        threshold_card.setObjectName("tankOptionCard")
        threshold_layout = QGridLayout(threshold_card)
        threshold_layout.setContentsMargins(10, 6, 8, 6)
        threshold_layout.setHorizontalSpacing(10)
        threshold_layout.setVerticalSpacing(1)
        threshold_layout.addWidget(threshold_title, 0, 0)
        threshold_layout.addWidget(threshold_hint, 1, 0)
        threshold_layout.addWidget(
            self.refuel_threshold_spinbox,
            0,
            1,
            2,
            1,
            Qt.AlignmentFlag.AlignVCenter,
        )

        position_card = QWidget()
        position_card.setObjectName("tankOptionCard")
        position_layout = QGridLayout(position_card)
        position_layout.setContentsMargins(10, 6, 8, 6)
        position_layout.setHorizontalSpacing(10)
        position_layout.setVerticalSpacing(1)
        position_layout.addWidget(position_title, 0, 0)
        position_layout.addWidget(position_hint, 1, 0)
        position_layout.addWidget(
            self.tritium_position_spinbox,
            0,
            1,
            2,
            1,
            Qt.AlignmentFlag.AlignVCenter,
        )

        tank_layout.addWidget(threshold_card, 0, 1, 2, 1)
        tank_layout.addWidget(position_card, 0, 2, 2, 1)

        # --------------------------------------------------
        # Assistenten und Prüfungen rechts oben
        # --------------------------------------------------

        assistant_box = QGroupBox("Assistenten und Prüfung")
        assistant_box.setObjectName("assistantBox")
        assistant_box.setMinimumWidth(190)
        top_layout.addWidget(assistant_box)

        assistant_layout = QVBoxLayout(assistant_box)

        self.vision_wizard_button = QPushButton("🚀  Sprung Wizard")
        self.vision_wizard_button.setObjectName("assistantButton")
        self.vision_wizard_button.setMinimumHeight(42)
        self.vision_wizard_button.clicked.connect(self.open_vision_wizard)

        self.tank_wizard_button = QPushButton("⛽  Tank Wizard")
        self.tank_wizard_button.setObjectName("assistantButton")
        self.tank_wizard_button.setMinimumHeight(42)
        self.tank_wizard_button.clicked.connect(self.open_tank_wizard)

        self.tank_test_button = QPushButton("✓  Tankfunktion prüfen")
        self.tank_test_button.setObjectName("assistantButton")
        self.tank_test_button.setMinimumHeight(42)
        self.tank_test_button.setToolTip(
            "Prüft die automatische Tankfunktion vor dem Start der Route. "
            "Der aktuelle Test öffnet nur das Tritiumdepot und "
            "überträgt noch kein Tritium."
        )
        self.tank_test_button.clicked.connect(self.start_tank_test)

        assistant_layout.addWidget(self.vision_wizard_button)
        assistant_layout.addWidget(self.tank_wizard_button)
        assistant_layout.addWidget(self.tank_test_button)

        assistant_layout.addSpacing(8)

        self.tank_status_title = QLabel("Tankstatus")
        self.tank_status_title.setStyleSheet("font-weight: bold;")

        self.tank_status_label = QLabel()
        self.tank_status_label.setMinimumHeight(32)
        self.tank_status_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        assistant_layout.addWidget(self.tank_status_title)
        assistant_layout.addWidget(self.tank_status_label)

        self.set_tank_status(TankStatus.IDLE.value)

        assistant_layout.addStretch()

        # --------------------------------------------------
        # Hauptsteuerung
        # --------------------------------------------------

        button_layout = QHBoxLayout()

        self.restart_button = QPushButton("↺  Route neu starten")
        self.restart_button.setObjectName("secondaryButton")
        self.restart_button.clicked.connect(self.restart_route)

        self.resume_button = QPushButton("↪  Route fortsetzen")
        self.resume_button.setObjectName("secondaryButton")
        self.resume_button.clicked.connect(self.refresh_route_display)

        self.start_button = QPushButton("▶  Automatik starten")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(36)
        self.start_button.setMinimumWidth(180)
        self.start_button.clicked.connect(self.start_automation)

        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.setMinimumHeight(36)
        self.stop_button.setMinimumWidth(90)
        self.stop_button.clicked.connect(self.stop_automation)
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.restart_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        status_box = QGroupBox("Status")
        status_box.setObjectName("statusBox")
        layout.addWidget(status_box, 1)

        status_layout = QVBoxLayout(status_box)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setObjectName("statusLog")
        self.status_log.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        status_layout.addWidget(self.status_log)

        self.log("CTSVision Carrier Automation gestartet.")

        self.journal = JournalMonitor()
        self.journal.event_received.connect(self.on_journal_event)
        self.journal.status_changed.connect(self.on_journal_status)
        self.journal.error_occurred.connect(self.on_journal_error)
        self.journal.start()

    # --------------------------------------------------

    def _apply_theme(self) -> None:
        """Wendet das zentrale, ruhige CTSVision-Erscheinungsbild an."""

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f3f6fa;
                color: #1f2933;
                font-size: 10pt;
            }

            QLabel#appTitle {
                font-size: 20pt;
                font-weight: 700;
                color: #123f66;
            }

            QLabel#appSubtitle {
                color: #68798a;
                font-size: 9.5pt;
                padding-bottom: 4px;
            }

            QLabel#versionBadge {
                border: 1px solid #b8cce0;
                border-radius: 12px;
                padding: 6px 12px;
                background-color: #eaf3fb;
                color: #315f86;
                font-weight: 700;
                line-height: 1.2;
            }

            QGroupBox {
                border: 1px solid #c8d3dd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 700;
                background-color: #ffffff;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #334e68;
            }

            QGroupBox#routeBox {
                background-color: #f3f8fd;
                border-color: #a9c9e5;
            }

            QGroupBox#routeBox::title {
                color: #23699d;
            }

            QGroupBox#infoBox {
                background-color: #f1faf9;
                border-color: #9fd5d0;
            }

            QGroupBox#infoBox::title {
                color: #247d78;
            }

            QGroupBox#tankBox {
                background-color: #f4faf3;
                border-color: #add2a9;
            }

            QGroupBox#tankBox::title {
                color: #397b3b;
            }

            QCheckBox#autoRefuelCheck {
                font-weight: 600;
                color: #2f6433;
                padding: 4px 2px;
            }

            QCheckBox#scheduledStartCheck {
                font-weight: 600;
                color: #23699d;
                padding: 4px 2px;
            }

            QDateTimeEdit#scheduledStartEdit {
                min-height: 28px;
                background-color: #ffffff;
                border: 1px solid #a9c9e5;
                border-radius: 5px;
                padding: 4px 7px;
                color: #234f73;
                font-weight: 600;
            }

            QDateTimeEdit#scheduledStartEdit:disabled {
                color: #8d99a5;
                background-color: #edf1f4;
                border-color: #d4dade;
            }

            QLabel#scheduledStartStatus {
                color: #315f86;
                background-color: #eaf3fb;
                border: 1px solid #b8cce0;
                border-radius: 5px;
                padding: 4px 7px;
                font-weight: 700;
            }

            QWidget#tankOptionCard {
                background-color: #ffffff;
                border: 1px solid #c6ddc3;
                border-radius: 7px;
            }

            QLabel#tankOptionTitle {
                color: #315d35;
                font-size: 9.5pt;
                font-weight: 700;
                background: transparent;
            }

            QLabel#tankOptionHint {
                color: #718074;
                font-size: 8pt;
                background: transparent;
            }

            QSpinBox#tankSpinBox {
                min-height: 30px;
                font-weight: 700;
                color: #234a28;
                background-color: #fbfefb;
                border-color: #a9c9a5;
            }

            QGroupBox#assistantBox {
                background-color: #f7f4fc;
                border-color: #c7b6e1;
            }

            QGroupBox#assistantBox::title {
                color: #7153a1;
            }

            QGroupBox#statusBox {
                background-color: #f7f9fc;
                border-color: #b9c8d6;
            }

            QGroupBox#statusBox::title {
                color: #415f78;
            }

            QLineEdit, QSpinBox, QTextEdit {
                background-color: rgba(255, 255, 255, 235);
                border: 1px solid #b8c5d0;
                border-radius: 5px;
                padding: 5px;
                selection-background-color: #2d78b7;
            }

            QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
                border: 1px solid #2d78b7;
                background-color: #ffffff;
            }

            QSpinBox:disabled, QLineEdit:disabled {
                color: #8d99a5;
                background-color: #edf1f4;
            }

            /* Pfeiltasten der Zahlenfelder:
               oben = erhöhen (grün), unten = verringern (orange) */
            QSpinBox {
                padding-right: 27px;
            }

            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 24px;
                background-color: #dff3e3;
                border-left: 1px solid #9fc9a8;
                border-bottom: 1px solid #9fc9a8;
                border-top-right-radius: 4px;
            }

            QSpinBox::up-button:hover {
                background-color: #bfe6c8;
                border-color: #6eaf7d;
            }

            QSpinBox::up-button:pressed {
                background-color: #9fd7ab;
            }

            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 24px;
                background-color: #fff0d7;
                border-left: 1px solid #e0b879;
                border-top: 1px solid #e0b879;
                border-bottom-right-radius: 4px;
            }

            QSpinBox::down-button:hover {
                background-color: #ffdca5;
                border-color: #ca9140;
            }

            QSpinBox::down-button:pressed {
                background-color: #f5c77f;
            }

            QSpinBox::up-button:disabled,
            QSpinBox::down-button:disabled {
                background-color: #e8ecef;
                border-color: #cfd6dc;
            }

            QPushButton {
                min-height: 28px;
                padding: 5px 11px;
                border: 1px solid #aebbc7;
                border-radius: 6px;
                background-color: #f8fafc;
                color: #243746;
            }

            QPushButton:hover {
                background-color: #e8f2fa;
                border-color: #6f9fc2;
            }

            QPushButton:pressed {
                background-color: #d7e7f3;
            }

            QPushButton:disabled {
                color: #9aa5ae;
                background-color: #edf0f2;
                border-color: #d4dade;
            }

            QPushButton#primaryButton {
                color: white;
                background-color: #2478b5;
                border-color: #1b6399;
                font-weight: 700;
                font-size: 10.5pt;
            }

            QPushButton#primaryButton:hover {
                background-color: #3189c4;
            }

            QPushButton#primaryButton:pressed {
                background-color: #1d689e;
            }

            QPushButton#dangerButton {
                color: #a23030;
                background-color: #fff2f2;
                border-color: #dfa3a3;
                font-weight: 700;
            }

            QPushButton#dangerButton:hover {
                color: #ffffff;
                background-color: #c94b4b;
                border-color: #ad3d3d;
            }

            QPushButton#secondaryButton {
                color: #31566f;
                background-color: #eef5fa;
                border-color: #a8c3d7;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background-color: #deedf7;
                border-color: #79a4c1;
            }

            QPushButton#assistantButton {
                text-align: left;
                padding-left: 14px;
                font-weight: 600;
                color: #5c4387;
                background-color: #ffffff;
                border-color: #c8b9df;
            }

            QPushButton#assistantButton:hover {
                color: #49336f;
                background-color: #eee7f8;
                border-color: #9f86c7;
            }

            QLabel#infoValue {
                color: #205d61;
                font-weight: 700;
            }

            QLabel#targetValue {
                color: #176f9b;
                background-color: #e8f5fc;
                border: 1px solid #aed5e8;
                border-radius: 5px;
                padding: 4px 7px;
                font-size: 11pt;
                font-weight: 700;
            }

            QTextEdit#statusLog {
                font-family: monospace;
                font-size: 9.5pt;
                color: #263746;
                background-color: #fbfdff;
                border-color: #b9c8d6;
            }

            QCheckBox {
                spacing: 7px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            """)

    # --------------------------------------------------

    def log(
        self,
        text: str,
    ) -> None:
        self.status_log.append(text)

    # --------------------------------------------------

    @Slot(str)
    def set_tank_status(
        self,
        status_text: str,
    ) -> None:
        """Aktualisiert die farbige Tankstatus-Anzeige."""

        styles = {
            TankStatus.IDLE.value: (
                "●  Bereit",
                "#6b7280",
                "#f3f4f6",
            ),
            TankStatus.RUNNING.value: (
                "●  Tankvorgang läuft",
                "#b7791f",
                "#fff8dc",
            ),
            TankStatus.SUCCESS.value: (
                "●  Erfolgreich",
                "#2f855a",
                "#e6ffed",
            ),
            TankStatus.ERROR.value: (
                "●  Fehler",
                "#c53030",
                "#fff0f0",
            ),
        }

        text, foreground, background = styles.get(
            status_text,
            (
                f"●  {status_text}",
                "#6b7280",
                "#f3f4f6",
            ),
        )

        self.tank_status_label.setText(text)
        self.tank_status_label.setStyleSheet(
            "QLabel {"
            f"color: {foreground};"
            f"background-color: {background};"
            "border: 1px solid #b8b8b8;"
            "border-radius: 4px;"
            "padding: 5px 8px;"
            "font-weight: bold;"
            "}"
        )

    @Slot(bool)
    def _on_auto_refuel_toggled(
        self,
        enabled: bool,
    ) -> None:
        """
        Aktiviert beziehungsweise deaktiviert die Einstellung
        für den Mindestfüllstand und speichert die Tankoptionen.
        """

        self.refuel_threshold_spinbox.setEnabled(enabled)
        self.tritium_position_spinbox.setEnabled(enabled)
        self._save_tank_settings()

    @Slot()
    def _save_tank_settings(self) -> None:
        """
        Speichert die Tankoptionen in der bestehenden
        CTSVision-Konfigurationsdatei.
        """

        self.settings["auto_refuel_enabled"] = self.auto_refuel_checkbox.isChecked()

        self.settings["carrier_refuel_threshold"] = (
            self.refuel_threshold_spinbox.value()
        )
        self.settings["tritium_list_position"] = self.tritium_position_spinbox.value()

        save_settings(self.settings)

    # --------------------------------------------------

    def _get_route_dialog_directory(self) -> str:
        """
        Ermittelt den Startordner für die Routenauswahl.

        Wenn bereits eine Route bekannt ist, wird deren
        Ordner verwendet. Andernfalls wird der persönliche
        Benutzerordner geöffnet.
        """

        if self.route_file is not None:
            route_parent = self.route_file.expanduser().parent

            if route_parent.exists():
                return str(route_parent)

        last_route = str(
            self.settings.get(
                "last_route",
                "",
            )
        ).strip()

        if last_route:
            last_route_parent = Path(last_route).expanduser().parent

            if last_route_parent.exists():
                return str(last_route_parent)

        return str(Path.home())

    def select_route(self) -> None:

        if self.automation_thread is not None:
            QMessageBox.information(
                self,
                "Automatik läuft",
                (
                    "Während die Automatik läuft, "
                    "kann keine andere Route "
                    "ausgewählt werden."
                ),
            )
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Route auswählen",
            self._get_route_dialog_directory(),
            "CSV (*.csv)",
        )

        if not filename:
            return

        route_file = Path(filename)

        try:
            route_manager = RouteManager(route_file)

        except RouteManagerError as exc:
            QMessageBox.critical(
                self,
                "Route konnte nicht geladen werden",
                str(exc),
            )

            self.log(f"Fehler beim Laden der Route: {exc}")

            return

        self.route_file = route_file
        self.route_manager = route_manager

        self.route_edit.setText(str(self.route_file))

        self.settings["last_route"] = str(self.route_file)

        save_settings(self.settings)

        self.log(f"Route geladen: {self.route_file.name}")

        self.refresh_route_display()

    def select_journal_directory(self) -> None:
        """
        Ermöglicht die Auswahl des Elite-Journalordners.
        """

        current_directory = str(
            self.settings.get(
                "journal_directory",
                "",
            )
        ).strip()

        if not current_directory:
            current_directory = str(Path.home())

        directory = QFileDialog.getExistingDirectory(
            self,
            ("Elite Dangerous " "Journalordner auswählen"),
            current_directory,
        )

        if not directory:
            return

        self.settings["journal_directory"] = directory
        save_settings(self.settings)

        self.journal_directory_edit.setText(directory)

        self.journal.set_journal_directory(directory)

        self.log("Journalordner geändert.")

    # --------------------------------------------------

    def refresh_route_display(self) -> None:
        """
        Aktualisiert Hauptfenster und Routen-Info-Fenster.
        """

        if self.route_manager is None:
            self.total_label.setText("-")
            self.progress_label.setText("-")
            self.target_label.setText("-")

            self.log("Keine Route geladen.")

            return

        info = self.route_manager.get_route_info()

        current_jump = self.route_manager.get_current_jump()

        total_jumps = int(info["total_jumps"])

        completed_jumps = int(info["completed_jumps"])

        progress_percent = float(info["progress_percent"])

        self.total_label.setText(str(total_jumps))

        self.progress_label.setText(
            f"{completed_jumps} von " f"{total_jumps} " f"({progress_percent:.1f} %)"
        )

        if current_jump is None:
            self.target_label.setText("Route abgeschlossen")
        else:
            self.target_label.setText(current_jump.system)

        if self.route_info_window is not None:
            self.route_info_window.update_route(self.route_manager)

    # --------------------------------------------------

    def open_route_info(self) -> None:
        """
        Öffnet das separate Routen-Info-Fenster.
        """

        if self.route_info_window is None:
            self.route_info_window = RouteInfoWindow(parent=self)

        if self.route_manager is None:
            self.route_info_window.clear_route()
        else:
            self.route_info_window.update_route(self.route_manager)

        self.route_info_window.show()
        self.route_info_window.raise_()
        self.route_info_window.activateWindow()

    # --------------------------------------------------

    def open_vision_wizard(self) -> None:
        """
        Öffnet den CTS Vision Wizard.

        Ist das Fenster bereits geöffnet, wird es nur
        wieder in den Vordergrund geholt.
        """

        if self.vision_wizard_window is None:
            self.vision_wizard_window = VisionWizardWindow()

        self.vision_wizard_window.show()
        self.vision_wizard_window.raise_()
        self.vision_wizard_window.activateWindow()

    # --------------------------------------------------

    def open_tank_wizard(self) -> None:
        """
        Öffnet den CTS Tank Wizard.

        Ist das Fenster bereits geöffnet, wird es nur
        wieder in den Vordergrund geholt.
        """

        if self.tank_wizard_window is None:
            self.tank_wizard_window = TankWizardWindow()

        self.tank_wizard_window.show()
        self.tank_wizard_window.raise_()
        self.tank_wizard_window.activateWindow()

    # --------------------------------------------------

    def restart_route(self) -> None:
        """
        Setzt den gespeicherten Fortschritt auf null.
        """

        if self.automation_thread is not None:
            QMessageBox.information(
                self,
                "Automatik läuft",
                (
                    "Der Routenfortschritt kann "
                    "während der Automatik nicht "
                    "zurückgesetzt werden."
                ),
            )
            return

        if self.route_manager is None:
            QMessageBox.information(
                self,
                "Keine Route",
                "Bitte zuerst eine Route auswählen.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Route neu starten",
            (
                "Soll der Fortschritt dieser Route "
                "wirklich auf 0 zurückgesetzt werden?"
            ),
            (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.route_manager.reset()

        except RouteManagerError as exc:
            QMessageBox.critical(
                self,
                ("Fortschritt konnte nicht " "gespeichert werden"),
                str(exc),
            )
            return

        self.log("Routenfortschritt wurde auf 0 " "zurückgesetzt.")

        self.refresh_route_display()

    # --------------------------------------------------

    def start_tank_test(self) -> None:
        """
        Startet die manuelle Tankfunktions-Prüfung.

        Die Prüfung verwendet exakt dieselben Komponenten wie
        der spätere automatische Tankablauf. Elite und CTSVision
        müssen sich dabei auf derselben aktiven Arbeitsfläche befinden.
        """

        if self.automation_thread is not None:
            QMessageBox.information(
                self,
                "Automatik läuft",
                (
                    "Während die Sprungautomatik läuft, "
                    "kann die Tankfunktion nicht geprüft werden."
                ),
            )
            return

        if self.tank_test_thread is not None:
            self.log("Die Tankfunktions-Prüfung läuft bereits.")
            return

        self.log("--------------------------------")
        self.log("Tankfunktions-Prüfung wird gestartet.")
        self.log(
            "Die Prüfung öffnet das Tritiumdepot. "
            "Es wird noch kein Tritium übertragen."
        )

        self._set_tank_test_running(True)

        thread = QThread(self)
        worker = TankTestWorker()

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        worker.log_message.connect(self.log)
        worker.tank_status_changed.connect(self.set_tank_status)
        worker.completed.connect(self.tank_test_completed)
        worker.failed.connect(self.tank_test_failed)
        worker.finished.connect(thread.quit)

        thread.finished.connect(self.tank_test_thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self.tank_test_thread = thread
        self.tank_test_worker = worker

        thread.start()

    # --------------------------------------------------

    @Slot()
    def tank_test_completed(self) -> None:
        """
        Wird aufgerufen, wenn das Tritiumdepot erfolgreich
        geöffnet und erkannt wurde.
        """

        self.log(
            "Tankprüfung erfolgreich: "
            "Das Tritiumdepot wurde geöffnet und sicher erkannt."
        )
        self.log(
            "Die automatische Tankfunktion ist für diesen " "Prüfschritt einsatzbereit."
        )

    # --------------------------------------------------

    @Slot(str)
    def tank_test_failed(
        self,
        error_message: str,
    ) -> None:
        """
        Zeigt einen Fehler der Tankfunktions-Prüfung an.
        """

        self.log(f"Tankprüfung fehlgeschlagen: {error_message}")
        self.log(
            "Die Carrier-Automatik sollte erst gestartet werden, "
            "wenn die Ursache behoben ist."
        )

        QMessageBox.critical(
            self,
            "Tankprüfung fehlgeschlagen",
            error_message,
        )

    # --------------------------------------------------

    @Slot()
    def tank_test_thread_finished(self) -> None:
        """
        Räumt den Worker der Tankfunktions-Prüfung auf.
        """

        self.tank_test_thread = None
        self.tank_test_worker = None

        self._set_tank_test_running(False)

        self.log("Tankfunktions-Prüfung wurde beendet.")

    # --------------------------------------------------

    def _set_tank_test_running(
        self,
        running: bool,
    ) -> None:
        """
        Sperrt während der Tankfunktions-Prüfung alle
        Bedienelemente, die einen zweiten Ablauf starten könnten.
        """

        self.start_button.setEnabled(not running)
        self.tank_test_button.setEnabled(not running)

        self.route_button.setEnabled(not running)
        self.restart_button.setEnabled(not running)
        self.resume_button.setEnabled(not running)

        self.vision_wizard_button.setEnabled(not running)
        self.tank_wizard_button.setEnabled(not running)

        self.auto_refuel_checkbox.setEnabled(not running)

        tank_controls_enabled = not running and self.auto_refuel_checkbox.isChecked()
        self.refuel_threshold_spinbox.setEnabled(tank_controls_enabled)
        self.tritium_position_spinbox.setEnabled(tank_controls_enabled)

        if running:
            self.tank_test_button.setText("●  Tankprüfung läuft...")
        else:
            self.tank_test_button.setText("✓  Tankfunktion prüfen")

    # --------------------------------------------------

    @Slot(bool)
    def _on_scheduled_start_toggled(self, enabled: bool) -> None:
        """Aktiviert oder deaktiviert die Auswahl einer Startzeit."""

        self.scheduled_start_edit.setEnabled(enabled)

        if enabled:
            minimum = QDateTime.currentDateTime().addSecs(60)
            self.scheduled_start_edit.setMinimumDateTime(minimum)

            if self.scheduled_start_edit.dateTime() < minimum:
                self.scheduled_start_edit.setDateTime(
                    QDateTime.currentDateTime().addSecs(5 * 60)
                )
        elif self.scheduled_start_active:
            self._cancel_scheduled_start("Geplanter Start wurde aufgehoben.")

        self._update_scheduled_start_preview()

    @Slot()
    def _update_scheduled_start_preview(self) -> None:
        """Aktualisiert die Anzeige der verbleibenden Wartezeit."""

        if not self.scheduled_start_checkbox.isChecked():
            self.scheduled_start_status.setText("Sofortstart")
            return

        selected = self.scheduled_start_edit.dateTime().toPython()
        remaining_seconds = int((selected - datetime.now()).total_seconds())

        if remaining_seconds <= 0:
            self.scheduled_start_status.setText("Zeit liegt in der Vergangenheit")
            return

        hours, remainder = divmod(remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours >= 24:
            days, hours = divmod(hours, 24)
            countdown = f"Start in {days} T " f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            countdown = f"Start in {hours:02d}:{minutes:02d}:{seconds:02d}"

        self.scheduled_start_status.setText(countdown)

    def _schedule_automation_start(self) -> None:
        """Plant die geladene Route zur ausgewählten Uhrzeit ein."""

        scheduled = self.scheduled_start_edit.dateTime().toPython()

        if scheduled <= datetime.now():
            QMessageBox.warning(
                self,
                "Ungültige Startzeit",
                "Die gewählte Startzeit muss in der Zukunft liegen.",
            )
            return

        self.scheduled_start_datetime = scheduled
        self.scheduled_start_active = True
        self.scheduled_start_timer.start()
        self._set_scheduled_waiting(True)
        self._update_scheduled_start_preview()

        self.log("--------------------------------")
        self.log(
            "Route wurde eingeplant für "
            f"{scheduled.strftime('%d.%m.%Y um %H:%M:%S')} Uhr."
        )
        self.log("CTSVision wartet auf die geplante Startzeit.")

    @Slot()
    def _check_scheduled_start(self) -> None:
        """Startet die Route, sobald die geplante Zeit erreicht ist."""

        if not self.scheduled_start_active:
            self.scheduled_start_timer.stop()
            return

        self._update_scheduled_start_preview()

        if self.scheduled_start_datetime is None:
            self._cancel_scheduled_start(
                "Geplanter Start wurde wegen eines internen Fehlers aufgehoben."
            )
            return

        if datetime.now() < self.scheduled_start_datetime:
            return

        self.scheduled_start_timer.stop()
        self.scheduled_start_active = False
        self.scheduled_start_status.setText("Start wird ausgeführt...")

        self.log("--------------------------------")
        self.log("Geplante Startzeit wurde erreicht.")
        self.log("Die Carrier-Automatik wird jetzt gestartet.")

        self._set_scheduled_waiting(False)
        self._start_automation_now()

    def _cancel_scheduled_start(
        self,
        log_message: str | None = None,
    ) -> None:
        """Hebt eine wartende Startplanung auf."""

        self.scheduled_start_timer.stop()
        self.scheduled_start_active = False
        self.scheduled_start_datetime = None
        self.scheduled_start_status.setText("Sofortstart")
        self._set_scheduled_waiting(False)

        if log_message:
            self.log(log_message)

    def _set_scheduled_waiting(self, waiting: bool) -> None:
        """Sperrt Änderungen, solange CTSVision auf die Startzeit wartet."""

        self.start_button.setEnabled(not waiting)
        self.stop_button.setEnabled(waiting)
        self.route_button.setEnabled(not waiting)
        self.restart_button.setEnabled(not waiting)
        self.resume_button.setEnabled(not waiting)
        self.vision_wizard_button.setEnabled(not waiting)
        self.tank_wizard_button.setEnabled(not waiting)
        self.tank_test_button.setEnabled(not waiting)
        self.auto_refuel_checkbox.setEnabled(not waiting)
        self.scheduled_start_checkbox.setEnabled(not waiting)
        self.scheduled_start_edit.setEnabled(
            not waiting and self.scheduled_start_checkbox.isChecked()
        )

        tank_controls_enabled = not waiting and self.auto_refuel_checkbox.isChecked()
        self.refuel_threshold_spinbox.setEnabled(tank_controls_enabled)
        self.tritium_position_spinbox.setEnabled(tank_controls_enabled)

        if waiting:
            self.start_button.setText("◷  Route eingeplant")
            self.stop_button.setText("■  Planung aufheben")
        else:
            self.start_button.setText("▶  Automatik starten")
            self.stop_button.setText("■  Stop")

    def start_automation(self) -> None:
        """Startet die Automatik sofort oder plant sie ein."""

        if self.scheduled_start_active:
            self.log("Die Route ist bereits eingeplant.")
            return

        if self.automation_thread is not None:
            self.log("Die Automatik läuft bereits.")
            return

        if self.tank_test_thread is not None:
            QMessageBox.information(
                self,
                "Tankprüfung läuft",
                (
                    "Während die Tankfunktion geprüft wird, "
                    "kann die Sprungautomatik nicht gestartet werden."
                ),
            )
            return

        if self.route_manager is None:
            QMessageBox.information(
                self,
                "Keine Route",
                "Bitte zuerst eine Route auswählen.",
            )
            return

        current_jump = self.route_manager.get_current_jump()

        if current_jump is None:
            QMessageBox.information(
                self,
                "Route abgeschlossen",
                "Für diese Route ist kein weiteres Sprungziel vorhanden.",
            )
            return

        if self.scheduled_start_checkbox.isChecked():
            self._schedule_automation_start()
            return

        self._start_automation_now()

    def _start_automation_now(self) -> None:
        """Startet den bestehenden Automatik-Worker unmittelbar."""

        if self.automation_thread is not None:
            self.log("Die Automatik läuft bereits.")
            return

        if self.route_manager is None:
            self.log("Automatik konnte nicht starten: Keine Route geladen.")
            return

        current_jump = self.route_manager.get_current_jump()

        if current_jump is None:
            self.log("Automatik konnte nicht starten: Route abgeschlossen.")
            return

        self.log("--------------------------------")
        self.log("Automatik-Testlauf wird gestartet.")
        self.log("Ziel aus RouteManager: " f"{current_jump.system}")
        self._set_automation_running(True)

        thread = QThread(self)
        worker = AutomationWorker(self.route_manager)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_message.connect(self.log)
        worker.tank_status_changed.connect(self.set_tank_status)
        worker.completed.connect(self.automation_completed)
        worker.failed.connect(self.automation_failed)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self.automation_thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.automation_thread = thread
        self.automation_worker = worker
        thread.start()

    # --------------------------------------------------

    def stop_automation(self) -> None:
        """
        Fordert das kontrollierte Stoppen der Automatik an.
        """

        if self.scheduled_start_active:
            self._cancel_scheduled_start(
                "Geplanter Start wurde vom Benutzer aufgehoben."
            )
            return

        if self.automation_worker is None:
            self.log("Die Automatik läuft derzeit nicht.")
            return

        self.log("Stop wird angefordert...")

        self.automation_worker.request_stop()

        self.stop_button.setEnabled(False)

    # --------------------------------------------------

    @Slot(str)
    def automation_completed(
        self,
        system_name: str,
    ) -> None:
        """
        Wird nach einem erfolgreichen Sprung aufgerufen.
        """

        self.log("Sprung erfolgreich abgeschlossen: " f"{system_name}")

        # Route-Anzeige nach dem abgeschlossenen Sprung aktualisieren.
        self.refresh_route_display()

        if self.route_manager is not None and self.route_manager.is_completed:
            self.start_next_jump = False

            self.log("Route vollständig abgeschlossen.")

            return

        self.start_next_jump = True

        self.log(
            "Nächstes Ziel wurde vorgemerkt und "
            "startet nach dem Aufräumen des "
            "aktuellen Testlaufs."
        )

    # --------------------------------------------------

    @Slot(str)
    def automation_failed(
        self,
        error_message: str,
    ) -> None:
        """
        Zeigt einen Fehler aus dem Worker an.
        """

        self.log("Fehler im Automatik-Test: " f"{error_message}")

        QMessageBox.critical(
            self,
            "Automatik-Fehler",
            error_message,
        )

    # --------------------------------------------------

    @Slot()
    def automation_thread_finished(self) -> None:
        """
        Räumt den Worker nach dem Testlauf auf.
        """

        self.automation_thread = None
        self.automation_worker = None

        self.log("Automatik-Testlauf wurde beendet.")

        if self.start_next_jump:
            self.start_next_jump = False

            self.log("Der nächste Sprung wird jetzt gestartet.")

            self.start_automation()
            return

        self._set_automation_running(False)

    # --------------------------------------------------

    def _set_automation_running(
        self,
        running: bool,
    ) -> None:
        """
        Aktiviert beziehungsweise deaktiviert die
        passenden Bedienelemente.
        """

        self.start_button.setEnabled(not running)

        self.stop_button.setEnabled(running)

        self.route_button.setEnabled(not running)

        self.restart_button.setEnabled(not running)
        self.resume_button.setEnabled(not running)

        self.vision_wizard_button.setEnabled(not running)
        self.tank_wizard_button.setEnabled(not running)
        self.tank_test_button.setEnabled(not running)

        self.auto_refuel_checkbox.setEnabled(not running)
        self.scheduled_start_checkbox.setEnabled(not running)
        self.scheduled_start_edit.setEnabled(
            not running and self.scheduled_start_checkbox.isChecked()
        )

        tank_controls_enabled = not running and self.auto_refuel_checkbox.isChecked()
        self.refuel_threshold_spinbox.setEnabled(tank_controls_enabled)
        self.tritium_position_spinbox.setEnabled(tank_controls_enabled)

        if running:
            self.start_button.setText("●  Automatik läuft...")
        else:
            self.start_button.setText("▶  Automatik starten")

    def on_journal_status(
        self,
        text: str,
    ) -> None:
        self.log(text)

    def on_journal_error(
        self,
        text: str,
    ) -> None:
        self.log(f"Journal: {text}")

    def on_journal_event(
        self,
        event: dict,
    ) -> None:

        timestamp = event.get(
            "timestamp",
            "",
        )

        name = event.get(
            "event",
            "",
        )

        self.log(f"[Journal] {timestamp}   {name}")

        if name == "CarrierJump" and self.automation_worker is not None:
            self.log("CarrierJump erkannt. " "Der AutomationWorker wird informiert.")

            self.automation_worker.on_carrier_jump()


def run_gui() -> None:
    app = QApplication.instance() or QApplication([])

    window = AutomationWindow()
    window.show()

    app.exec()


if __name__ == "__main__":
    run_gui()
