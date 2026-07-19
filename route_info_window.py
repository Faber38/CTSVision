from __future__ import annotations
from route_manager import RouteManager
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class RouteInfoWindow(QDialog):
    """
    Separates Fenster zur Anzeige der Routendaten.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("CTSVision - Routen-Informationen")
        self.resize(600, 520)

        self._build_ui()

    def _build_ui(self) -> None:

        main_layout = QVBoxLayout(self)

        # --------------------------------------------------
        # Allgemeine Routendaten
        # --------------------------------------------------

        route_box = QGroupBox("Route")
        main_layout.addWidget(route_box)

        route_layout = QGridLayout(route_box)

        self.lbl_file = QLabel("-")
        self.lbl_file.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.lbl_file.setWordWrap(True)

        self.lbl_start = QLabel("-")
        self.lbl_target = QLabel("-")
        self.lbl_jumps = QLabel("-")
        self.lbl_distance = QLabel("-")
        self.lbl_tritium = QLabel("-")
        self.lbl_duration = QLabel("-")

        route_layout.addWidget(QLabel("Routendatei:"), 0, 0)
        route_layout.addWidget(self.lbl_file, 0, 1)

        route_layout.addWidget(QLabel("Startsystem:"), 1, 0)
        route_layout.addWidget(self.lbl_start, 1, 1)

        route_layout.addWidget(QLabel("Zielsystem:"), 2, 0)
        route_layout.addWidget(self.lbl_target, 2, 1)

        route_layout.addWidget(QLabel("Sprünge gesamt:"), 3, 0)
        route_layout.addWidget(self.lbl_jumps, 3, 1)

        route_layout.addWidget(QLabel("Gesamtstrecke:"), 4, 0)
        route_layout.addWidget(self.lbl_distance, 4, 1)

        route_layout.addWidget(QLabel("Tritiumbedarf:"), 5, 0)
        route_layout.addWidget(self.lbl_tritium, 5, 1)
        route_layout.addWidget(
            QLabel("Geplante Reisedauer:"),
            6,
            0,
        )
        route_layout.addWidget(
            self.lbl_duration,
            6,
            1,
        )

        route_layout.setColumnStretch(1, 1)

        # --------------------------------------------------
        # Fortschritt
        # --------------------------------------------------

        progress_box = QGroupBox("Fortschritt")
        main_layout.addWidget(progress_box)

        progress_layout = QVBoxLayout(progress_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p %")

        progress_layout.addWidget(self.progress_bar)

        progress_grid = QGridLayout()
        progress_layout.addLayout(progress_grid)

        self.lbl_progress_jumps = QLabel("-")
        self.lbl_progress_distance = QLabel("-")
        self.lbl_progress_fuel = QLabel("-")
        self.lbl_remaining_jumps = QLabel("-")
        self.lbl_remaining_distance = QLabel("-")
        self.lbl_remaining_fuel = QLabel("-")
        self.lbl_remaining_duration = QLabel("-")
        self.lbl_arrival_time = QLabel("-")

        progress_grid.addWidget(
            QLabel("Sprünge abgeschlossen:"),
            0,
            0,
        )
        progress_grid.addWidget(
            self.lbl_progress_jumps,
            0,
            1,
        )

        progress_grid.addWidget(
            QLabel("Zurückgelegte Strecke:"),
            1,
            0,
        )
        progress_grid.addWidget(
            self.lbl_progress_distance,
            1,
            1,
        )

        progress_grid.addWidget(
            QLabel("Tritium verbraucht:"),
            2,
            0,
        )
        progress_grid.addWidget(
            self.lbl_progress_fuel,
            2,
            1,
        )

        progress_grid.addWidget(
            QLabel("Verbleibende Sprünge:"),
            3,
            0,
        )
        progress_grid.addWidget(
            self.lbl_remaining_jumps,
            3,
            1,
        )

        progress_grid.addWidget(
            QLabel("Reststrecke:"),
            4,
            0,
        )
        progress_grid.addWidget(
            self.lbl_remaining_distance,
            4,
            1,
        )

        progress_grid.addWidget(
            QLabel("Tritium verbleibend:"),
            5,
            0,
        )
        progress_grid.addWidget(
            self.lbl_remaining_fuel,
            5,
            1,
        )
        progress_grid.addWidget(
            QLabel("Voraussichtliche Restdauer:"),
            6,
            0,
        )
        progress_grid.addWidget(
            self.lbl_remaining_duration,
            6,
            1,
        )

        progress_grid.addWidget(
            QLabel("Voraussichtliche Ankunft:"),
            7,
            0,
        )
        progress_grid.addWidget(
            self.lbl_arrival_time,
            7,
            1,
        )

        progress_grid.setColumnStretch(1, 1)

        # --------------------------------------------------
        # Nächster Sprung
        # --------------------------------------------------

        next_box = QGroupBox("Nächster Sprung")
        main_layout.addWidget(next_box)

        next_layout = QGridLayout(next_box)

        self.lbl_current = QLabel("-")
        self.lbl_current.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.lbl_next_distance = QLabel("-")
        self.lbl_next_fuel = QLabel("-")
        self.lbl_fuel_left = QLabel("-")
        self.lbl_notes = QLabel("-")
        self.lbl_notes.setWordWrap(True)

        next_layout.addWidget(QLabel("Zielsystem:"), 0, 0)
        next_layout.addWidget(self.lbl_current, 0, 1)

        next_layout.addWidget(QLabel("Entfernung:"), 1, 0)
        next_layout.addWidget(self.lbl_next_distance, 1, 1)

        next_layout.addWidget(QLabel("Tritium:"), 2, 0)
        next_layout.addWidget(self.lbl_next_fuel, 2, 1)

        next_layout.addWidget(QLabel("Tank danach:"), 3, 0)
        next_layout.addWidget(self.lbl_fuel_left, 3, 1)

        next_layout.addWidget(QLabel("Hinweise:"), 4, 0)
        next_layout.addWidget(self.lbl_notes, 4, 1)

        next_layout.setColumnStretch(1, 1)

        # --------------------------------------------------
        # Status und Schließen
        # --------------------------------------------------

        self.lbl_status = QLabel("Keine Route geladen")
        main_layout.addWidget(self.lbl_status)

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.close)

        main_layout.addWidget(close_button)

    # --------------------------------------------------

    @staticmethod
    def _format_float(
        value: float | None,
        suffix: str = "",
    ) -> str:

        if value is None:
            return "-"

        text = f"{value:,.1f}"

        text = text.replace(",", "X")
        text = text.replace(".", ",")
        text = text.replace("X", ".")

        return f"{text}{suffix}"

    @staticmethod
    def _format_int(
        value: int | None,
        suffix: str = "",
    ) -> str:

        if value is None:
            return "-"

        text = f"{value:,}".replace(",", ".")

        return f"{text}{suffix}"

    @staticmethod
    def _format_duration(minutes: int | None) -> str:
        """
        Wandelt Minuten in eine gut lesbare Zeitangabe um.
        """

        if minutes is None:
            return "-"

        minutes = max(0, int(minutes))

        hours, remaining_minutes = divmod(minutes, 60)

        if hours == 0:
            return f"{remaining_minutes} Minuten"

        if remaining_minutes == 0:
            if hours == 1:
                return "1 Stunde"

            return f"{hours} Stunden"

        if hours == 1:
            return f"1 Stunde {remaining_minutes} Minuten"

        return f"{hours} Stunden " f"{remaining_minutes} Minuten"

    # --------------------------------------------------

    def clear_route(self) -> None:
        """
        Setzt das Fenster auf den Zustand ohne geladene Route.
        """

        self.lbl_file.setText("-")
        self.lbl_start.setText("-")
        self.lbl_target.setText("-")
        self.lbl_jumps.setText("-")
        self.lbl_distance.setText("-")
        self.lbl_tritium.setText("-")
        self.lbl_duration.setText("-")

        self.progress_bar.setValue(0)

        self.lbl_progress_jumps.setText("-")
        self.lbl_progress_distance.setText("-")
        self.lbl_progress_fuel.setText("-")
        self.lbl_remaining_jumps.setText("-")
        self.lbl_remaining_distance.setText("-")
        self.lbl_remaining_fuel.setText("-")
        self.lbl_remaining_duration.setText("-")
        self.lbl_arrival_time.setText("-")

        self.lbl_current.setText("-")
        self.lbl_next_distance.setText("-")
        self.lbl_next_fuel.setText("-")
        self.lbl_fuel_left.setText("-")
        self.lbl_notes.setText("-")

        self.lbl_status.setText("Keine Route geladen")

    # --------------------------------------------------

    def update_route(
        self,
        manager: RouteManager,
    ) -> None:
        """
        Übernimmt sämtliche Daten aus dem RouteManager.
        """

        info = manager.get_route_info()
        jump = manager.get_current_jump()

        self.lbl_file.setText(str(info["file"]))
        self.lbl_start.setText(str(info["start_system"]))
        self.lbl_target.setText(str(info["destination_system"]))

        self.lbl_jumps.setText(
            self._format_int(
                int(info["total_jumps"]),
            )
        )

        self.lbl_distance.setText(
            self._format_float(
                float(info["total_distance"]),
                " Lj",
            )
        )

        self.lbl_tritium.setText(
            self._format_int(
                int(info["total_fuel_required"]),
                " t",
            )
        )

        self.lbl_duration.setText(
            self._format_duration(int(info["total_duration_minutes"]))
        )
        progress_percent = float(info["progress_percent"])

        self.progress_bar.setValue(round(progress_percent))

        completed_jumps = int(info["completed_jumps"])
        total_jumps = int(info["total_jumps"])

        self.lbl_progress_jumps.setText(f"{completed_jumps} von {total_jumps}")

        self.lbl_progress_distance.setText(
            f"{self._format_float(float(info['completed_distance']), ' Lj')}"
            f" von "
            f"{self._format_float(float(info['total_distance']), ' Lj')}"
        )

        self.lbl_progress_fuel.setText(
            f"{self._format_int(int(info['completed_fuel']), ' t')}"
            f" von "
            f"{self._format_int(int(info['total_fuel_required']), ' t')}"
        )

        self.lbl_remaining_jumps.setText(
            self._format_int(
                int(info["remaining_jumps"]),
            )
        )

        self.lbl_remaining_distance.setText(
            self._format_float(
                float(info["remaining_distance"]),
                " Lj",
            )
        )

        self.lbl_remaining_fuel.setText(
            self._format_int(
                int(info["remaining_fuel"]),
                " t",
            )
        )

        self.lbl_remaining_duration.setText(
            self._format_duration(int(info["remaining_duration_minutes"]))
        )

        remaining_minutes = int(info["remaining_duration_minutes"])

        estimated_arrival = datetime.now() + timedelta(minutes=remaining_minutes)

        self.lbl_arrival_time.setText(
            estimated_arrival.strftime("%d.%m.%Y um %H:%M Uhr")
        )

        if jump is None:
            self.lbl_current.setText("Route abgeschlossen")
            self.lbl_next_distance.setText("-")
            self.lbl_next_fuel.setText("-")
            self.lbl_fuel_left.setText("-")
            self.lbl_notes.setText("-")

            self.lbl_status.setText("Die Route wurde vollständig abgeschlossen.")

            self.progress_bar.setValue(100)

            self.lbl_remaining_duration.setText("0 Minuten")
            self.lbl_arrival_time.setText("Route abgeschlossen")

            return

        self.lbl_current.setText(jump.system)

        self.lbl_next_distance.setText(
            self._format_float(
                jump.distance,
                " Lj",
            )
        )

        self.lbl_next_fuel.setText(
            self._format_int(
                jump.fuel_used,
                " t",
            )
        )

        self.lbl_fuel_left.setText(
            self._format_int(
                jump.fuel_left,
                " t",
            )
        )

        if jump.extra_notes:
            self.lbl_notes.setText("\n".join(jump.extra_notes))
        else:
            self.lbl_notes.setText("Keine zusätzlichen Hinweise")

        self.lbl_status.setText("Route erfolgreich geladen.")
