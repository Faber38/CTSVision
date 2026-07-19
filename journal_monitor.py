from __future__ import annotations

import json

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

DEFAULT_JOURNAL_DIRECTORY = Path(
    "~/.steam/debian-installation/steamapps/compatdata/"
    "359320/pfx/drive_c/users/steamuser/Saved Games/"
    "Frontier Developments/Elite Dangerous"
).expanduser()


class JournalMonitor(QObject):
    """
    Überwacht die jeweils aktuelle Journal-Datei von Elite Dangerous.

    Beim Start wird an das Ende der vorhandenen Journal-Datei gesprungen.
    Dadurch werden nur Ereignisse verarbeitet, die danach neu hinzukommen.
    """

    event_received = Signal(dict)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        journal_directory: str | Path = DEFAULT_JOURNAL_DIRECTORY,
        poll_interval_ms: int = 500,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.journal_directory = Path(journal_directory).expanduser().resolve()

        self.poll_interval_ms = poll_interval_ms

        self._timer = QTimer(self)
        self._timer.setInterval(self.poll_interval_ms)
        self._timer.timeout.connect(self._poll)

        self._current_file: Path | None = None
        self._file_position = 0
        self._running = False

    # --------------------------------------------------
    # Öffentliche Methoden
    # --------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_file(self) -> Path | None:
        return self._current_file

    def set_journal_directory(
        self,
        journal_directory: str | Path,
    ) -> None:
        """
        Ändert den Journal-Ordner.

        Ein laufender Monitor wird dabei neu gestartet.
        """

        was_running = self._running

        if was_running:
            self.stop()

        self.journal_directory = Path(journal_directory).expanduser().resolve()

        self._current_file = None
        self._file_position = 0

        if was_running:
            self.start()

    def start(self) -> None:
        """
        Startet die Journal-Überwachung.
        """

        if self._running:
            return

        if not self.journal_directory.exists():
            message = (
                "Journal-Ordner wurde nicht gefunden: " f"{self.journal_directory}"
            )

            self.error_occurred.emit(message)
            return

        if not self.journal_directory.is_dir():
            message = "Der Journal-Pfad ist kein Ordner: " f"{self.journal_directory}"

            self.error_occurred.emit(message)
            return

        newest_file = self._find_newest_journal()

        if newest_file is None:
            message = "Im Journal-Ordner wurde keine " "Journal.*.log-Datei gefunden."

            self.error_occurred.emit(message)
            return

        try:
            self._current_file = newest_file

            # Beim ersten Start nur neue Zeilen lesen.
            self._file_position = newest_file.stat().st_size

        except OSError as exc:
            self.error_occurred.emit(
                f"Journal-Datei konnte nicht geöffnet werden: {exc}"
            )
            return

        self._running = True
        self._timer.start()

        self.status_changed.emit(f"Journal verbunden: {newest_file.name}")

    def stop(self) -> None:
        """
        Beendet die Journal-Überwachung.
        """

        if not self._running:
            return

        self._timer.stop()
        self._running = False

        self.status_changed.emit("Journal-Überwachung beendet.")

    # --------------------------------------------------
    # Journal-Dateien
    # --------------------------------------------------

    def _find_newest_journal(self) -> Path | None:
        """
        Liefert die zuletzt geänderte Journal-Datei.
        """

        try:
            files = list(self.journal_directory.glob("Journal.*.log"))

        except OSError as exc:
            self.error_occurred.emit(
                f"Journal-Ordner konnte nicht gelesen werden: {exc}"
            )
            return None

        if not files:
            return None

        try:
            return max(
                files,
                key=lambda path: path.stat().st_mtime,
            )

        except OSError as exc:
            self.error_occurred.emit(
                f"Journal-Dateien konnten nicht geprüft werden: {exc}"
            )
            return None

    def _switch_to_new_file(
        self,
        new_file: Path,
    ) -> None:
        """
        Wechselt auf eine neu angelegte Journal-Datei.

        Bei einem späteren Dateiewechsel wird vom Anfang gelesen,
        damit keine Ereignisse der neuen Sitzung verloren gehen.
        """

        self._current_file = new_file
        self._file_position = 0

        self.status_changed.emit(f"Neue Journal-Datei erkannt: {new_file.name}")

    # --------------------------------------------------
    # Überwachung
    # --------------------------------------------------

    def _poll(self) -> None:
        """
        Wird regelmäßig durch den QTimer aufgerufen.
        """

        if not self._running:
            return

        newest_file = self._find_newest_journal()

        if newest_file is None:
            return

        if self._current_file != newest_file:
            self._switch_to_new_file(newest_file)

        if self._current_file is None:
            return

        try:
            current_size = self._current_file.stat().st_size

            # Datei wurde eventuell geleert oder neu geschrieben.
            if current_size < self._file_position:
                self._file_position = 0

            with self._current_file.open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:

                handle.seek(self._file_position)

                while True:
                    line = handle.readline()

                    if not line:
                        break

                    self._process_line(line)

                self._file_position = handle.tell()

        except OSError as exc:
            self.error_occurred.emit(f"Fehler beim Lesen des Journals: {exc}")

    def _process_line(
        self,
        line: str,
    ) -> None:
        """
        Wandelt eine Journal-Zeile in ein Python-Dictionary um.
        """

        line = line.strip()

        if not line:
            return

        try:
            event_data = json.loads(line)

        except json.JSONDecodeError:
            return

        if not isinstance(event_data, dict):
            return

        event_name = event_data.get("event")

        if not event_name:
            return

        print(event_data)
        self.event_received.emit(event_data)
