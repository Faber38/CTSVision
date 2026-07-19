from __future__ import annotations

import csv
import hashlib
import json
import re

from dataclasses import dataclass
from pathlib import Path

from app_paths import ROUTE_STATE_FILE

JUMP_DURATION_MINUTES = 22


@dataclass(frozen=True)
class RoutePoint:
    """
    Ein System beziehungsweise Wegpunkt aus der EDD-Route.
    """

    system: str
    notes: str
    distance: float | None

    x: float | None
    y: float | None
    z: float | None

    star_class: str
    waypoint_distance: float | None
    deviation: float | None
    system_address: str

    fuel_used: int | None
    fuel_left: int | None
    restock_fuel: int | None

    @property
    def extra_notes(self) -> list[str]:
        """
        Liefert Hinweise aus dem Notizfeld, jedoch ohne
        die Angaben zu Fuel used und Must restock.
        """

        result: list[str] = []

        for line in self.notes.splitlines():
            line = line.strip()

            if not line:
                continue

            lowered = line.lower()

            if lowered.startswith("fuel used"):
                continue

            if lowered.startswith("must restock"):
                continue

            result.append(line)

        return result


class RouteManagerError(RuntimeError):
    """
    Fehler beim Laden oder Verarbeiten einer Route.
    """


class RouteManager:
    """
    Liest Routendateien verschiedener Anbieter und verwaltet den Fortschritt.

    Unterstützte CSV-Formate:
        - EDD / Elite Dangerous Discovery
        - Fleet Carrier Router mit der Spalte "System Name"

    current_index bezeichnet die Anzahl der bereits
    abgeschlossenen Sprünge.

    Beispiel:
        current_index = 0
            Noch kein Sprung abgeschlossen.
            Aktuelles Ziel ist der erste Zielwegpunkt.

        current_index = 1
            Der erste Sprung wurde abgeschlossen.
            Aktuelles Ziel ist der zweite Zielwegpunkt.
    """

    def __init__(
        self,
        route_file: str | Path,
        state_file: str | Path = ROUTE_STATE_FILE,
    ) -> None:

        self.route_file = Path(route_file).expanduser().resolve()

        self.state_file = Path(state_file).expanduser().resolve()

        self.points: list[RoutePoint] = []
        self.current_index = 0

        self.route_signature = ""
        self.route_format = ""

        self._load_route()
        self._load_state()

    # --------------------------------------------------
    # CSV laden
    # --------------------------------------------------

    def _load_route(self) -> None:
        """
        Lädt die CSV-Datei, erkennt das Format automatisch und
        wandelt alle Zeilen in einheitliche RoutePoint-Objekte um.
        """

        if not self.route_file.exists():
            raise RouteManagerError(
                f"Die Routendatei wurde nicht gefunden: {self.route_file}"
            )

        try:
            with self.route_file.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                sample = handle.read(8192)
                handle.seek(0)

                delimiter = self._detect_delimiter(sample)

                reader = csv.DictReader(
                    handle,
                    delimiter=delimiter,
                )

                fieldnames = [
                    str(name).strip()
                    for name in (reader.fieldnames or [])
                    if name is not None
                ]

                if not fieldnames:
                    raise RouteManagerError("Die Routendatei enthält keine Kopfzeile.")

                self.route_format = self._detect_route_format(fieldnames)

                for row_number, raw_row in enumerate(
                    reader,
                    start=2,
                ):
                    row = {
                        str(key).strip(): value
                        for key, value in raw_row.items()
                        if key is not None
                    }

                    if self.route_format == "edd":
                        point = self._parse_edd_row(
                            row=row,
                            row_number=row_number,
                        )
                    elif self.route_format == "fleet_carrier_router":
                        point = self._parse_fleet_carrier_row(
                            row=row,
                            row_number=row_number,
                        )
                    else:
                        raise RouteManagerError(
                            "Internes Problem: unbekanntes Routenformat."
                        )

                    self.points.append(point)

        except RouteManagerError:
            raise

        except (OSError, csv.Error) as exc:
            raise RouteManagerError(
                "Die Routendatei konnte nicht " f"gelesen werden: {exc}"
            ) from exc

        if not self.points:
            raise RouteManagerError("Die Routendatei enthält keine Systeme.")

        if len(self.points) < 2:
            raise RouteManagerError("Die Route enthält keinen Sprung.")

        self.route_signature = self._create_signature()

    @staticmethod
    def _detect_delimiter(sample: str) -> str:
        """
        Erkennt Komma oder Semikolon als Trennzeichen.
        """

        try:
            dialect = csv.Sniffer().sniff(
                sample,
                delimiters=";,",
            )
            return dialect.delimiter
        except csv.Error:
            first_line = sample.splitlines()[0] if sample else ""

            if first_line.count(";") >= first_line.count(","):
                return ";"

            return ","

    @staticmethod
    def _detect_route_format(
        fieldnames: list[str],
    ) -> str:
        """
        Erkennt den Anbieter anhand der vorhandenen Spalten.
        """

        available = set(fieldnames)

        edd_required = {
            "System",
            "Notizen",
            "Entfernung",
            "X",
            "Y",
            "Z",
        }

        fleet_carrier_required = {
            "System Name",
            "Distance",
            "Fuel Used",
        }

        if edd_required.issubset(available):
            return "edd"

        if fleet_carrier_required.issubset(available):
            return "fleet_carrier_router"

        columns = ", ".join(fieldnames)

        raise RouteManagerError(
            "Das CSV-Format wurde nicht erkannt. " "Gefundene Spalten: " f"{columns}"
        )

    def _parse_edd_row(
        self,
        *,
        row: dict[str, str],
        row_number: int,
    ) -> RoutePoint:
        """
        Verarbeitet eine Route aus Elite Dangerous Discovery.
        """

        system = (row.get("System") or "").strip()

        if not system:
            raise RouteManagerError(f"Zeile {row_number}: Systemname fehlt.")

        notes = (row.get("Notizen") or "").strip()

        fuel_used, fuel_left = self._extract_fuel(notes)
        restock_fuel = self._extract_restock(notes)

        return RoutePoint(
            system=system,
            notes=notes,
            distance=self._parse_float(
                row.get("Entfernung"),
                decimal_comma=True,
            ),
            x=self._parse_float(
                row.get("X"),
                decimal_comma=True,
            ),
            y=self._parse_float(
                row.get("Y"),
                decimal_comma=True,
            ),
            z=self._parse_float(
                row.get("Z"),
                decimal_comma=True,
            ),
            star_class=(row.get("Sternenklasse") or "").strip(),
            waypoint_distance=self._parse_float(
                row.get("Entf. Wegpunkt"),
                decimal_comma=True,
            ),
            deviation=self._parse_float(
                row.get("Abweichung"),
                decimal_comma=True,
            ),
            system_address=(row.get("System Address") or "").strip(),
            fuel_used=fuel_used,
            fuel_left=fuel_left,
            restock_fuel=restock_fuel,
        )

    def _parse_fleet_carrier_row(
        self,
        *,
        row: dict[str, str],
        row_number: int,
    ) -> RoutePoint:
        """
        Verarbeitet eine CSV des Fleet Carrier Routers.

        Nicht vorhandene EDD-Werte wie X/Y/Z werden mit None belegt.
        Zusätzliche Angaben des Anbieters werden als Hinweise übernommen.
        """

        system = (row.get("System Name") or "").strip()

        if not system:
            raise RouteManagerError(f"Zeile {row_number}: Systemname fehlt.")

        notes = self._build_fleet_carrier_notes(row)

        return RoutePoint(
            system=system,
            notes=notes,
            distance=self._parse_float(
                row.get("Distance"),
                decimal_comma=False,
            ),
            x=None,
            y=None,
            z=None,
            star_class="",
            waypoint_distance=self._parse_float(
                row.get("Distance Remaining"),
                decimal_comma=False,
            ),
            deviation=None,
            system_address="",
            fuel_used=self._parse_int(row.get("Fuel Used")),
            fuel_left=self._parse_int(row.get("Tritium in tank")),
            restock_fuel=None,
        )

    @classmethod
    def _build_fleet_carrier_notes(
        cls,
        row: dict[str, str],
    ) -> str:
        """
        Übernimmt nützliche Zusatzangaben des Fleet Carrier Routers
        in das vorhandene Notizfeld.
        """

        notes: list[str] = []

        distance_remaining = cls._parse_float(
            row.get("Distance Remaining"),
            decimal_comma=False,
        )

        tritium_in_tank = cls._parse_int(row.get("Tritium in tank"))

        tritium_in_market = cls._parse_int(row.get("Tritium in market"))

        if distance_remaining is not None:
            notes.append(f"Distance remaining: {distance_remaining:.2f} ly")

        if tritium_in_tank is not None:
            notes.append(f"Tritium in tank: {tritium_in_tank}")

        if tritium_in_market is not None:
            notes.append(f"Tritium in market: {tritium_in_market}")

        if cls._is_yes(row.get("Icy Ring")):
            notes.append("Icy Ring")

        if cls._is_yes(row.get("Pristine")):
            notes.append("Pristine")

        if cls._is_yes(row.get("Restock Tritium")):
            notes.append("Must restock Tritium")

        return "\n".join(notes)

    @staticmethod
    def _is_yes(
        value: str | None,
    ) -> bool:
        if value is None:
            return False

        return value.strip().lower() in {
            "yes",
            "ja",
            "true",
            "1",
        }

    @staticmethod
    def _parse_float(
        value: str | None,
        *,
        decimal_comma: bool,
    ) -> float | None:
        """
        Wandelt sowohl deutsche Dezimalzahlen als auch Zahlen mit
        Dezimalpunkt sicher um.
        """

        if value is None:
            return None

        text = value.strip().replace(" ", "")

        if not text:
            return None

        if decimal_comma:
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            if "," in text and "." in text:
                if text.rfind(",") > text.rfind("."):
                    text = text.replace(".", "")
                    text = text.replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None

    @classmethod
    def _parse_int(
        cls,
        value: str | None,
    ) -> int | None:
        number = cls._parse_float(
            value,
            decimal_comma=False,
        )

        if number is None:
            return None

        return int(round(number))

    @staticmethod
    def _extract_fuel(
        notes: str,
    ) -> tuple[int | None, int | None]:

        match = re.search(
            r"Fuel\s+used\s+(\d+)\s*,\s*left\s+(\d+)",
            notes,
            flags=re.IGNORECASE,
        )

        if not match:
            return None, None

        return (
            int(match.group(1)),
            int(match.group(2)),
        )

    @staticmethod
    def _extract_restock(
        notes: str,
    ) -> int | None:

        match = re.search(
            r"Must\s+restock\s+(\d+)",
            notes,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return int(match.group(1))

    # --------------------------------------------------
    # Fortschritt speichern und laden
    # --------------------------------------------------

    def _create_signature(self) -> str:

        route_text = "\n".join(point.system for point in self.points)

        return hashlib.sha256(route_text.encode("utf-8")).hexdigest()

    def _load_state(self) -> None:

        if not self.state_file.exists():
            self.current_index = 0
            return

        try:
            with self.state_file.open(
                "r",
                encoding="utf-8",
            ) as handle:
                state = json.load(handle)

        except (OSError, json.JSONDecodeError):
            self.current_index = 0
            return

        if not isinstance(
            state,
            dict,
        ):
            self.current_index = 0
            return

        stored_signature = state.get("route_signature")

        if stored_signature != self.route_signature:
            self.current_index = 0
            return

        stored_index = state.get(
            "current_index",
            0,
        )

        try:
            stored_index = int(stored_index)

        except (TypeError, ValueError):
            stored_index = 0

        self.current_index = max(
            0,
            min(
                stored_index,
                self.total_jumps,
            ),
        )

    def _save_state(self) -> None:

        state = {
            "route_file": str(self.route_file),
            "route_signature": self.route_signature,
            "current_index": self.current_index,
            "total_jumps": self.total_jumps,
        }

        try:
            self.state_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with self.state_file.open(
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    state,
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

        except OSError as exc:
            raise RouteManagerError(
                "Der Routenfortschritt konnte nicht " f"gespeichert werden: {exc}"
            ) from exc

    # --------------------------------------------------
    # Allgemeine Routeninformationen
    # --------------------------------------------------

    @property
    def start_point(self) -> RoutePoint:
        return self.points[0]

    @property
    def destination_point(self) -> RoutePoint:
        return self.points[-1]

    @property
    def jump_points(self) -> list[RoutePoint]:
        """
        Alle Zielsysteme. Das Startsystem ist nicht enthalten.
        """

        return self.points[1:]

    @property
    def total_jumps(self) -> int:
        return max(
            0,
            len(self.points) - 1,
        )

    @property
    def completed_jumps(self) -> int:
        return self.current_index

    @property
    def remaining_jumps(self) -> int:
        return self.total_jumps - self.completed_jumps

    @property
    def is_completed(self) -> bool:
        return self.current_index >= self.total_jumps

    @property
    def progress_percent(self) -> float:

        if self.total_jumps == 0:
            return 100.0

        return self.completed_jumps / self.total_jumps * 100.0

    @property
    def total_distance(self) -> float:

        return sum(point.distance or 0.0 for point in self.jump_points)

    @property
    def completed_distance(self) -> float:

        completed = self.jump_points[: self.completed_jumps]

        return sum(point.distance or 0.0 for point in completed)

    @property
    def remaining_distance(self) -> float:

        remaining = self.jump_points[self.completed_jumps :]

        return sum(point.distance or 0.0 for point in remaining)

    @property
    def total_fuel_required(self) -> int:

        return sum(point.fuel_used or 0 for point in self.jump_points)

    @property
    def completed_fuel(self) -> int:

        completed = self.jump_points[: self.completed_jumps]

        return sum(point.fuel_used or 0 for point in completed)

    @property
    def remaining_fuel(self) -> int:

        remaining = self.jump_points[self.completed_jumps :]

        return sum(point.fuel_used or 0 for point in remaining)

    @property
    def jump_duration_minutes(self) -> int:
        """
        Geplante Dauer eines Carrier-Sprungs.
        """

        return JUMP_DURATION_MINUTES

    @property
    def total_duration_minutes(self) -> int:
        """
        Voraussichtliche Dauer der gesamten Route.
        """

        return self.total_jumps * self.jump_duration_minutes

    @property
    def completed_duration_minutes(self) -> int:
        """
        Geplante Zeit der bereits abgeschlossenen Sprünge.
        """

        return self.completed_jumps * self.jump_duration_minutes

    @property
    def remaining_duration_minutes(self) -> int:
        """
        Voraussichtliche Restdauer der Route.
        """

        return self.remaining_jumps * self.jump_duration_minutes

    @property
    def required_start_fuel(self) -> int | None:

        if self.start_point.restock_fuel is not None:
            return self.start_point.restock_fuel

        if self.total_fuel_required > 0:
            return self.total_fuel_required

        return None

    # --------------------------------------------------
    # Aktueller Sprung
    # --------------------------------------------------

    def get_current_jump(
        self,
    ) -> RoutePoint | None:

        if self.is_completed:
            return None

        return self.jump_points[self.current_index]

    def get_current_target(
        self,
    ) -> str | None:

        jump = self.get_current_jump()

        if jump is None:
            return None

        return jump.system

    def get_remaining_targets(
        self,
    ) -> list[str]:

        return [point.system for point in self.jump_points[self.current_index :]]

    # --------------------------------------------------
    # Fortschritt verändern
    # --------------------------------------------------

    def mark_current_completed(self) -> None:
        """
        Markiert genau einen erfolgreich ausgeführten Sprung
        als abgeschlossen.
        """

        if self.is_completed:
            return

        self.current_index += 1
        self._save_state()

    def reset(self) -> None:
        """
        Setzt den Fortschritt an den Anfang der Route.
        """

        self.current_index = 0
        self._save_state()

    def set_progress(
        self,
        completed_jumps: int,
    ) -> None:
        """
        Setzt den Fortschritt gezielt, beispielsweise für Tests.
        """

        completed_jumps = int(completed_jumps)

        if not (0 <= completed_jumps <= self.total_jumps):
            raise RouteManagerError(
                "Ungültiger Fortschritt: "
                f"{completed_jumps}. "
                "Erlaubt sind Werte "
                f"zwischen 0 und {self.total_jumps}."
            )

        self.current_index = completed_jumps
        self._save_state()

    # --------------------------------------------------

    def get_route_info(
        self,
    ) -> dict[str, object]:
        """
        Liefert alle wichtigen Werte für die GUI.
        """

        current_jump = self.get_current_jump()

        return {
            "file": self.route_file,
            "route_format": self.route_format,
            "start_system": self.start_point.system,
            "destination_system": self.destination_point.system,
            "total_jumps": self.total_jumps,
            "completed_jumps": self.completed_jumps,
            "remaining_jumps": self.remaining_jumps,
            "progress_percent": self.progress_percent,
            "total_distance": self.total_distance,
            "completed_distance": self.completed_distance,
            "remaining_distance": self.remaining_distance,
            "total_fuel_required": self.total_fuel_required,
            "completed_fuel": self.completed_fuel,
            "remaining_fuel": self.remaining_fuel,
            "jump_duration_minutes": (self.jump_duration_minutes),
            "total_duration_minutes": (self.total_duration_minutes),
            "completed_duration_minutes": (self.completed_duration_minutes),
            "remaining_duration_minutes": (self.remaining_duration_minutes),
            "required_start_fuel": (self.required_start_fuel),
            "current_jump": current_jump,
            "is_completed": self.is_completed,
        }
