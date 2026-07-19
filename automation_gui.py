from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
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

            self.log_message.emit(
                "Abkühlzeit läuft: 4 Minuten " "bis zum nächsten Sprung."
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

                    self.log_message.emit(
                        f"Abkühlzeit: " f"{minutes:02d}:{seconds:02d}"
                    )

                time.sleep(1)

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

        self.automation_thread: QThread | None = None
        self.automation_worker: AutomationWorker | None = None

        self.start_next_jump = False
        self.settings = load_settings()

        self.setWindowTitle("CTSVision - Carrier Automation | " "CMDR Faber38")

        self.resize(
            800,
            600,
        )

        self._build_ui()

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

        # --------------------------------------------------
        # Route
        # --------------------------------------------------

        route_box = QGroupBox("Route")
        layout.addWidget(route_box)

        route_layout = QGridLayout(route_box)

        self.route_edit = QLineEdit()
        self.route_edit.setReadOnly(True)

        self.route_button = QPushButton("Route auswählen...")

        self.route_button.clicked.connect(self.select_route)

        self.route_info_button = QPushButton("Routen-Info")

        self.route_info_button.clicked.connect(self.open_route_info)

        route_layout.addWidget(
            QLabel("Datei:"),
            0,
            0,
        )

        route_layout.addWidget(
            self.route_edit,
            0,
            1,
        )

        route_layout.addWidget(
            self.route_button,
            0,
            2,
        )

        route_layout.addWidget(
            self.route_info_button,
            0,
            3,
        )

        # --------------------------------------------------
        # Journal
        # --------------------------------------------------

        self.journal_directory_edit = QLineEdit()
        self.journal_directory_edit.setReadOnly(True)

        self.journal_button = QPushButton("Journalordner...")

        self.journal_button.clicked.connect(self.select_journal_directory)

        route_layout.addWidget(
            QLabel("Journalordner:"),
            1,
            0,
        )

        route_layout.addWidget(
            self.journal_directory_edit,
            1,
            1,
            1,
            2,
        )

        route_layout.addWidget(
            self.journal_button,
            1,
            3,
        )

        # --------------------------------------------------
        # Informationen
        # --------------------------------------------------

        info_box = QGroupBox("Informationen")
        layout.addWidget(info_box)

        info_layout = QGridLayout(info_box)

        self.total_label = QLabel("-")
        self.progress_label = QLabel("-")
        self.target_label = QLabel("-")

        info_layout.addWidget(
            QLabel("Anzahl Ziele:"),
            0,
            0,
        )

        info_layout.addWidget(
            self.total_label,
            0,
            1,
        )

        info_layout.addWidget(
            QLabel("Fortschritt:"),
            1,
            0,
        )

        info_layout.addWidget(
            self.progress_label,
            1,
            1,
        )

        info_layout.addWidget(
            QLabel("Aktuelles Ziel:"),
            2,
            0,
        )

        info_layout.addWidget(
            self.target_label,
            2,
            1,
        )

        # --------------------------------------------------
        # Buttons
        # --------------------------------------------------

        button_layout = QHBoxLayout()

        self.restart_button = QPushButton("Route neu starten")

        self.restart_button.clicked.connect(self.restart_route)

        self.resume_button = QPushButton("Route fortsetzen")

        self.resume_button.clicked.connect(self.refresh_route_display)

        self.vision_wizard_button = QPushButton("Vision Wizard")

        self.vision_wizard_button.clicked.connect(self.open_vision_wizard)

        self.start_button = QPushButton("Automatik starten")

        self.start_button.clicked.connect(self.start_automation)

        self.stop_button = QPushButton("Stop")

        self.stop_button.clicked.connect(self.stop_automation)

        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.restart_button)

        button_layout.addWidget(self.resume_button)

        button_layout.addWidget(self.vision_wizard_button)

        button_layout.addStretch()

        button_layout.addWidget(self.start_button)

        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        status_box = QGroupBox("Status")
        layout.addWidget(status_box)

        status_layout = QVBoxLayout(status_box)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)

        status_layout.addWidget(self.status_log)

        self.log("CTSVision Carrier Automation gestartet.")

        self.journal = JournalMonitor()

        self.journal.event_received.connect(self.on_journal_event)

        self.journal.status_changed.connect(self.on_journal_status)

        self.journal.error_occurred.connect(self.on_journal_error)

        self.journal.start()

    # --------------------------------------------------

    def log(
        self,
        text: str,
    ) -> None:
        self.status_log.append(text)

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

    def start_automation(self) -> None:
        """
        Startet den ersten vollständigen GUI-Testlauf.

        Der Ablauf endet nach der Eingabe des Systemnamens
        und dem Drücken von ENTER.
        """

        if self.automation_thread is not None:
            self.log("Die Automatik läuft bereits.")
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
                ("Für diese Route ist kein " "weiteres Sprungziel vorhanden."),
            )
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

        self.vision_wizard_button.setEnabled(not running)

        if running:
            self.start_button.setText("Automatik läuft...")
        else:
            self.start_button.setText("Automatik starten")

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
