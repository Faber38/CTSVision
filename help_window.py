from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app_paths import APP_DIR


class HelpWindow(QDialog):
    """Integrierte deutschsprachige Hilfe für CTSVision."""

    def __init__(
        self,
        parent=None,
        *,
        dark_mode: bool = False,
    ) -> None:
        super().__init__(parent)

        self.dark_mode = bool(dark_mode)
        self.help_path = APP_DIR / "docs" / "help_de.md"
        self.help_text = ""

        self.setWindowTitle("CTSVision - Hilfe")
        self.resize(1050, 720)
        self.setMinimumSize(820, 560)

        self._build_ui()
        self._load_help()
        self._apply_theme()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()

        title = QLabel("CTSVision Hilfe")
        title.setObjectName("helpTitle")

        subtitle = QLabel(
            "Bedienung • Vision Wizard • Automatik • Tanken • Fehlerhilfe"
        )
        subtitle.setObjectName("helpSubtitle")

        title_block = QVBoxLayout()
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        header.addLayout(title_block)
        header.addStretch()

        close_button = QPushButton("Schließen")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.accept)
        header.addWidget(close_button)

        layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(12)

        self.topic_list = QListWidget()
        self.topic_list.setObjectName("topicList")
        self.topic_list.setMinimumWidth(230)
        self.topic_list.setMaximumWidth(290)
        self.topic_list.currentTextChanged.connect(self._jump_to_topic)

        self.browser = QTextBrowser()
        self.browser.setObjectName("helpBrowser")
        self.browser.setOpenExternalLinks(True)

        content.addWidget(self.topic_list)
        content.addWidget(self.browser, 1)

        layout.addLayout(content, 1)

    def _load_help(self) -> None:
        if not self.help_path.is_file():
            self.browser.setPlainText(
                "Die Hilfedatei wurde nicht gefunden.\n\n"
                f"Erwarteter Pfad:\n{self.help_path}"
            )
            return

        try:
            self.help_text = self.help_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.browser.setPlainText(
                "Die Hilfedatei konnte nicht gelesen werden.\n\n"
                f"{exc}"
            )
            return

        self.browser.setMarkdown(self.help_text)

        self.topic_list.clear()

        for raw_line in self.help_text.splitlines():
            line = raw_line.strip()

            if line.startswith("## ") and not line.startswith("### "):
                title = line[3:].strip()

                if title:
                    self.topic_list.addItem(title)

        if self.topic_list.count() > 0:
            self.topic_list.setCurrentRow(0)

    def _jump_to_topic(self, topic: str) -> None:
        if not topic:
            return

        cursor = self.browser.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.browser.setTextCursor(cursor)

        if self.browser.find(topic):
            cursor = self.browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            self.browser.setTextCursor(cursor)
            self.browser.ensureCursorVisible()

    def set_dark_mode(self, enabled: bool) -> None:
        self.dark_mode = bool(enabled)
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #151a20;
                    color: #d7dee7;
                    font-size: 10pt;
                }

                QLabel#helpTitle {
                    color: #76b9ea;
                    font-size: 20pt;
                    font-weight: 700;
                }

                QLabel#helpSubtitle {
                    color: #95a4b5;
                    font-size: 9.5pt;
                }

                QListWidget#topicList {
                    background-color: #1b2229;
                    color: #d7dee7;
                    border: 1px solid #435261;
                    border-radius: 7px;
                    padding: 4px;
                }

                QListWidget#topicList::item {
                    padding: 7px 8px;
                    border-radius: 4px;
                }

                QListWidget#topicList::item:selected {
                    background-color: #244861;
                    color: #ffffff;
                }

                QListWidget#topicList::item:hover {
                    background-color: #25323d;
                }

                QTextBrowser#helpBrowser {
                    background-color: #10151a;
                    color: #d7dee7;
                    border: 1px solid #435261;
                    border-radius: 7px;
                    padding: 10px;
                    selection-background-color: #2b6f9e;
                }

                QPushButton#closeButton {
                    color: #ffffff;
                    background-color: #256f9f;
                    border: 1px solid #3985b7;
                    border-radius: 6px;
                    padding: 7px 16px;
                    font-weight: 700;
                }

                QPushButton#closeButton:hover {
                    background-color: #3184b8;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f3f6fa;
                    color: #1f2933;
                    font-size: 10pt;
                }

                QLabel#helpTitle {
                    color: #123f66;
                    font-size: 20pt;
                    font-weight: 700;
                }

                QLabel#helpSubtitle {
                    color: #68798a;
                    font-size: 9.5pt;
                }

                QListWidget#topicList {
                    background-color: #ffffff;
                    color: #243746;
                    border: 1px solid #b9c8d6;
                    border-radius: 7px;
                    padding: 4px;
                }

                QListWidget#topicList::item {
                    padding: 7px 8px;
                    border-radius: 4px;
                }

                QListWidget#topicList::item:selected {
                    background-color: #dcecf8;
                    color: #123f66;
                }

                QListWidget#topicList::item:hover {
                    background-color: #eef5fa;
                }

                QTextBrowser#helpBrowser {
                    background-color: #ffffff;
                    color: #263746;
                    border: 1px solid #b9c8d6;
                    border-radius: 7px;
                    padding: 10px;
                    selection-background-color: #2d78b7;
                }

                QPushButton#closeButton {
                    color: #ffffff;
                    background-color: #2478b5;
                    border: 1px solid #1b6399;
                    border-radius: 6px;
                    padding: 7px 16px;
                    font-weight: 700;
                }

                QPushButton#closeButton:hover {
                    background-color: #3189c4;
                }
            """)


__all__ = ["HelpWindow"]
