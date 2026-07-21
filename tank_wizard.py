from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_paths import APP_DIR, REFERENCES_DIR
from capture import capture_window_region
from compare import compare_images
from project_store import load_config, save_reference
from window_finder import find_elite_window

TANK_REFERENCES_DIR = REFERENCES_DIR
TANK_CATALOG_PATH = APP_DIR / "config" / "tank_reference_catalog.json"


def load_tank_reference_catalog() -> list[dict]:
    """Lädt den tankspezifischen Referenzkatalog."""

    if not TANK_CATALOG_PATH.is_file():
        raise FileNotFoundError(
            f"Tank-Referenzkatalog nicht gefunden:\n{TANK_CATALOG_PATH}"
        )

    try:
        data = json.loads(TANK_CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültige JSON-Datei:\n{TANK_CATALOG_PATH}\n\n{exc}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError("Der Tank-Referenzkatalog muss eine JSON-Liste sein.")

    entries = [entry for entry in data if isinstance(entry, dict) and entry.get("name")]

    if not entries:
        raise ValueError("Der Tank-Referenzkatalog enthält keine gültigen Einträge.")

    return entries


class RegionOverlay(QDialog):
    """Verschiebbarer und skalierbarer Rahmen für einen Bildschirmbereich."""

    RESIZE_MARGIN = 16
    OUTER_BORDER_COLOR = QColor("#000000")
    INNER_BORDER_COLOR = QColor("#FFD800")
    RESIZE_HANDLE_COLOR = QColor("#FFFFFF")

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        position_changed=None,
        size_changed=None,
    ) -> None:
        super().__init__()

        self.position_changed = position_changed
        self.size_changed = size_changed

        self.drag_offset = None
        self.resizing = False
        self.resize_start_global = None
        self.resize_start_size = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(x, y, width, height)
        self.setMouseTracking(True)
        self.setMinimumSize(20, 20)

    def paintEvent(self, event) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer_pen = QPen(self.OUTER_BORDER_COLOR)
        outer_pen.setWidth(6)
        painter.setPen(outer_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(
            3,
            3,
            max(1, self.width() - 6),
            max(1, self.height() - 6),
        )

        inner_pen = QPen(self.INNER_BORDER_COLOR)
        inner_pen.setWidth(3)
        painter.setPen(inner_pen)
        painter.drawRect(
            4,
            4,
            max(1, self.width() - 8),
            max(1, self.height() - 8),
        )

        handle_x = self.width() - self.RESIZE_MARGIN
        handle_y = self.height() - self.RESIZE_MARGIN
        handle_size = self.RESIZE_MARGIN - 3

        handle_border_pen = QPen(self.OUTER_BORDER_COLOR)
        handle_border_pen.setWidth(2)
        painter.setPen(handle_border_pen)
        painter.setBrush(self.RESIZE_HANDLE_COLOR)
        painter.drawRect(
            handle_x,
            handle_y,
            handle_size,
            handle_size,
        )

        marker_pen = QPen(self.INNER_BORDER_COLOR)
        marker_pen.setWidth(3)
        painter.setPen(marker_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(
            handle_x + 4,
            handle_y + handle_size - 4,
            handle_x + handle_size - 4,
            handle_y + 4,
        )

    def _is_resize_area(self, position) -> bool:
        return (
            position.x() >= self.width() - self.RESIZE_MARGIN
            and position.y() >= self.height() - self.RESIZE_MARGIN
        )

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        if self._is_resize_area(event.position()):
            self.resizing = True
            self.resize_start_global = event.globalPosition().toPoint()
            self.resize_start_size = self.size()
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(Qt.SizeAllCursor)

        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.resize_start_global

            new_width = max(
                self.minimumWidth(),
                self.resize_start_size.width() + delta.x(),
            )
            new_height = max(
                self.minimumHeight(),
                self.resize_start_size.height() + delta.y(),
            )

            self.resize(new_width, new_height)

            if self.size_changed is not None:
                self.size_changed(new_width, new_height)

            event.accept()
            return

        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            new_position = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_position)

            if self.position_changed is not None:
                self.position_changed(self.x(), self.y())

            event.accept()
            return

        if self._is_resize_area(event.position()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeAllCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        if self.resizing:
            self.resizing = False

            if self.size_changed is not None:
                self.size_changed(
                    self.width(),
                    self.height(),
                )
        else:
            self.drag_offset = None

            if self.position_changed is not None:
                self.position_changed(
                    self.x(),
                    self.y(),
                )

        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.close()
            event.accept()


class ReferenceReviewDialog(QDialog):
    """Zeigt Asset-Vorlage und neue Aufnahme nebeneinander."""

    def __init__(
        self,
        *,
        template_path: Path | None,
        captured_path: Path,
        stability_percent: float,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Tank-Referenzaufnahme prüfen")
        self.resize(900, 520)
        self.setMinimumSize(760, 440)

        layout = QVBoxLayout(self)

        title = QLabel("Neue Tank-Referenz prüfen")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        stability_label = QLabel(f"Stabilität: {stability_percent:.2f} %")
        stability_label.setAlignment(Qt.AlignCenter)
        stability_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(stability_label)

        image_row = QHBoxLayout()

        image_row.addWidget(
            self._create_image_panel(
                title="Asset-Vorlage",
                image_path=template_path,
                missing_text="Keine Asset-Vorlage gefunden.",
            )
        )

        image_row.addWidget(
            self._create_image_panel(
                title="Neue Aufnahme",
                image_path=captured_path,
                missing_text=("Neue Aufnahme konnte nicht angezeigt werden."),
            )
        )

        layout.addLayout(image_row, 1)

        hint = QLabel(
            "Vergleiche Vorlage und Aufnahme. Übernimm die "
            "Aufnahme nur, wenn Ausschnitt und Motiv übereinstimmen."
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()

        accept_button = buttons.addButton(
            "Übernehmen",
            QDialogButtonBox.AcceptRole,
        )
        retry_button = buttons.addButton(
            "Nochmal aufnehmen",
            QDialogButtonBox.RejectRole,
        )

        accept_button.clicked.connect(self.accept)
        retry_button.clicked.connect(self.reject)

        if stability_percent < 93.0:
            retry_button.setDefault(True)
            retry_button.setFocus()
        else:
            accept_button.setDefault(True)

        layout.addWidget(buttons)

    def _create_image_panel(
        self,
        *,
        title: str,
        image_path: Path | None,
        missing_text: str,
    ) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 17px; font-weight: bold;")
        panel_layout.addWidget(title_label)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(320, 260)
        image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        image_label.setStyleSheet("border: 1px solid gray; background: #202020;")

        if image_path is not None and image_path.is_file():
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        410,
                        300,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                image_label.setText(missing_text)
        else:
            image_label.setText(missing_text)

        panel_layout.addWidget(image_label, 1)

        path_label = QLabel(str(image_path) if image_path is not None else "")
        path_label.setAlignment(Qt.AlignCenter)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #A0A0A0;")
        panel_layout.addWidget(path_label)

        return panel


class TankWizardWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("CTS Tank Wizard - Reference Setup & Calibration")
        self.resize(1180, 720)
        self.setMinimumSize(900, 620)

        self.output_dir = TANK_REFERENCES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.reference_catalog = load_tank_reference_catalog()
        self.catalog_by_name = {
            entry["name"]: entry for entry in self.reference_catalog
        }

        self.selected_reference_name: str | None = None

        central = QWidget()
        self.setCentralWidget(central)

        outer_layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        outer_layout.addWidget(splitter)

        # Linke Seite: tankspezifische Referenzliste
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)

        list_title = QLabel("Tank-Einrichtung")
        list_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        list_layout.addWidget(list_title)

        info_label = QLabel(
            "Menü 1 und Menü 2 werden aus dem Vision Wizard "
            "übernommen. Hier werden nur neue Tank-Schritte "
            "eingerichtet."
        )
        info_label.setWordWrap(True)
        list_layout.addWidget(info_label)

        self.progress_label = QLabel()
        list_layout.addWidget(self.progress_label)

        self.reference_list = QTreeWidget()
        self.reference_list.setHeaderHidden(True)
        self.reference_list.setIndentation(18)
        self.reference_list.currentItemChanged.connect(self.reference_selection_changed)
        list_layout.addWidget(self.reference_list)

        splitter.addWidget(list_panel)

        # Rechte Seite: Vorlage, Einstellungen und Live-Vorschau
        editor_panel = QWidget()
        main_layout = QVBoxLayout(editor_panel)

        template_title = QLabel("Vorlage")
        template_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(template_title)

        self.template_preview = QLabel("Links einen Tank-Schritt auswählen.")
        self.template_preview.setAlignment(Qt.AlignCenter)
        self.template_preview.setMinimumHeight(180)
        self.template_preview.setMaximumHeight(220)
        self.template_preview.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored,
        )
        self.template_preview.setStyleSheet(
            "border: 1px solid gray; background: #202020;"
        )
        main_layout.addWidget(self.template_preview)

        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setReadOnly(True)

        self.x_input = QSpinBox()
        self.x_input.setRange(0, 10000)
        self.x_input.setValue(400)

        self.y_input = QSpinBox()
        self.y_input.setRange(0, 10000)
        self.y_input.setValue(500)

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 5000)
        self.width_input.setValue(300)

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 5000)
        self.height_input.setValue(160)

        self.x_input.valueChanged.connect(self.update_overlay_geometry)
        self.y_input.valueChanged.connect(self.update_overlay_geometry)
        self.width_input.valueChanged.connect(self.update_overlay_geometry)
        self.height_input.valueChanged.connect(self.update_overlay_geometry)

        form.addRow("Name:", self.name_input)
        form.addRow("X:", self.x_input)
        form.addRow("Y:", self.y_input)
        form.addRow("Breite:", self.width_input)
        form.addRow("Höhe:", self.height_input)

        main_layout.addLayout(form)

        button_row = QHBoxLayout()

        self.capture_button = QPushButton("Ausschnitt aufnehmen")
        self.capture_button.clicked.connect(self.capture_reference)

        self.mark_button = QPushButton("Bereich markieren")
        self.mark_button.clicked.connect(self.show_region_overlay)

        self.compare_button = QPushButton("Vergleichen")
        self.compare_button.clicked.connect(self.compare_reference)

        button_row.addWidget(self.capture_button)
        button_row.addWidget(self.mark_button)
        button_row.addWidget(self.compare_button)
        button_row.addStretch()

        main_layout.addLayout(button_row)

        self.result_label = QLabel("Noch kein Vergleich")
        self.result_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(self.result_label)

        self.output_label = QLabel(str(self.output_dir))
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.output_label)

        live_title = QLabel("Live-Vorschau")
        live_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(live_title)

        self.preview = QLabel("Live-Vorschau wird gestartet")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(220)
        self.preview.setMaximumHeight(280)
        self.preview.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored,
        )
        self.preview.setStyleSheet("border: 1px solid gray; background: #202020;")
        main_layout.addWidget(self.preview)

        splitter.addWidget(editor_panel)
        splitter.setSizes([360, 820])

        self.refresh_reference_list()

        self.live_timer = QTimer(self)
        self.live_timer.setInterval(200)
        self.live_timer.timeout.connect(self.update_live_preview)
        self.live_timer.start()

    def refresh_reference_list(self) -> None:
        current_name = self.selected_reference_name

        config = load_config()
        references = config.get("references", {})

        self.reference_list.blockSignals(True)
        self.reference_list.clear()

        completed = 0
        selected_item = None

        group_items: dict[str, QTreeWidgetItem] = {}
        group_counts: dict[str, list[int]] = {}

        for entry in self.reference_catalog:
            group_name = str(entry.get("group", "Tank"))

            group_item = group_items.get(group_name)

            if group_item is None:
                group_item = QTreeWidgetItem([group_name])
                group_item.setFlags(
                    group_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsUserCheckable
                )

                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)

                self.reference_list.addTopLevelItem(group_item)

                group_items[group_name] = group_item
                group_counts[group_name] = [0, 0]

            name = entry["name"]
            title = str(entry.get("title", name))
            reference_data = references.get(name)

            is_complete = False

            if isinstance(reference_data, dict):
                image_name = str(reference_data.get("image", "")).strip()

                if image_name:
                    is_complete = (self.output_dir / image_name).is_file()

            item = QTreeWidgetItem([title])
            item.setData(0, Qt.UserRole, name)
            item.setCheckState(
                0,
                Qt.Checked if is_complete else Qt.Unchecked,
            )
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            item.setToolTip(0, name)

            group_item.addChild(item)
            group_counts[group_name][1] += 1

            if is_complete:
                completed += 1
                group_counts[group_name][0] += 1

            if name == current_name:
                selected_item = item

        for group_name, group_item in group_items.items():
            done, total = group_counts[group_name]
            group_item.setText(
                0,
                f"{group_name} ({done}/{total})",
            )
            group_item.setExpanded(True)

        total = len(self.reference_catalog)
        percent = int(round(completed / total * 100)) if total else 0

        self.progress_label.setText(f"{completed} / {total} erstellt ({percent} %)")

        self.reference_list.blockSignals(False)

        if selected_item is not None:
            self.reference_list.setCurrentItem(selected_item)
        elif self.reference_list.topLevelItemCount() > 0:
            first_group = self.reference_list.topLevelItem(0)

            if first_group.childCount() > 0:
                self.reference_list.setCurrentItem(first_group.child(0))

    def reference_selection_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        del previous

        if current is None:
            return

        name_data = current.data(0, Qt.UserRole)

        if not name_data:
            return

        name = str(name_data)
        self.selected_reference_name = name
        self.name_input.setText(name)

        entry = self.catalog_by_name.get(name)

        if entry is None:
            return

        description = str(entry.get("description", "")).strip()
        entry_type = str(entry.get("type", "reference")).strip().lower()

        self.description_label.setText(
            description or "Keine zusätzliche Beschreibung vorhanden."
        )

        if entry_type == "ocr":
            self.capture_button.setText("OCR-Bereich speichern")
            self.compare_button.setEnabled(False)
            self.compare_button.setToolTip(
                "Der OCR-Vergleich wird im nächsten Schritt ergänzt."
            )
        else:
            self.capture_button.setText("Ausschnitt aufnehmen")
            self.compare_button.setEnabled(True)
            self.compare_button.setToolTip("")

        template_path = self._get_template_path(name)

        self.template_preview.setPixmap(QPixmap())

        if template_path is not None:
            pixmap = QPixmap(str(template_path))

            if not pixmap.isNull():
                self.template_preview.setPixmap(
                    pixmap.scaled(
                        self.template_preview.contentsRect().size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.template_preview.setText("Vorlage konnte nicht angezeigt werden.")
        else:
            template_value = str(entry.get("template", "")).strip()

            if entry_type == "ocr" and not template_value:
                self.template_preview.setText(
                    "OCR-Bereich\n\n"
                    "Markiere im Elite-Fenster nur den Bereich mit "
                    "dem aktuellen Tankfüllstand, zum Beispiel "
                    "„965/1000“."
                )
            else:
                self.template_preview.setText(
                    "Template nicht gefunden:\n" f"{APP_DIR / template_value}"
                )

        config = load_config()
        reference_data = config.get(
            "references",
            {},
        ).get(name)

        if isinstance(reference_data, dict):
            self.x_input.setValue(int(reference_data.get("x", 400)))
            self.y_input.setValue(int(reference_data.get("y", 500)))
            self.width_input.setValue(int(reference_data.get("width", 300)))
            self.height_input.setValue(int(reference_data.get("height", 160)))
        else:
            region = entry.get("region", {})

            if isinstance(region, dict):
                self.x_input.setValue(int(region.get("x", 400)))
                self.y_input.setValue(int(region.get("y", 500)))
                self.width_input.setValue(int(region.get("width", 220)))
                self.height_input.setValue(int(region.get("height", 70)))

    @staticmethod
    def _get_window_position(window) -> tuple[int, int]:
        if isinstance(window, dict):
            x = window.get("x", window.get("left"))
            y = window.get("y", window.get("top"))
        else:
            x = getattr(window, "x", None)
            y = getattr(window, "y", None)

            if x is None:
                x = getattr(window, "left", None)

            if y is None:
                y = getattr(window, "top", None)

        if x is None or y is None:
            raise RuntimeError(
                "Die Position des Elite-Fensters konnte " "nicht bestimmt werden."
            )

        return int(x), int(y)

    def _get_elite_window_position(self) -> tuple[int, int]:
        window = find_elite_window()

        if window is None:
            raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

        return self._get_window_position(window)

    def _get_template_path(
        self,
        name: str,
    ) -> Path | None:
        entry = self.catalog_by_name.get(name)

        if entry is None:
            return None

        template_value = str(entry.get("template", "")).strip()

        if not template_value:
            return None

        template_path = Path(template_value)

        if not template_path.is_absolute():
            template_path = APP_DIR / template_path

        if not template_path.is_file():
            return None

        return template_path

    def update_live_preview(self) -> None:
        try:
            window = find_elite_window()

            if window is None:
                raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

            image = capture_window_region(
                window=window,
                x=self.x_input.value(),
                y=self.y_input.value(),
                width=self.width_input.value(),
                height=self.height_input.value(),
            )

            rgb_image = image.convert("RGB")
            image_data = rgb_image.tobytes("raw", "RGB")

            qimage = QImage(
                image_data,
                rgb_image.width,
                rgb_image.height,
                rgb_image.width * 3,
                QImage.Format_RGB888,
            ).copy()

            pixmap = QPixmap.fromImage(qimage)

            self.preview.setPixmap(
                pixmap.scaled(
                    self.preview.contentsRect().size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        except Exception as exc:
            self.preview.setPixmap(QPixmap())
            self.preview.setText(f"Live-Vorschau Fehler:\n{exc}")

    def capture_reference(self) -> None:
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Keine Referenz gewählt",
                "Bitte links einen Tank-Schritt auswählen.",
            )
            return

        entry = self.catalog_by_name.get(name)

        if entry is None:
            QMessageBox.warning(
                self,
                "Unbekannte Referenz",
                f"'{name}' ist nicht im Tank-Katalog enthalten.",
            )
            return

        output_path = self.output_dir / entry["filename"]
        temp_path = output_path.with_name(
            f".{output_path.stem}_aufnahme_test" f"{output_path.suffix}"
        )

        overlay_was_visible = (
            hasattr(self, "region_overlay") and self.region_overlay.isVisible()
        )

        if overlay_was_visible:
            self.region_overlay.hide()
            QApplication.processEvents()

        self.capture_button.setEnabled(False)
        self.result_label.setText("Aufnahme wird geprüft...")

        QTimer.singleShot(
            300,
            lambda: self._capture_reference_first_image(
                name=name,
                output_path=output_path,
                temp_path=temp_path,
                overlay_was_visible=overlay_was_visible,
            ),
        )

    def _capture_reference_first_image(
        self,
        *,
        name: str,
        output_path: Path,
        temp_path: Path,
        overlay_was_visible: bool,
    ) -> None:
        try:
            window = find_elite_window()

            if window is None:
                raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

            capture_window_region(
                window=window,
                x=self.x_input.value(),
                y=self.y_input.value(),
                width=self.width_input.value(),
                height=self.height_input.value(),
                output_path=temp_path,
            )

        except Exception as exc:
            self._finish_reference_capture(
                overlay_was_visible=overlay_was_visible,
                temp_path=temp_path,
            )
            QMessageBox.critical(
                self,
                "Fehler",
                str(exc),
            )
            return

        QTimer.singleShot(
            300,
            lambda: self._validate_reference_capture(
                name=name,
                output_path=output_path,
                temp_path=temp_path,
                overlay_was_visible=overlay_was_visible,
            ),
        )

    def _validate_reference_capture(
        self,
        *,
        name: str,
        output_path: Path,
        temp_path: Path,
        overlay_was_visible: bool,
    ) -> None:
        try:
            window = find_elite_window()

            if window is None:
                raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

            current_image = capture_window_region(
                window=window,
                x=self.x_input.value(),
                y=self.y_input.value(),
                width=self.width_input.value(),
                height=self.height_input.value(),
            )

            similarity = compare_images(
                temp_path,
                current_image,
            )
            percent = similarity * 100.0

            self.result_label.setText(f"{name}: {percent:.2f} %")

            review_dialog = ReferenceReviewDialog(
                template_path=self._get_template_path(name),
                captured_path=temp_path,
                stability_percent=percent,
                parent=self,
            )

            if (
                str(
                    self.catalog_by_name.get(name, {}).get(
                        "type",
                        "reference",
                    )
                ).lower()
                == "ocr"
            ):
                review_dialog.setWindowTitle("OCR-Bereich prüfen")

            should_save = review_dialog.exec() == QDialog.Accepted

            if should_save:
                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                temp_path.replace(output_path)

                save_reference(
                    name=name,
                    x=self.x_input.value(),
                    y=self.y_input.value(),
                    width=self.width_input.value(),
                    height=self.height_input.value(),
                    image_filename=output_path.name,
                )

                self.refresh_reference_list()

                entry_type = str(
                    self.catalog_by_name.get(name, {}).get(
                        "type",
                        "reference",
                    )
                ).lower()

                if entry_type == "ocr":
                    message_title = "OCR-Bereich gespeichert"
                    message_text = (
                        f"Kontrollbild und Koordinaten gespeichert:\n"
                        f"{output_path}\n\n"
                        f"Stabilität: {percent:.2f} %"
                    )
                else:
                    message_title = "Tank-Referenz gespeichert"
                    message_text = (
                        f"Referenzbild gespeichert:\n"
                        f"{output_path}\n\n"
                        f"Stabilität: {percent:.2f} %"
                    )

                QMessageBox.information(
                    self,
                    message_title,
                    message_text,
                )
            else:
                if temp_path.exists():
                    temp_path.unlink()

                self.result_label.setText(f"{name}: bitte noch einmal aufnehmen")

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Qualitätsprüfung fehlgeschlagen",
                str(exc),
            )

        finally:
            self._finish_reference_capture(
                overlay_was_visible=overlay_was_visible,
                temp_path=temp_path,
            )

    def _finish_reference_capture(
        self,
        *,
        overlay_was_visible: bool,
        temp_path: Path,
    ) -> None:
        self.capture_button.setEnabled(True)

        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

        if overlay_was_visible and hasattr(self, "region_overlay"):
            self.region_overlay.show()
            self.region_overlay.raise_()

    def compare_reference(self) -> None:
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Keine Referenz gewählt",
                "Bitte links einen Tank-Schritt auswählen.",
            )
            return

        try:
            config = load_config()
            reference_data = config.get(
                "references",
                {},
            ).get(name)

            if reference_data is None:
                raise KeyError(f"Keine Referenz mit dem Namen " f"'{name}' gefunden.")

            reference_path = self.output_dir / reference_data["image"]

            window = find_elite_window()

            if window is None:
                raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

            current_image = capture_window_region(
                window=window,
                x=int(reference_data["x"]),
                y=int(reference_data["y"]),
                width=int(reference_data["width"]),
                height=int(reference_data["height"]),
            )

            similarity = compare_images(
                reference_path,
                current_image,
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Vergleich fehlgeschlagen",
                str(exc),
            )
            return

        self.result_label.setText(f"{name}: {similarity * 100.0:.2f} %")

    def show_region_overlay(self) -> None:
        if hasattr(self, "region_overlay"):
            self.region_overlay.close()

        try:
            window_x, window_y = self._get_elite_window_position()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Elite-Fenster nicht gefunden",
                str(exc),
            )
            return

        self.region_overlay = RegionOverlay(
            x=window_x + self.x_input.value(),
            y=window_y + self.y_input.value(),
            width=self.width_input.value(),
            height=self.height_input.value(),
            position_changed=self.update_region_position,
            size_changed=self.update_region_size,
        )
        self.region_overlay.show()

    def update_region_position(
        self,
        x: int,
        y: int,
    ) -> None:
        try:
            window_x, window_y = self._get_elite_window_position()
        except Exception:
            return

        self.x_input.setValue(max(0, x - window_x))
        self.y_input.setValue(max(0, y - window_y))

    def update_overlay_geometry(self) -> None:
        if not hasattr(self, "region_overlay"):
            return

        if not self.region_overlay.isVisible():
            return

        try:
            window_x, window_y = self._get_elite_window_position()
        except Exception:
            return

        self.region_overlay.setGeometry(
            window_x + self.x_input.value(),
            window_y + self.y_input.value(),
            self.width_input.value(),
            self.height_input.value(),
        )

    def update_region_size(
        self,
        width: int,
        height: int,
    ) -> None:
        self.width_input.setValue(width)
        self.height_input.setValue(height)


def run_gui() -> None:
    app = QApplication.instance() or QApplication([])
    window = TankWizardWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_gui()
