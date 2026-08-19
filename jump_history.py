from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app_paths import CARRIER_HISTORY_FILE


@dataclass
class JumpHistoryRecord:
    """
    Roh- und Auswertedaten eines tatsächlich ausgeführten Carrier-Sprungs.

    Die CSV ist bewusst als Langzeit-Historie gedacht. Unbekannte Werte
    werden leer gespeichert und nicht künstlich geschätzt.
    """

    timestamp: str
    route_file: str
    jump_number: int
    from_system: str
    to_system: str
    distance_ly: float | None
    planned_fuel: int | None

    capacity_before_jump: int | None
    capacity_maximum: int | None

    tank_before_jump: int | None
    tank_after_jump: int | None
    tank_capacity: int | None

    actual_fuel_used: int | None
    deviation_from_plan: int | None

    refueled_after_jump: bool | None
    inferred_refuel_before_jump: int | None
    tank_read_count: int | None


class JumpHistory:
    """
    Verwaltet die dauerhafte CTSVision Carrier-/Tritium-Historie.

    Standarddatei:
        logs/carrier_history.csv
    """

    FIELDNAMES = [
        "Zeit",
        "Route",
        "Sprung",
        "Von System",
        "Nach System",
        "Distanz Lj",
        "Verbrauch geplant t",
        "Used Capacity vor Sprung t",
        "Capacity Maximum t",
        "Tank vor Sprung t",
        "Tank nach Sprung t",
        "Tank Maximum t",
        "Verbrauch IST t",
        "Abweichung t",
        "Nachgetankt nach Sprung",
        "Ermitteltes Nachtanken vor Sprung t",
        "Tank OCR Messungen",
    ]

    def __init__(self, path: str | Path = CARRIER_HISTORY_FILE) -> None:
        self.path = Path(path)

    @staticmethod
    def now_timestamp() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _bool_to_text(value: bool | None) -> str:
        if value is None:
            return ""
        return "Ja" if value else "Nein"

    @staticmethod
    def _optional(value) -> str:
        if value is None:
            return ""
        return str(value)

    def append(self, record: JumpHistoryRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.path.exists() or self.path.stat().st_size == 0

        row = {
            "Zeit": record.timestamp,
            "Route": record.route_file,
            "Sprung": record.jump_number,
            "Von System": record.from_system,
            "Nach System": record.to_system,
            "Distanz Lj": (
                "" if record.distance_ly is None else f"{record.distance_ly:.3f}"
            ),
            "Verbrauch geplant t": self._optional(record.planned_fuel),
            "Used Capacity vor Sprung t": self._optional(
                record.capacity_before_jump
            ),
            "Capacity Maximum t": self._optional(record.capacity_maximum),
            "Tank vor Sprung t": self._optional(record.tank_before_jump),
            "Tank nach Sprung t": self._optional(record.tank_after_jump),
            "Tank Maximum t": self._optional(record.tank_capacity),
            "Verbrauch IST t": self._optional(record.actual_fuel_used),
            "Abweichung t": self._optional(record.deviation_from_plan),
            "Nachgetankt nach Sprung": self._bool_to_text(
                record.refueled_after_jump
            ),
            "Ermitteltes Nachtanken vor Sprung t": self._optional(
                record.inferred_refuel_before_jump
            ),
            "Tank OCR Messungen": self._optional(record.tank_read_count),
        }

        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=self.FIELDNAMES,
                delimiter=";",
            )

            if write_header:
                writer.writeheader()

            writer.writerow(row)

    def latest_for_route(self, route_file: str | Path) -> dict[str, str] | None:
        """
        Liefert den letzten gespeicherten Datensatz derselben Routendatei.

        Das wird genutzt, um bei Folgesprüngen den Tankstand vor dem
        nächsten Sprung aus dem vorherigen Nach-Sprung-Wert und einer
        eventuellen Capacity-Änderung abzuleiten.
        """

        if not self.path.exists():
            return None

        wanted = str(Path(route_file).expanduser().resolve())
        latest = None

        try:
            with self.path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=";")

                for row in reader:
                    route_value = str(row.get("Route", "")).strip()

                    try:
                        route_value = str(
                            Path(route_value).expanduser().resolve()
                        )
                    except Exception:
                        pass

                    if route_value == wanted:
                        latest = row

        except (OSError, csv.Error):
            return None

        return latest

    @staticmethod
    def get_int(row: dict[str, str] | None, key: str) -> int | None:
        if not row:
            return None

        raw = str(row.get(key, "")).strip()

        if not raw:
            return None

        try:
            return int(round(float(raw.replace(",", "."))))
        except ValueError:
            return None

    @staticmethod
    def get_bool(row: dict[str, str] | None, key: str) -> bool | None:
        if not row:
            return None

        raw = str(row.get(key, "")).strip().lower()

        if raw in {"ja", "yes", "true", "1"}:
            return True

        if raw in {"nein", "no", "false", "0"}:
            return False

        return None
