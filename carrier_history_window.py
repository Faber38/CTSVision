from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app_paths import CARRIER_HISTORY_FILE


class JumpDetailDialog(QDialog):
    """Zeigt alle gespeicherten Rohdaten eines einzelnen Carrier-Sprungs."""

    FIELD_LABELS = [
        ("Zeit", "Zeitpunkt"),
        ("Route", "Routendatei"),
        ("Sprung", "Sprung Nr."),
        ("Von System", "Von-System"),
        ("Nach System", "Nach-System"),
        ("Distanz Lj", "Distanz"),
        ("Verbrauch geplant t", "Verbrauch geplant"),
        ("Used Capacity vor Sprung t", "Used Capacity vor Sprung"),
        ("Capacity Maximum t", "Capacity Maximum"),
        ("Tank vor Sprung t", "Tank vor Sprung"),
        ("Tank nach Sprung t", "Tank nach Sprung"),
        ("Tank Maximum t", "Tank Maximum"),
        ("Verbrauch IST t", "Verbrauch IST"),
        ("Abweichung t", "Abweichung"),
        ("Nachgetankt nach Sprung", "Nachgetankt nach Sprung"),
        ("Ermitteltes Nachtanken vor Sprung t", "Ermitteltes Nachtanken vor Sprung"),
        ("Tank OCR Messungen", "Tank OCR-Messungen"),
    ]

    def __init__(
        self,
        row: dict[str, str],
        parent=None,
        dark_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self.row = row
        self.dark_mode = bool(dark_mode)

        self.setWindowTitle("CTSVision - Sprungdetails")
        self.resize(650, 620)
        self.setMinimumSize(580, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("detailHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Sprungdetails")
        title.setObjectName("detailTitle")
        header_layout.addWidget(title)

        route_text = (
            f"{row.get('Von System', '-') or '-'}  →  "
            f"{row.get('Nach System', '-') or '-'}"
        )
        route_label = QLabel(route_text)
        route_label.setObjectName("detailRoute")
        route_label.setWordWrap(True)
        header_layout.addWidget(route_label)

        layout.addWidget(header)

        panel = QFrame()
        panel.setObjectName("detailPanel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(9)

        for index, (key, caption) in enumerate(self.FIELD_LABELS):
            caption_label = QLabel(caption)
            caption_label.setObjectName("detailCaption")

            value = str(row.get(key, "")).strip() or "—"

            if key == "Distanz Lj" and value != "—":
                value = f"{value.replace('.', ',')} Lj"
            elif key.endswith(" t") and value != "—":
                value = f"{value} t"

            value_label = QLabel(value)
            value_label.setObjectName("detailValue")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            grid.addWidget(caption_label, index, 0)
            grid.addWidget(value_label, index, 1)

        grid.setColumnStretch(1, 1)
        layout.addWidget(panel, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Schließen")
        close_button.setObjectName("detailCloseButton")
        close_button.setMinimumWidth(120)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        self._apply_style()

    def _apply_style(self) -> None:
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #151a20; color: #d7dee7;
                    font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 9pt; }
                QFrame#detailHeader, QFrame#detailPanel {
                    background-color: #1d232a; border: 1px solid #3b4652; border-radius: 9px; }
                QLabel#detailTitle { color: #8ec7ef; font-size: 15pt; font-weight: 700; }
                QLabel#detailRoute { color: #9bcaf0; font-size: 10.5pt; font-weight: 700; }
                QLabel#detailCaption { color: #8494a4; font-weight: 700; }
                QLabel#detailValue { color: #d7dee7; }
                QPushButton#detailCloseButton {
                    color: white; background-color: #256f9f; border: 1px solid #3985b7;
                    border-radius: 6px; padding: 8px 18px; font-weight: 700; }
                QPushButton#detailCloseButton:hover { background-color: #3184b8; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #f4f7fb; color: #1f2937;
                    font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 9pt; }
                QFrame#detailHeader, QFrame#detailPanel {
                    background-color: white; border: 1px solid #d7e0ea; border-radius: 9px; }
                QLabel#detailTitle { color: #183b56; font-size: 15pt; font-weight: 700; }
                QLabel#detailRoute { color: #315f86; font-size: 10.5pt; font-weight: 700; }
                QLabel#detailCaption { color: #718096; font-weight: 700; }
                QLabel#detailValue { color: #263746; }
                QPushButton#detailCloseButton {
                    color: white; background-color: #2d6ea3; border: none;
                    border-radius: 6px; padding: 8px 18px; font-weight: 700; }
                QPushButton#detailCloseButton:hover { background-color: #245d8b; }
            """)


class CarrierHistoryWindow(QDialog):
    """Zeigt die dauerhaft gespeicherte Carrier-/Tritium-Historie."""

    def __init__(self, parent=None, dark_mode: bool = False) -> None:
        super().__init__(parent)

        self.dark_mode = bool(dark_mode)
        self.history_file = Path(CARRIER_HISTORY_FILE)

        self.setWindowTitle("CTSVision - Carrier-Historie")
        self.resize(1180, 760)
        self.setMinimumSize(980, 650)

        self._build_ui()
        self._apply_style()
        self.refresh()

    # --------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 13, 18, 13)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("CTSVision")
        title.setObjectName("headerTitle")

        subtitle = QLabel("Carrier- und Tritium-Historie")
        subtitle.setObjectName("headerSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.lbl_header_status = QLabel("Keine Daten")
        self.lbl_header_status.setObjectName("headerStatus")
        self.lbl_header_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.lbl_header_status)

        main_layout.addWidget(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_jumps, self.lbl_jumps = self._create_card("SPRÜNGE", "-")
        self.card_distance, self.lbl_distance = self._create_card("STRECKE", "-")
        self.card_tritium, self.lbl_tritium = self._create_card("IST-TRITIUM", "-")
        self.card_capacity, self.lbl_capacity = self._create_card("LETZTE CAPACITY", "-")

        cards_layout.addWidget(self.card_jumps, 1)
        cards_layout.addWidget(self.card_distance, 1)
        cards_layout.addWidget(self.card_tritium, 1)
        cards_layout.addWidget(self.card_capacity, 1)

        main_layout.addLayout(cards_layout)

        overview = QFrame()
        overview.setObjectName("panel")
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(16, 13, 16, 13)
        overview_layout.setSpacing(12)

        overview_title = QLabel("Verbrauchsübersicht")
        overview_title.setObjectName("sectionTitle")
        overview_layout.addWidget(overview_title)

        overview_grid = QGridLayout()
        overview_grid.setHorizontalSpacing(28)
        overview_grid.setVerticalSpacing(10)

        self.lbl_avg_distance = self._add_metric(
            overview_grid, 0, 0, "Ø Sprungweite"
        )
        self.lbl_avg_actual = self._add_metric(
            overview_grid, 0, 1, "Ø IST-Verbrauch"
        )
        self.lbl_avg_planned = self._add_metric(
            overview_grid, 0, 2, "Ø Prognose"
        )
        self.lbl_avg_deviation = self._add_metric(
            overview_grid, 0, 3, "Ø Abweichung"
        )
        self.lbl_refuels = self._add_metric(
            overview_grid, 0, 4, "Nachtankvorgänge"
        )

        overview_layout.addLayout(overview_grid)
        main_layout.addWidget(overview)

        table_panel = QFrame()
        table_panel.setObjectName("panel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(16, 13, 16, 13)
        table_layout.setSpacing(10)

        table_title = QLabel("Sprunghistorie")
        table_title.setObjectName("sectionTitle")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 10)
        self.table.setObjectName("historyTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Datum / Zeit",
                "Von",
                "Nach",
                "Distanz",
                "Capacity",
                "Tank vor",
                "Tank nach",
                "IST",
                "Plan",
                "Abw.",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.cellClicked.connect(self._open_jump_details)
        self._display_rows: list[dict[str, str]] = []
        self.table.verticalHeader().setVisible(False)

        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        table_layout.addWidget(self.table, 1)
        main_layout.addWidget(table_panel, 1)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)

        self.lbl_status = QLabel("Noch keine Historie vorhanden")
        self.lbl_status.setObjectName("footerStatus")
        self.lbl_status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        footer_layout.addWidget(self.lbl_status, 1)

        backup_button = QPushButton("Backup")
        backup_button.setObjectName("secondaryButton")
        backup_button.setToolTip(
            "Sichert die komplette Carrier-Historie als CSV-Datei."
        )
        backup_button.clicked.connect(self.backup_history)
        footer_layout.addWidget(backup_button)

        restore_button = QPushButton("Wiederherstellen")
        restore_button.setObjectName("secondaryButton")
        restore_button.setToolTip(
            "Stellt eine zuvor gesicherte Carrier-Historie wieder her."
        )
        restore_button.clicked.connect(self.restore_history)
        footer_layout.addWidget(restore_button)

        export_button = QPushButton("Excel-Export")
        export_button.setObjectName("secondaryButton")
        export_button.setToolTip(
            "Exportiert die komplette Carrier-Historie als Excel-Datei (.xlsx)."
        )
        export_button.clicked.connect(self.export_excel)
        footer_layout.addWidget(export_button)

        delete_button = QPushButton("Historie löschen")
        delete_button.setObjectName("dangerButton")
        delete_button.setToolTip(
            "Löscht die komplette Carrier-Historie nach doppelter Sicherheitsabfrage."
        )
        delete_button.clicked.connect(self.delete_history)
        footer_layout.addWidget(delete_button)

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(self.refresh)
        footer_layout.addWidget(refresh_button)

        close_button = QPushButton("Schließen")
        close_button.setObjectName("closeButton")
        close_button.setMinimumWidth(120)
        close_button.clicked.connect(self.close)
        footer_layout.addWidget(close_button)

        main_layout.addLayout(footer_layout)

    # --------------------------------------------------

    @staticmethod
    def _create_card(caption: str, value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        caption_label = QLabel(caption)
        caption_label.setObjectName("cardCaption")

        value_label = QLabel(value)
        value_label.setObjectName("cardValue")

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
        wrapper = QFrame()
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

    # --------------------------------------------------

    @staticmethod
    def _to_float(value: str) -> float | None:
        raw = str(value).strip()

        if not raw:
            return None

        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _to_int(value: str) -> int | None:
        number = CarrierHistoryWindow._to_float(value)

        if number is None:
            return None

        return int(round(number))

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

        return f"{value:,}".replace(",", ".") + suffix

    @staticmethod
    def _format_timestamp(value: str) -> str:
        raw = str(value).strip()

        if not raw:
            return "-"

        try:
            parsed = datetime.fromisoformat(raw)
            return parsed.strftime("%d.%m.%Y %H:%M:%S")
        except ValueError:
            return raw

    @staticmethod
    def _format_table_number(
        value: str,
        *,
        decimals: int = 0,
        suffix: str = "",
        signed: bool = False,
    ) -> str:
        number = CarrierHistoryWindow._to_float(value)

        if number is None:
            return "-"

        if decimals == 0:
            if signed:
                text = f"{int(round(number)):+d}"
            else:
                text = f"{int(round(number))}"
        else:
            text = f"{number:.{decimals}f}".replace(".", ",")

        return f"{text}{suffix}"

    # --------------------------------------------------

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.history_file.exists():
            return []

        with self.history_file.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            return list(csv.DictReader(handle, delimiter=";"))

    def refresh(self) -> None:
        """Liest die CSV neu ein und aktualisiert Kennzahlen und Tabelle."""

        try:
            rows = self._read_rows()
        except Exception as exc:
            self._clear()
            self.lbl_status.setText(
                f"Carrier-Historie konnte nicht gelesen werden: {exc}"
            )
            self.lbl_header_status.setText("Fehler")
            return

        if not rows:
            self._clear()
            self.lbl_status.setText(
                f"Noch keine Messdaten vorhanden · {self.history_file}"
            )
            return

        distances = [
            value
            for row in rows
            if (value := self._to_float(row.get("Distanz Lj", ""))) is not None
        ]
        actual_values = [
            value
            for row in rows
            if (value := self._to_int(row.get("Verbrauch IST t", ""))) is not None
        ]
        planned_values = [
            value
            for row in rows
            if (value := self._to_int(row.get("Verbrauch geplant t", ""))) is not None
        ]
        deviations = [
            value
            for row in rows
            if (value := self._to_int(row.get("Abweichung t", ""))) is not None
        ]

        refuel_count = sum(
            1
            for row in rows
            if str(row.get("Nachgetankt nach Sprung", "")).strip().lower()
            == "ja"
        )

        last_capacity = self._to_int(
            rows[-1].get("Used Capacity vor Sprung t", "")
        )

        self.lbl_jumps.setText(self._format_int(len(rows)))
        self.lbl_distance.setText(
            self._format_float(sum(distances) if distances else None, " Lj")
        )
        self.lbl_tritium.setText(
            self._format_int(sum(actual_values) if actual_values else None, " t")
        )
        self.lbl_capacity.setText(
            self._format_int(last_capacity, " t")
        )

        self.lbl_avg_distance.setText(
            self._format_float(
                sum(distances) / len(distances) if distances else None,
                " Lj",
            )
        )
        self.lbl_avg_actual.setText(
            self._format_float(
                sum(actual_values) / len(actual_values)
                if actual_values
                else None,
                " t",
            )
        )
        self.lbl_avg_planned.setText(
            self._format_float(
                sum(planned_values) / len(planned_values)
                if planned_values
                else None,
                " t",
            )
        )
        self.lbl_avg_deviation.setText(
            self._format_float(
                sum(deviations) / len(deviations)
                if deviations
                else None,
                " t",
            )
        )
        self.lbl_refuels.setText(self._format_int(refuel_count))

        self._display_rows = list(reversed(rows))
        self.table.setRowCount(len(self._display_rows))

        for table_row, row in enumerate(self._display_rows):
            values = [
                self._format_timestamp(row.get("Zeit", "")),
                row.get("Von System", "") or "-",
                row.get("Nach System", "") or "-",
                self._format_table_number(
                    row.get("Distanz Lj", ""),
                    decimals=1,
                    suffix=" Lj",
                ),
                self._format_table_number(
                    row.get("Used Capacity vor Sprung t", ""),
                    suffix=" t",
                ),
                self._format_table_number(
                    row.get("Tank vor Sprung t", ""),
                    suffix=" t",
                ),
                self._format_table_number(
                    row.get("Tank nach Sprung t", ""),
                    suffix=" t",
                ),
                self._format_table_number(
                    row.get("Verbrauch IST t", ""),
                    suffix=" t",
                ),
                self._format_table_number(
                    row.get("Verbrauch geplant t", ""),
                    suffix=" t",
                ),
                self._format_table_number(
                    row.get("Abweichung t", ""),
                    suffix=" t",
                    signed=True,
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column >= 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self.table.setItem(table_row, column, item)

        self.lbl_header_status.setText(f"{len(rows)} Sprünge")
        self.lbl_status.setText(
            f"Historie geladen · {self.history_file}"
        )

    def _open_jump_details(self, row_index: int, column_index: int) -> None:
        """Öffnet beim Anklicken einer Tabellenzeile die vollständigen Sprungdaten."""

        if row_index < 0 or row_index >= len(self._display_rows):
            return

        dialog = JumpDetailDialog(
            self._display_rows[row_index],
            parent=self,
            dark_mode=self.dark_mode,
        )
        dialog.exec()

    def _clear(self) -> None:
        self.lbl_jumps.setText("-")
        self.lbl_distance.setText("-")
        self.lbl_tritium.setText("-")
        self.lbl_capacity.setText("-")
        self.lbl_avg_distance.setText("-")
        self.lbl_avg_actual.setText("-")
        self.lbl_avg_planned.setText("-")
        self.lbl_avg_deviation.setText("-")
        self.lbl_refuels.setText("-")
        self.table.setRowCount(0)
        self._display_rows = []
        self.lbl_header_status.setText("Keine Daten")

    # --------------------------------------------------

    def backup_history(self) -> None:
        """Sichert die komplette Historie als CSV-Datei."""

        if not self.history_file.exists():
            QMessageBox.information(
                self,
                "Keine Historie",
                "Es sind noch keine Carrier-Historiedaten vorhanden.",
            )
            return

        suggested = (
            Path.home()
            / f"CTSVision_Carrier_History_Backup_"
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Carrier-Historie sichern",
            str(suggested),
            "CSV-Datei (*.csv)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".csv":
            target = target.with_suffix(".csv")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.history_file, target)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Backup fehlgeschlagen",
                f"Die Carrier-Historie konnte nicht gesichert werden.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Backup erstellt",
            f"Die Carrier-Historie wurde erfolgreich gesichert:\n\n{target}",
        )

    def restore_history(self) -> None:
        """Stellt eine zuvor gesicherte Carrier-Historie wieder her."""

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Carrier-Historie wiederherstellen",
            str(Path.home()),
            "CSV-Datei (*.csv)",
        )

        if not filename:
            return

        source = Path(filename)

        try:
            with source.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=";")
                fieldnames = reader.fieldnames or []
                rows = list(reader)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Wiederherstellung fehlgeschlagen",
                f"Die ausgewählte Datei konnte nicht gelesen werden.\n\n{exc}",
            )
            return

        required = {
            "Zeit",
            "Von System",
            "Nach System",
            "Distanz Lj",
            "Verbrauch IST t",
        }

        if not required.issubset(set(fieldnames)):
            QMessageBox.warning(
                self,
                "Ungültiges Backup",
                (
                    "Die ausgewählte CSV-Datei ist keine gültige "
                    "CTSVision Carrier-Historie."
                ),
            )
            return

        answer = QMessageBox.question(
            self,
            "Historie wiederherstellen",
            (
                "Die aktuelle Carrier-Historie wird durch das Backup ersetzt.\n\n"
                f"Backup enthält {len(rows)} Sprungdatensätze.\n\n"
                "Fortfahren?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # Vor dem Überschreiben automatisch eine Sicherheitskopie
            # der aktuell vorhandenen Historie erzeugen.
            if self.history_file.exists():
                safety_backup = self.history_file.with_name(
                    "carrier_history_before_restore_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                shutil.copy2(self.history_file, safety_backup)

            shutil.copy2(source, self.history_file)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Wiederherstellung fehlgeschlagen",
                f"Die Historie konnte nicht wiederhergestellt werden.\n\n{exc}",
            )
            return

        self.refresh()

        QMessageBox.information(
            self,
            "Historie wiederhergestellt",
            "Die Carrier-Historie wurde erfolgreich wiederhergestellt.",
        )

    def export_excel(self) -> None:
        """Exportiert die Historie als formatierte Excel-Datei (.xlsx)."""

        try:
            rows = self._read_rows()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Excel-Export fehlgeschlagen",
                f"Die Carrier-Historie konnte nicht gelesen werden.\n\n{exc}",
            )
            return

        if not rows:
            QMessageBox.information(
                self,
                "Keine Historie",
                "Es sind noch keine Carrier-Historiedaten vorhanden.",
            )
            return

        try:
            import xlsxwriter
        except ImportError:
            QMessageBox.critical(
                self,
                "Excel-Export nicht verfügbar",
                (
                    "Für den Excel-Export fehlt das Python-Paket 'xlsxwriter'.\n\n"
                    "Installiere es in der CTSVision-Umgebung mit:\n"
                    "pip install XlsxWriter"
                ),
            )
            return

        suggested = (
            Path.home()
            / f"CTSVision_Carrier_History_"
            f"{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Carrier-Historie als Excel exportieren",
            str(suggested),
            "Excel-Datei (*.xlsx)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".xlsx":
            target = target.with_suffix(".xlsx")

        try:
            workbook = xlsxwriter.Workbook(str(target))
            worksheet = workbook.add_worksheet("Carrier-Historie")

            header_format = workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#D9EAF7",
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                }
            )
            text_format = workbook.add_format({"border": 1})
            number_format = workbook.add_format(
                {"border": 1, "num_format": "0"}
            )
            decimal_format = workbook.add_format(
                {"border": 1, "num_format": "0.0"}
            )
            date_format = workbook.add_format(
                {"border": 1, "num_format": "dd.mm.yyyy hh:mm:ss"}
            )

            headers = list(rows[0].keys())

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            numeric_int_headers = {
                "Sprung",
                "Verbrauch geplant t",
                "Used Capacity vor Sprung t",
                "Capacity Maximum t",
                "Tank vor Sprung t",
                "Tank nach Sprung t",
                "Tank Maximum t",
                "Verbrauch IST t",
                "Abweichung t",
                "Ermitteltes Nachtanken vor Sprung t",
                "Tank OCR Messungen",
            }

            for row_index, row in enumerate(rows, start=1):
                for col, header in enumerate(headers):
                    value = str(row.get(header, "")).strip()

                    if header == "Zeit" and value:
                        try:
                            parsed = datetime.fromisoformat(value)
                            worksheet.write_datetime(
                                row_index,
                                col,
                                parsed.replace(tzinfo=None),
                                date_format,
                            )
                            continue
                        except ValueError:
                            pass

                    if header == "Distanz Lj" and value:
                        try:
                            worksheet.write_number(
                                row_index,
                                col,
                                float(value.replace(",", ".")),
                                decimal_format,
                            )
                            continue
                        except ValueError:
                            pass

                    if header in numeric_int_headers and value:
                        try:
                            worksheet.write_number(
                                row_index,
                                col,
                                int(round(float(value.replace(",", ".")))),
                                number_format,
                            )
                            continue
                        except ValueError:
                            pass

                    worksheet.write(row_index, col, value, text_format)

            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(
                0,
                0,
                len(rows),
                max(0, len(headers) - 1),
            )

            widths = {
                "Zeit": 20,
                "Route": 44,
                "Sprung": 9,
                "Von System": 28,
                "Nach System": 28,
                "Distanz Lj": 13,
                "Verbrauch geplant t": 18,
                "Used Capacity vor Sprung t": 24,
                "Capacity Maximum t": 20,
                "Tank vor Sprung t": 18,
                "Tank nach Sprung t": 18,
                "Tank Maximum t": 17,
                "Verbrauch IST t": 16,
                "Abweichung t": 14,
                "Nachgetankt nach Sprung": 23,
                "Ermitteltes Nachtanken vor Sprung t": 31,
                "Tank OCR Messungen": 19,
            }

            for col, header in enumerate(headers):
                worksheet.set_column(col, col, widths.get(header, 18))

            workbook.close()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Excel-Export fehlgeschlagen",
                f"Die Excel-Datei konnte nicht erstellt werden.\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Excel-Export abgeschlossen",
            f"Die Carrier-Historie wurde exportiert:\n\n{target}",
        )

    def delete_history(self) -> None:
        """Löscht die komplette Historie nach zwei Sicherheitsabfragen."""

        if not self.history_file.exists():
            QMessageBox.information(
                self,
                "Keine Historie",
                "Es sind keine Carrier-Historiedaten vorhanden.",
            )
            return

        first = QMessageBox.question(
            self,
            "Carrier-Historie löschen",
            (
                "Soll die komplette Carrier-Historie gelöscht werden?\n\n"
                "Alle gespeicherten Sprung- und Verbrauchsdaten wären betroffen."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if first != QMessageBox.StandardButton.Yes:
            return

        second = QMessageBox.warning(
            self,
            "Wirklich löschen?",
            (
                "WIRKLICH alle Carrier-Historiedaten endgültig löschen?\n\n"
                "Dieser Vorgang kann nicht rückgängig gemacht werden, "
                "wenn vorher kein Backup erstellt wurde."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if second != QMessageBox.StandardButton.Yes:
            return

        try:
            self.history_file.unlink()
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Löschen fehlgeschlagen",
                f"Die Carrier-Historie konnte nicht gelöscht werden.\n\n{exc}",
            )
            return

        self.refresh()

        QMessageBox.information(
            self,
            "Historie gelöscht",
            "Die Carrier-Historie wurde vollständig gelöscht.",
        )

    def set_dark_mode(self, enabled: bool) -> None:
        enabled = bool(enabled)

        if self.dark_mode == enabled:
            return

        self.dark_mode = enabled
        self._apply_style()

    def _apply_style(self) -> None:
        if self.dark_mode:
            self._apply_dark_style()
        else:
            self._apply_light_style()

    def _apply_dark_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #151a20;
                color: #d7dee7;
                font-family: "Noto Sans", "DejaVu Sans", sans-serif;
                font-size: 9pt;
            }

            QFrame#headerFrame,
            QFrame#card,
            QFrame#panel {
                background-color: #1d232a;
                border: 1px solid #3b4652;
                border-radius: 9px;
            }

            QLabel#headerTitle {
                color: #76b9ea;
                font-size: 18pt;
                font-weight: 700;
            }

            QLabel#headerSubtitle {
                color: #95a4b5;
            }

            QLabel#headerStatus {
                color: #9bcaf0;
                background-color: #1b2b38;
                border: 1px solid #3e617c;
                border-radius: 13px;
                padding: 5px 11px;
                font-weight: 700;
            }

            QLabel#cardCaption,
            QLabel#metricCaption {
                color: #8494a4;
                font-size: 7.5pt;
                font-weight: 700;
            }

            QLabel#cardValue,
            QLabel#metricValue {
                color: #9cc8e8;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #8ec7ef;
                font-size: 10.5pt;
                font-weight: 700;
            }

            QLabel#footerStatus {
                color: #9ee6ad;
                background-color: #17361f;
                border: 1px solid #3e7750;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 700;
            }

            QTableWidget#historyTable {
                background-color: #11161b;
                alternate-background-color: #171d23;
                color: #d7dee7;
                border: 1px solid #3b4652;
                gridline-color: #303a43;
                selection-background-color: #285f87;
                selection-color: #ffffff;
            }

            QHeaderView::section {
                background-color: #202830;
                color: #9bcaf0;
                border: none;
                border-right: 1px solid #3b4652;
                border-bottom: 1px solid #3b4652;
                padding: 7px;
                font-weight: 700;
            }

            QPushButton#secondaryButton {
                color: #aac5d7;
                background-color: #1d2a33;
                border: 1px solid #405d70;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background-color: #263947;
            }

            QPushButton#dangerButton {
                color: #f0a2a2;
                background-color: #382021;
                border: 1px solid #714043;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
            }

            QPushButton#dangerButton:hover {
                color: #ffffff;
                background-color: #a93d43;
            }

            QPushButton#closeButton {
                color: #ffffff;
                background-color: #256f9f;
                border: 1px solid #3985b7;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
            }

            QPushButton#closeButton:hover {
                background-color: #3184b8;
            }
        """)

    def _apply_light_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #f4f7fb;
                color: #1f2937;
                font-family: "Noto Sans", "DejaVu Sans", sans-serif;
                font-size: 9pt;
            }

            QFrame#headerFrame,
            QFrame#card,
            QFrame#panel {
                background-color: #ffffff;
                border: 1px solid #d7e0ea;
                border-radius: 9px;
            }

            QLabel#headerTitle {
                color: #183b56;
                font-size: 18pt;
                font-weight: 700;
            }

            QLabel#headerSubtitle {
                color: #60758a;
            }

            QLabel#headerStatus {
                color: #2563a6;
                background-color: #eaf3ff;
                border: 1px solid #bdd5f2;
                border-radius: 13px;
                padding: 5px 11px;
                font-weight: 700;
            }

            QLabel#cardCaption,
            QLabel#metricCaption {
                color: #718096;
                font-size: 7.5pt;
                font-weight: 700;
            }

            QLabel#cardValue,
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

            QLabel#footerStatus {
                color: #2f6f4e;
                background-color: #eaf7ef;
                border: 1px solid #c8e5d2;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 700;
            }

            QTableWidget#historyTable {
                background-color: #ffffff;
                alternate-background-color: #f7f9fc;
                color: #263746;
                border: 1px solid #d7e0ea;
                gridline-color: #e4eaf0;
                selection-background-color: #d9ebfa;
                selection-color: #183b56;
            }

            QHeaderView::section {
                background-color: #eef4f9;
                color: #315f86;
                border: none;
                border-right: 1px solid #d7e0ea;
                border-bottom: 1px solid #d7e0ea;
                padding: 7px;
                font-weight: 700;
            }

            QPushButton#secondaryButton {
                color: #31566f;
                background-color: #eef5fa;
                border: 1px solid #a8c3d7;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background-color: #deedf7;
            }

            QPushButton#dangerButton {
                color: #a23030;
                background-color: #fff2f2;
                border: 1px solid #dfa3a3;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
            }

            QPushButton#dangerButton:hover {
                color: #ffffff;
                background-color: #c94b4b;
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
        """)
