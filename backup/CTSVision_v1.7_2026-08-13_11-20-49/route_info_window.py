from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from route_manager import RouteManager


class RouteInfoWindow(QDialog):
    """Modernes Informationsfenster für die aktuell geladene Route."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("CTSVision - Routeninformationen")
        self.resize(860, 690)
        self.setMinimumSize(760, 620)

        self._build_ui()
        self._apply_style()

    # --------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # --------------------------------------------------
        # Kopfbereich
        # --------------------------------------------------

        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 13, 18, 13)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("CTSVision")
        title.setObjectName("headerTitle")

        subtitle = QLabel("Routeninformationen")
        subtitle.setObjectName("headerSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.lbl_header_status = QLabel("Keine Route")
        self.lbl_header_status.setObjectName("headerStatus")
        self.lbl_header_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.lbl_header_status)

        main_layout.addWidget(header)

        # --------------------------------------------------
        # Route / Start / Ziel als Karten
        # --------------------------------------------------

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.file_card, self.lbl_file = self._create_card(
            "ROUTENDATEI",
            "-",
            selectable=True,
            word_wrap=True,
        )
        self.start_card, self.lbl_start = self._create_card("STARTSYSTEM", "-")
        self.target_card, self.lbl_target = self._create_card("ZIELSYSTEM", "-")

        cards_layout.addWidget(self.file_card, 2)
        cards_layout.addWidget(self.start_card, 1)
        cards_layout.addWidget(self.target_card, 1)

        main_layout.addLayout(cards_layout)

        # --------------------------------------------------
        # Gesamtübersicht
        # --------------------------------------------------

        overview = QFrame()
        overview.setObjectName("panel")
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(16, 13, 16, 13)
        overview_layout.setSpacing(12)

        overview_title = QLabel("Routenübersicht")
        overview_title.setObjectName("sectionTitle")
        overview_layout.addWidget(overview_title)

        overview_grid = QGridLayout()
        overview_grid.setHorizontalSpacing(28)
        overview_grid.setVerticalSpacing(10)

        self.lbl_jumps = self._add_metric(overview_grid, 0, 0, "Sprünge gesamt")
        self.lbl_distance = self._add_metric(overview_grid, 0, 1, "Gesamtstrecke")
        self.lbl_tritium = self._add_metric(overview_grid, 0, 2, "Tritiumbedarf")
        self.lbl_duration = self._add_metric(overview_grid, 0, 3, "Geplante Dauer")

        overview_layout.addLayout(overview_grid)
        main_layout.addWidget(overview)

        # --------------------------------------------------
        # Fortschritt
        # --------------------------------------------------

        progress_panel = QFrame()
        progress_panel.setObjectName("panel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(16, 13, 16, 13)
        progress_layout.setSpacing(12)

        progress_header = QHBoxLayout()

        progress_title = QLabel("Fortschritt")
        progress_title.setObjectName("sectionTitle")
        progress_header.addWidget(progress_title)
        progress_header.addStretch()

        self.lbl_progress_percent = QLabel("0 %")
        self.lbl_progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self.lbl_progress_percent)

        progress_layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(16)
        progress_layout.addWidget(self.progress_bar)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        completed_frame = QFrame()
        completed_frame.setObjectName("subPanel")
        completed_layout = QGridLayout(completed_frame)
        completed_layout.setContentsMargins(14, 12, 14, 12)
        completed_layout.setHorizontalSpacing(16)
        completed_layout.setVerticalSpacing(8)

        completed_title = QLabel("Bereits abgeschlossen")
        completed_title.setObjectName("subSectionTitle")
        completed_layout.addWidget(completed_title, 0, 0, 1, 2)

        self.lbl_progress_jumps = self._add_detail_row(completed_layout, 1, "Sprünge")
        self.lbl_progress_distance = self._add_detail_row(
            completed_layout, 2, "Strecke"
        )
        self.lbl_progress_fuel = self._add_detail_row(completed_layout, 3, "Tritium")

        remaining_frame = QFrame()
        remaining_frame.setObjectName("subPanel")
        remaining_layout = QGridLayout(remaining_frame)
        remaining_layout.setContentsMargins(14, 12, 14, 12)
        remaining_layout.setHorizontalSpacing(16)
        remaining_layout.setVerticalSpacing(8)

        remaining_title = QLabel("Noch verbleibend")
        remaining_title.setObjectName("subSectionTitle")
        remaining_layout.addWidget(remaining_title, 0, 0, 1, 2)

        self.lbl_remaining_jumps = self._add_detail_row(remaining_layout, 1, "Sprünge")
        self.lbl_remaining_distance = self._add_detail_row(
            remaining_layout, 2, "Reststrecke"
        )
        self.lbl_remaining_fuel = self._add_detail_row(remaining_layout, 3, "Tritium")
        self.lbl_remaining_duration = self._add_detail_row(
            remaining_layout, 4, "Restdauer"
        )
        self.lbl_arrival_time = self._add_detail_row(remaining_layout, 5, "Ankunft")

        stats_layout.addWidget(completed_frame, 1)
        stats_layout.addWidget(remaining_frame, 1)
        progress_layout.addLayout(stats_layout)

        main_layout.addWidget(progress_panel)

        # --------------------------------------------------
        # Nächster Sprung
        # --------------------------------------------------

        next_panel = QFrame()
        next_panel.setObjectName("nextPanel")
        next_layout = QVBoxLayout(next_panel)
        next_layout.setContentsMargins(14, 11, 14, 11)
        next_layout.setSpacing(8)

        next_title = QLabel("Nächster Sprung")
        next_title.setObjectName("sectionTitle")
        next_layout.addWidget(next_title)

        self.lbl_current = QLabel("-")
        self.lbl_current.setObjectName("currentTarget")
        self.lbl_current.setWordWrap(True)
        self.lbl_current.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        next_layout.addWidget(self.lbl_current)

        next_metrics = QGridLayout()
        next_metrics.setHorizontalSpacing(18)
        next_metrics.setVerticalSpacing(8)

        self.lbl_next_distance = self._add_metric(next_metrics, 0, 0, "Entfernung")
        next_metrics.setColumnStretch(0, 1)

        next_layout.addLayout(next_metrics)

        notes_title = QLabel("Hinweise")
        notes_title.setObjectName("smallTitle")
        next_layout.addWidget(notes_title)

        self.lbl_notes = QLabel("-")
        self.lbl_notes.setObjectName("notesLabel")
        self.lbl_notes.setWordWrap(True)
        self.lbl_notes.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        next_layout.addWidget(self.lbl_notes)

        main_layout.addWidget(next_panel)

        # --------------------------------------------------
        # Fußbereich
        # --------------------------------------------------

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        self.lbl_status = QLabel("Keine Route geladen")
        self.lbl_status.setObjectName("footerStatus")
        footer_layout.addWidget(self.lbl_status)
        footer_layout.addStretch()

        close_button = QPushButton("Schließen")
        close_button.setObjectName("closeButton")
        close_button.setMinimumWidth(120)
        close_button.clicked.connect(self.close)
        footer_layout.addWidget(close_button)

        main_layout.addLayout(footer_layout)

    # --------------------------------------------------

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #f4f7fb;
                color: #1f2937;
                font-family: "Noto Sans", "DejaVu Sans", sans-serif;
                font-size: 9pt;
            }

            QFrame#headerFrame {
                background-color: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 10px;
            }

            QLabel#headerTitle {
                color: #183b56;
                font-size: 18pt;
                font-weight: 700;
            }

            QLabel#headerSubtitle {
                color: #60758a;
                font-size: 9pt;
            }

            QLabel#headerStatus {
                color: #2563a6;
                background-color: #eaf3ff;
                border: 1px solid #bdd5f2;
                border-radius: 13px;
                padding: 5px 11px;
                font-weight: 700;
            }

            QFrame#card,
            QFrame#panel,
            QFrame#nextPanel {
                background-color: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 9px;
            }

            QFrame#nextPanel {
                border: 1px solid #b7d0e8;
                background-color: #fbfdff;
            }

            QFrame#subPanel {
                background-color: #f8fafc;
                border: 1px solid #e1e8f0;
                border-radius: 7px;
            }

            QLabel#cardCaption,
            QLabel#metricCaption {
                color: #718096;
                font-size: 7.5pt;
                font-weight: 700;
            }

            QLabel#cardValue {
                color: #1f3f5b;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#metricValue {
                color: #173b57;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #173b57;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#subSectionTitle {
                color: #365a73;
                font-weight: 700;
                padding-bottom: 3px;
            }

            QLabel#detailCaption {
                color: #6b7f90;
            }

            QLabel#detailValue {
                color: #253b4d;
                font-weight: 700;
            }

            QLabel#progressPercent {
                color: #2563a6;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QProgressBar {
                background-color: #e4ebf2;
                border: none;
                border-radius: 8px;
            }

            QProgressBar::chunk {
                background-color: #2d79bd;
                border-radius: 8px;
            }

            QLabel#currentTarget {
                color: #123f63;
                background-color: #eaf4ff;
                border: 1px solid #c6def5;
                border-radius: 7px;
                padding: 6px 9px;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#smallTitle {
                color: #60758a;
                font-weight: 700;
                margin-top: 2px;
            }

            QLabel#notesLabel {
                color: #465d70;
                background-color: #f6f9fc;
                border: 1px solid #e0e7ef;
                border-radius: 6px;
                padding: 6px 9px;
            }

            QLabel#footerStatus {
                color: #2f6f4e;
                background-color: #eaf7ef;
                border: 1px solid #c8e5d2;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 700;
            }

            QPushButton#closeButton {
                color: #ffffff;
                background-color: #2d6ea3;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
            }

            QPushButton#closeButton:hover {
                background-color: #245d8b;
            }

            QPushButton#closeButton:pressed {
                background-color: #1d4e76;
            }
            """)

    # --------------------------------------------------

    @staticmethod
    def _create_card(
        caption: str,
        value: str,
        *,
        selectable: bool = False,
        word_wrap: bool = False,
    ) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        caption_label = QLabel(caption)
        caption_label.setObjectName("cardCaption")

        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        value_label.setWordWrap(word_wrap)

        if selectable:
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        layout.addStretch()

        return frame, value_label

    @staticmethod
    def _add_metric(
        layout: QGridLayout,
        row: int,
        column: int,
        caption: str,
    ) -> QLabel:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(2)

        caption_label = QLabel(caption.upper())
        caption_label.setObjectName("metricCaption")

        value_label = QLabel("-")
        value_label.setObjectName("metricValue")

        wrapper_layout.addWidget(caption_label)
        wrapper_layout.addWidget(value_label)

        layout.addWidget(wrapper, row, column)
        return value_label

    @staticmethod
    def _add_detail_row(
        layout: QGridLayout,
        row: int,
        caption: str,
    ) -> QLabel:
        caption_label = QLabel(f"{caption}:")
        caption_label.setObjectName("detailCaption")

        value_label = QLabel("-")
        value_label.setObjectName("detailValue")
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(caption_label, row, 0)
        layout.addWidget(value_label, row, 1)
        return value_label

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
        """Wandelt Minuten in eine gut lesbare Zeitangabe um."""

        if minutes is None:
            return "-"

        minutes = max(0, int(minutes))
        hours, remaining_minutes = divmod(minutes, 60)

        if hours == 0:
            return f"{remaining_minutes} Minuten"

        if remaining_minutes == 0:
            return "1 Stunde" if hours == 1 else f"{hours} Stunden"

        if hours == 1:
            return f"1 Stunde {remaining_minutes} Minuten"

        return f"{hours} Stunden {remaining_minutes} Minuten"

    @staticmethod
    def _file_display_name(value: object) -> str:
        try:
            return Path(str(value)).name or str(value)
        except (TypeError, ValueError):
            return str(value)

    # --------------------------------------------------

    def clear_route(self) -> None:
        """Setzt das Fenster auf den Zustand ohne geladene Route."""

        self.lbl_file.setText("-")
        self.lbl_file.setToolTip("")
        self.lbl_start.setText("-")
        self.lbl_target.setText("-")
        self.lbl_jumps.setText("-")
        self.lbl_distance.setText("-")
        self.lbl_tritium.setText("-")
        self.lbl_duration.setText("-")

        self.progress_bar.setValue(0)
        self.lbl_progress_percent.setText("0 %")

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
        self.lbl_notes.setText("Keine Hinweise verfügbar")

        self.lbl_status.setText("Keine Route geladen")
        self.lbl_header_status.setText("Keine Route")

    # --------------------------------------------------

    def update_route(self, manager: RouteManager) -> None:
        """Übernimmt sämtliche Daten aus dem RouteManager."""

        info = manager.get_route_info()
        jump = manager.get_current_jump()

        route_path = str(info["file"])
        self.lbl_file.setText(self._file_display_name(info["file"]))
        self.lbl_file.setToolTip(route_path)
        self.lbl_start.setText(str(info["start_system"]))
        self.lbl_target.setText(str(info["destination_system"]))

        self.lbl_jumps.setText(self._format_int(int(info["total_jumps"])))
        self.lbl_distance.setText(
            self._format_float(float(info["total_distance"]), " Lj")
        )
        self.lbl_tritium.setText(
            self._format_int(int(info["total_fuel_required"]), " t")
        )
        self.lbl_duration.setText(
            self._format_duration(int(info["total_duration_minutes"]))
        )

        progress_percent = float(info["progress_percent"])
        self.progress_bar.setValue(round(progress_percent))
        self.lbl_progress_percent.setText(f"{progress_percent:.1f} %")

        completed_jumps = int(info["completed_jumps"])
        total_jumps = int(info["total_jumps"])

        self.lbl_progress_jumps.setText(f"{completed_jumps} von {total_jumps}")
        self.lbl_progress_distance.setText(
            f"{self._format_float(float(info['completed_distance']), ' Lj')}"
            f" von {self._format_float(float(info['total_distance']), ' Lj')}"
        )
        self.lbl_progress_fuel.setText(
            f"{self._format_int(int(info['completed_fuel']), ' t')}"
            f" von {self._format_int(int(info['total_fuel_required']), ' t')}"
        )

        self.lbl_remaining_jumps.setText(self._format_int(int(info["remaining_jumps"])))
        self.lbl_remaining_distance.setText(
            self._format_float(float(info["remaining_distance"]), " Lj")
        )
        self.lbl_remaining_fuel.setText(
            self._format_int(int(info["remaining_fuel"]), " t")
        )
        self.lbl_remaining_duration.setText(
            self._format_duration(int(info["remaining_duration_minutes"]))
        )

        remaining_minutes = int(info["remaining_duration_minutes"])
        estimated_arrival = datetime.now() + timedelta(minutes=remaining_minutes)
        self.lbl_arrival_time.setText(
            estimated_arrival.strftime("%d.%m.%Y · %H:%M Uhr")
        )

        if jump is None:
            self.lbl_current.setText("Route abgeschlossen")
            self.lbl_next_distance.setText("-")
            self.lbl_notes.setText("Alle geplanten Sprünge wurden abgeschlossen.")

            self.lbl_status.setText("Route vollständig abgeschlossen")
            self.lbl_header_status.setText("Abgeschlossen")

            self.progress_bar.setValue(100)
            self.lbl_progress_percent.setText("100,0 %")
            self.lbl_remaining_duration.setText("0 Minuten")
            self.lbl_arrival_time.setText("Route abgeschlossen")
            return

        self.lbl_current.setText(jump.system)
        self.lbl_next_distance.setText(self._format_float(jump.distance, " Lj"))

        if jump.extra_notes:
            self.lbl_notes.setText("\n".join(f"• {note}" for note in jump.extra_notes))
        else:
            self.lbl_notes.setText("Keine zusätzlichen Hinweise")

        self.lbl_status.setText("Route erfolgreich geladen")
        self.lbl_header_status.setText("Aktiv")
