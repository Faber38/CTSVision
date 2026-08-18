from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

APP_NAME = "CTSVision – Manueller XYZ-Routenplaner"
DEFAULT_JUMP = 495.0
DEFAULT_MAX_JUMP = 500.0
CTSV_HEADERS = [
    "System Name", "Distance", "Distance Remaining", "Tritium in tank",
    "Tritium in market", "Fuel Used", "Icy Ring", "Pristine", "Restock Tritium",
]


def distance(a, b):
    return math.sqrt(sum((b[i] - a[i]) ** 2 for i in range(3)))


def point_towards(start, target, step):
    total = distance(start, target)
    if total == 0:
        return target, 0.0
    move = min(step, total)
    f = move / total
    return tuple(start[i] + (target[i] - start[i]) * f for i in range(3)), move


def tritium_usage(distance_ly, used_capacity, tank_before):
    """
    Berechnet den Tritiumverbrauch eines Fleet-Carrier-Sprungs.

    Formel:
        5 + distance * (used_capacity + tank_before + 25000) / 200000

    Das Ergebnis wird wie in bekannten Carrier-Rechnern auf ganze Tonnen
    gerundet. Die Formel wurde zusätzlich mit realen CTSVision-Messwerten
    gegengeprüft.
    """
    value = 5 + (
        float(distance_ly)
        * (float(used_capacity) + float(tank_before) + 25000.0)
        / 200000.0
    )
    return int(round(value))


class ManualRoutePlanner(QDialog):
    route_created = Signal(str)

    def __init__(self, parent=None, *, dark_mode=False, default_directory=None):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.default_directory = Path(default_directory).expanduser() if default_directory else Path.home()
        self.route = []
        self.target = None
        self.next_point = None
        self.project_path = None

        self.setWindowTitle(APP_NAME)
        self.resize(1040, 760)
        self.setMinimumSize(940, 680)
        self._build_ui()
        self.set_dark_mode(dark_mode)
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        orient = QGroupBox("Orientierung in der Elite-Galaxiekarte")
        ol = QHBoxLayout(orient)
        ol.setContentsMargins(10, 6, 10, 6)
        lbl = QLabel(
            "<b>2D-Kartenebene: X / Z</b> &nbsp;&nbsp; "
            "X = links ↔ rechts &nbsp;&nbsp; Z = unten ↕ oben &nbsp;&nbsp; "
            "Y = Schicht / Höhe im 3D-Raum"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)
        ol.addWidget(lbl, 1)
        layers = QLabel("<b>Y-Schichten</b><br>──────<br>──────<br>──────")
        layers.setTextFormat(Qt.TextFormat.RichText)
        layers.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol.addWidget(layers)
        root.addWidget(orient)

        box = QGroupBox("1. Start und Ziel")
        g = QGridLayout(box)
        self.start_name = QLineEdit(); self.start_x = QLineEdit(); self.start_y = QLineEdit(); self.start_z = QLineEdit()
        self.target_x = QLineEdit(); self.target_y = QLineEdit(); self.target_z = QLineEdit()
        self.jump_distance = QLineEdit(str(DEFAULT_JUMP)); self.max_jump = QLineEdit(str(DEFAULT_MAX_JUMP))
        self.used_capacity = QLineEdit()
        self.tritium_tank = QLineEdit("1000")
        self.tritium_market = QLineEdit()
        g.addWidget(QLabel("Startsystem"),0,0); g.addWidget(self.start_name,0,1,1,5)
        g.addWidget(QLabel("Start X ↔"),1,0); g.addWidget(self.start_x,1,1)
        g.addWidget(QLabel("Y Schicht"),1,2); g.addWidget(self.start_y,1,3)
        g.addWidget(QLabel("Z ↕"),1,4); g.addWidget(self.start_z,1,5)
        g.addWidget(QLabel("Ziel X ↔"),0,7); g.addWidget(self.target_x,0,8)
        g.addWidget(QLabel("Y Schicht"),0,9); g.addWidget(self.target_y,0,10)
        g.addWidget(QLabel("Z ↕"),0,11); g.addWidget(self.target_z,0,12)
        g.addWidget(QLabel("Soll-Sprungweite"),1,7); g.addWidget(self.jump_distance,1,8); g.addWidget(QLabel("Lj"),1,9)
        g.addWidget(QLabel("Max. Carrier-Sprung"),2,7); g.addWidget(self.max_jump,2,8); g.addWidget(QLabel("Lj"),2,9)

        g.addWidget(QLabel("Carrier-Masse / Used Capacity"),2,10)
        g.addWidget(self.used_capacity,2,11)
        g.addWidget(QLabel("t"),2,12)

        g.addWidget(QLabel("Tritium im Tank"),3,7)
        g.addWidget(self.tritium_tank,3,8)
        g.addWidget(QLabel("t"),3,9)

        g.addWidget(QLabel("Tritium im Lager"),3,10)
        g.addWidget(self.tritium_market,3,11)
        g.addWidget(QLabel("t"),3,12)

        b = QPushButton("Route starten / neu berechnen"); b.clicked.connect(self.start_route); g.addWidget(b,3,0,1,4)
        root.addWidget(box)

        box = QGroupBox("2. Nächster Suchpunkt")
        g = QGridLayout(box)
        self.current_system_label = QLabel("—"); self.remaining_label = QLabel("—")
        self.next_x = QLineEdit("—"); self.next_y = QLineEdit("—"); self.next_z = QLineEdit("—")
        for e in (self.next_x,self.next_y,self.next_z): e.setReadOnly(True)
        self.info_label = QLabel("Noch keine Route gestartet."); self.info_label.setWordWrap(True)
        g.addWidget(QLabel("Aktuelles System:"),0,0); g.addWidget(self.current_system_label,0,1,1,5)
        g.addWidget(QLabel("Soll X ↔"),1,0); g.addWidget(self.next_x,1,1)
        g.addWidget(QLabel("Y Schicht"),1,2); g.addWidget(self.next_y,1,3)
        g.addWidget(QLabel("Z ↕"),1,4); g.addWidget(self.next_z,1,5)
        g.addWidget(QLabel("Rest zum Ziel:"),1,6); g.addWidget(self.remaining_label,1,7)
        g.addWidget(self.info_label,2,0,1,8)
        root.addWidget(box)

        box = QGroupBox("3. Gefundenes reales System")
        g = QGridLayout(box)
        self.found_name=QLineEdit(); self.found_x=QLineEdit(); self.found_y=QLineEdit(); self.found_z=QLineEdit()
        self.check_result=QLabel(""); self.check_result.setWordWrap(True)
        self.check_button=QPushButton("Entfernung prüfen"); self.check_button.clicked.connect(self.check_found)
        self.add_button=QPushButton("System übernehmen + weiter"); self.add_button.clicked.connect(self.add_found)
        g.addWidget(QLabel("Systemname"),0,0); g.addWidget(self.found_name,0,1,1,5); g.addWidget(self.check_button,0,6)
        g.addWidget(QLabel("X ↔"),1,0); g.addWidget(self.found_x,1,1)
        g.addWidget(QLabel("Y Schicht"),1,2); g.addWidget(self.found_y,1,3)
        g.addWidget(QLabel("Z ↕"),1,4); g.addWidget(self.found_z,1,5); g.addWidget(self.add_button,1,6)
        g.addWidget(self.check_result,2,0,1,7)
        root.addWidget(box)

        box = QGroupBox("4. Manuelle Route")
        vl = QVBoxLayout(box)
        self.table=QTableWidget(0,10)
        self.table.setHorizontalHeaderLabels([
            "#","System","X ↔","Y Schicht","Z ↕","Sprung",
            "Tritium","Tank danach","Nachtanken","Rest zum Ziel"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0,40); self.table.setColumnWidth(1,235)
        self.table.setColumnWidth(5,90); self.table.setColumnWidth(6,75)
        self.table.setColumnWidth(7,90); self.table.setColumnWidth(8,95)
        vl.addWidget(self.table)
        self.tritium_summary_label = QLabel("Tritiumberechnung: noch keine Route.")
        self.tritium_summary_label.setWordWrap(True)
        vl.addWidget(self.tritium_summary_label)
        root.addWidget(box,1)

        buttons=QHBoxLayout()
        for text, fn in [
            ("Projekt laden", self.load_project), ("Projekt speichern unter…", self.save_project_as),
            ("Letzten Punkt entfernen", self.remove_last), ("Neue Route", self.new_route)
        ]:
            btn=QPushButton(text); btn.clicked.connect(fn); buttons.addWidget(btn)
        buttons.addStretch()
        self.export_button=QPushButton("Route an CTSVision übergeben"); self.export_button.clicked.connect(self.export_to_ctsvision)
        buttons.addWidget(self.export_button); root.addLayout(buttons)
        self.status_label=QLabel("Bereit."); root.addWidget(self.status_label)

        # Änderungen an Masse/Tritium sofort in der Routentabelle nachführen.
        for edit in (self.used_capacity, self.tritium_tank, self.tritium_market):
            edit.editingFinished.connect(self._refresh)

    def set_dark_mode(self, enabled):
        self.dark_mode = enabled
        if enabled:
            self.setStyleSheet("""
                QDialog,QWidget{background:#151a20;color:#d7dee7;font-size:10pt}
                QGroupBox{border:1px solid #3b4652;border-radius:7px;margin-top:10px;padding-top:10px;font-weight:700;background:#1d232a}
                QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px;color:#b9c7d4}
                QLineEdit,QTableWidget{background:#10151a;color:#dbe3eb;border:1px solid #465563;border-radius:4px;padding:4px}
                QPushButton{min-height:28px;padding:5px 10px;border:1px solid #465564;border-radius:6px;background:#222a32;color:#dbe3eb}
                QPushButton:hover{background:#2b3945} QPushButton:disabled{color:#6f7b86;background:#1d2328}
            """)
        else:
            self.setStyleSheet("")

    def _float(self, edit, label):
        raw=edit.text().strip().replace(",", ".")
        try: return float(raw)
        except ValueError as exc: raise ValueError(f"{label}: '{edit.text()}' ist keine gültige Zahl.") from exc

    def _xyz(self, ex, ey, ez, prefix):
        return (self._float(ex,f"{prefix} X"), self._float(ey,f"{prefix} Y"), self._float(ez,f"{prefix} Z"))

    def current_point(self):
        if not self.route: return None
        e=self.route[-1]; return (float(e["x"]),float(e["y"]),float(e["z"]))

    def _calculate_next(self):
        if not self.route or self.target is None: self.next_point=None; return
        self.next_point,_=point_towards(self.current_point(),self.target,self._float(self.jump_distance,"Soll-Sprungweite"))

    def start_route(self):
        try:
            name=self.start_name.text().strip()
            if not name: raise ValueError("Bitte einen Startsystem-Namen eingeben.")
            start=self._xyz(self.start_x,self.start_y,self.start_z,"Start")
            target=self._xyz(self.target_x,self.target_y,self.target_z,"Ziel")
            jump=self._float(self.jump_distance,"Soll-Sprungweite"); max_jump=self._float(self.max_jump,"Maximaler Sprung")
            used_capacity=self._float(self.used_capacity,"Carrier-Masse / Used Capacity")
            tank=self._float(self.tritium_tank,"Tritium im Tank")
            market=self._float(self.tritium_market,"Tritium im Lager")
            if jump<=0 or max_jump<=0: raise ValueError("Sprungweiten müssen größer als 0 sein.")
            if jump>max_jump: raise ValueError("Soll-Sprungweite darf nicht größer als der maximale Carrier-Sprung sein.")
            if used_capacity < 0: raise ValueError("Carrier-Masse / Used Capacity darf nicht negativ sein.")
            if not (0 <= tank <= 1000): raise ValueError("Tritium im Tank muss zwischen 0 und 1000 t liegen.")
            if market < 0: raise ValueError("Tritium im Lager darf nicht negativ sein.")
            if distance(start,target)==0: raise ValueError("Start und Ziel sind identisch.")
        except ValueError as exc:
            QMessageBox.critical(self,APP_NAME,str(exc)); return
        if self.route and QMessageBox.question(self,APP_NAME,"Aktuelle Route verwerfen?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes: return
        self.target=target; self.route=[{"name":name,"x":start[0],"y":start[1],"z":start[2],"jump":0.0}]
        self.project_path=None; self._clear_found(); self._refresh(); self._autosave(); self.status_label.setText("Route gestartet.")

    def check_found(self):
        if not self.route or self.target is None:
            QMessageBox.information(self,APP_NAME,"Bitte zuerst eine Route starten."); return None
        try:
            name=self.found_name.text().strip()
            if not name: raise ValueError("Bitte den Namen des gefundenen Systems eingeben.")
            p=self._xyz(self.found_x,self.found_y,self.found_z,"Gefunden")
            max_jump=self._float(self.max_jump,"Maximaler Sprung")
        except ValueError as exc:
            QMessageBox.critical(self,APP_NAME,str(exc)); return None
        cur=self.current_point(); d=distance(cur,p); rem=distance(p,self.target); old=distance(cur,self.target)
        off=distance(p,self.next_point) if self.next_point is not None else 0.0
        if d>max_jump+1e-9:
            self.check_result.setText(f"✗ ZU WEIT: {d:.3f} Lj — maximal erlaubt: {max_jump:.3f} Lj"); return None
        progress=rem<old; extra="" if progress else "  ACHTUNG: Das System liegt nicht näher am Ziel."
        self.check_result.setText(f"✓ Sprung möglich: {d:.3f} Lj | Abweichung vom Sollpunkt: {off:.3f} Lj | Rest zum Ziel: {rem:.3f} Lj{extra}")
        return {"name":name,"x":p[0],"y":p[1],"z":p[2],"jump":d,"progress":progress}

    def add_found(self):
        item=self.check_found()
        if item is None: return
        if not item["progress"] and QMessageBox.question(self,APP_NAME,"System liegt nicht näher am Ziel. Trotzdem übernehmen?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes: return
        self.route.append({k:item[k] for k in ("name","x","y","z","jump")})
        self._clear_found(); self._refresh(); self._autosave(); self.status_label.setText(f"{item['name']} übernommen. Nächster Suchpunkt berechnet.")

    def _clear_found(self):
        for e in (self.found_name,self.found_x,self.found_y,self.found_z): e.clear()
        self.check_result.clear()

    def _simulate_tritium(self):
        """
        Simuliert den Tritiumverbrauch über die aktuell geplante Route.

        Used Capacity bleibt zwischen Sprüngen gleich. Erst wenn Tritium aus
        dem Carrier-Lager in den Tank übertragen wird, sinkt Used Capacity
        um genau diese Menge. Da der Tank um dieselbe Menge steigt, bleibt
        die Summe Used Capacity + Tank durch das reine Nachtanken zunächst
        unverändert.
        """
        if not self.route:
            return [], None

        try:
            used_capacity = self._float(
                self.used_capacity,
                "Carrier-Masse / Used Capacity",
            )
            tank = self._float(
                self.tritium_tank,
                "Tritium im Tank",
            )
            market = self._float(
                self.tritium_market,
                "Tritium im Lager",
            )
        except ValueError:
            return [], None

        result = []
        total_used = 0
        warning = None

        # Startsystem
        result.append({
            "fuel_used": 0,
            "tank_after": int(round(tank)),
            "market_after": int(round(market)),
            "restock": 0,
            "used_capacity": used_capacity,
        })

        for idx, entry in enumerate(self.route[1:], start=1):
            jump_distance = float(entry["jump"])
            restock = 0

            # Zuerst den Verbrauch mit dem aktuellen Zustand bestimmen.
            needed = tritium_usage(
                jump_distance,
                used_capacity,
                tank,
            )

            # Falls der Tank nicht reicht, wird automatisch bis maximal
            # 1000 t aus dem Lager nachgefüllt.
            if tank < needed:
                desired = 1000.0 - tank
                restock = min(desired, market)

                tank += restock
                market -= restock
                used_capacity -= restock

                needed = tritium_usage(
                    jump_distance,
                    used_capacity,
                    tank,
                )

            if tank < needed:
                warning = (
                    f"Ab Sprung {idx} reicht das verfügbare Tritium nicht mehr aus. "
                    f"Benötigt: {needed} t, Tank: {tank:.0f} t, Lager: {market:.0f} t."
                )
                result.append({
                    "fuel_used": needed,
                    "tank_after": max(0, int(round(tank))),
                    "market_after": int(round(market)),
                    "restock": int(round(restock)),
                    "used_capacity": used_capacity,
                    "insufficient": True,
                })
                break

            tank -= needed
            total_used += needed

            result.append({
                "fuel_used": needed,
                "tank_after": int(round(tank)),
                "market_after": int(round(market)),
                "restock": int(round(restock)),
                "used_capacity": used_capacity,
                "insufficient": False,
            })

        summary = {
            "total_used": total_used,
            "tank_after": int(round(tank)),
            "market_after": int(round(market)),
            "used_capacity_after": int(round(used_capacity)),
            "warning": warning,
        }

        return result, summary

    def _refresh(self):
        self.table.setRowCount(0)
        if not self.route or self.target is None:
            self.current_system_label.setText("—"); self.remaining_label.setText("—")
            for e in (self.next_x,self.next_y,self.next_z): e.setText("—")
            self.info_label.setText("Noch keine Route gestartet.")
            self.tritium_summary_label.setText("Tritiumberechnung: noch keine Route.")
            self.add_button.setEnabled(False); self.export_button.setEnabled(False); return
        self._calculate_next(); cur=self.current_point(); rem=distance(cur,self.target)
        self.current_system_label.setText(str(self.route[-1]["name"])); self.remaining_label.setText(f"{rem:.3f} Lj")
        if self.next_point is not None:
            self.next_x.setText(f"{self.next_point[0]:.3f}"); self.next_y.setText(f"{self.next_point[1]:.3f}"); self.next_z.setText(f"{self.next_point[2]:.3f}")
            step=distance(cur,self.next_point)
            self.info_label.setText(f"Suche zuerst X/Z auf der Kartenebene, dann Y als Schicht. Theoretischer nächster Schritt: {step:.3f} Lj.")
        tritium_rows, tritium_summary = self._simulate_tritium()

        for idx,e in enumerate(self.route,1):
            p=(float(e["x"]),float(e["y"]),float(e["z"])); remaining=distance(p,self.target)

            tritium = tritium_rows[idx-1] if idx-1 < len(tritium_rows) else None

            if tritium is None:
                fuel_text = "—"
                tank_text = "—"
                restock_text = "—"
            else:
                fuel_text = "Start" if idx == 1 else f"{tritium['fuel_used']} t"
                tank_text = f"{tritium['tank_after']} t"
                restock_amount = int(tritium.get("restock", 0))
                restock_text = f"{restock_amount} t" if restock_amount > 0 else "—"

            row=self.table.rowCount(); self.table.insertRow(row)
            vals=[
                str(idx),str(e["name"]),
                f"{float(e['x']):.3f}",f"{float(e['y']):.3f}",f"{float(e['z']):.3f}",
                f"{float(e['jump']):.3f} Lj",
                fuel_text,tank_text,restock_text,
                f"{remaining:.3f} Lj"
            ]
            for c,v in enumerate(vals): self.table.setItem(row,c,QTableWidgetItem(v))

        if tritium_summary is None:
            self.tritium_summary_label.setText(
                "Tritiumberechnung: Bitte Carrier-Masse, Tank und Lager vollständig eingeben."
            )
        else:
            summary_text = (
                f"Geschätzter Tritiumverbrauch: {tritium_summary['total_used']} t   |   "
                f"Tank nach Route: {tritium_summary['tank_after']} t   |   "
                f"Tritium im Lager: {tritium_summary['market_after']} t   |   "
                f"Used Capacity danach: {tritium_summary['used_capacity_after']} t"
            )
            if tritium_summary["warning"]:
                summary_text += "\n⚠ " + str(tritium_summary["warning"])
            self.tritium_summary_label.setText(summary_text)

        self.add_button.setEnabled(True); self.export_button.setEnabled(len(self.route)>=2)

    def project_data(self):
        return {
            "app":APP_NAME,
            "version":2,
            "saved_at":datetime.now().isoformat(timespec="seconds"),
            "target":list(self.target) if self.target else None,
            "jump_distance":self.jump_distance.text(),
            "max_jump":self.max_jump.text(),
            "used_capacity":self.used_capacity.text(),
            "tritium_tank":self.tritium_tank.text(),
            "tritium_market":self.tritium_market.text(),
            "route":self.route,
        }

    def _autosave(self):
        if not self.route: return
        path=self.project_path or (self.default_directory/"manual_xyz_route_autosave.json")
        try:
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(self.project_data(),ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as exc: self.status_label.setText(f"Autosave fehlgeschlagen: {exc}")

    def save_project_as(self):
        if not self.route: return
        filename,_=QFileDialog.getSaveFileName(self,"Routenprojekt speichern",str(self.default_directory/"manual_xyz_route.json"),"JSON (*.json)")
        if filename: self.project_path=Path(filename); self._autosave(); self.status_label.setText(f"Projekt gespeichert: {self.project_path.name}")

    def load_project(self):
        filename,_=QFileDialog.getOpenFileName(self,"Routenprojekt laden",str(self.default_directory),"JSON (*.json)")
        if not filename: return
        try:
            data=json.loads(Path(filename).read_text(encoding="utf-8")); self.route=data["route"]; self.target=tuple(map(float,data["target"])); self.project_path=Path(filename)
            self.jump_distance.setText(str(data.get("jump_distance",DEFAULT_JUMP))); self.max_jump.setText(str(data.get("max_jump",DEFAULT_MAX_JUMP)))
            self.used_capacity.setText(str(data.get("used_capacity","")))
            self.tritium_tank.setText(str(data.get("tritium_tank","1000")))
            self.tritium_market.setText(str(data.get("tritium_market","")))
            first=self.route[0]; self.start_name.setText(str(first["name"])); self.start_x.setText(str(first["x"])); self.start_y.setText(str(first["y"])); self.start_z.setText(str(first["z"]))
            self.target_x.setText(str(self.target[0])); self.target_y.setText(str(self.target[1])); self.target_z.setText(str(self.target[2])); self._clear_found(); self._refresh()
        except Exception as exc: QMessageBox.critical(self,APP_NAME,f"Projekt konnte nicht geladen werden.\n\n{exc}")

    def remove_last(self):
        if len(self.route)>1: self.route.pop(); self._refresh(); self._autosave()

    def new_route(self):
        if self.route and QMessageBox.question(self,APP_NAME,"Aktuelle Route verwerfen?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes: return
        self.route=[]; self.target=None; self.next_point=None; self.project_path=None; self._clear_found(); self._refresh(); self.status_label.setText("Neue manuelle Route.")

    def export_to_ctsvision(self):
        if len(self.route)<2 or self.target is None:
            QMessageBox.information(self,APP_NAME,"Mindestens Startsystem und ein Sprungziel werden benötigt."); return
        filename,_=QFileDialog.getSaveFileName(self,"CTSVision-Route speichern",str(self.default_directory/"manual_route.csv"),"CSV (*.csv)")
        if not filename: return
        route_path=Path(filename)
        try:
            route_path.parent.mkdir(parents=True,exist_ok=True)
            with route_path.open("w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(CTSV_HEADERS)

                # WICHTIG:
                # Der RouteManager von CTSVision erwartet in der ersten
                # Datenzeile das aktuelle Startsystem. Erst alle folgenden
                # Zeilen gelten als tatsächliche Sprungziele.
                #
                # Deshalb wird die komplette manuelle Route exportiert,
                # einschließlich self.route[0].
                tritium_rows, tritium_summary = self._simulate_tritium()

                if tritium_summary is None:
                    raise ValueError(
                        "Carrier-Masse, Tritium im Tank und Tritium im Lager "
                        "müssen für den Export vollständig angegeben werden."
                    )

                if tritium_summary.get("warning"):
                    answer = QMessageBox.question(
                        self,
                        APP_NAME,
                        "Die Tritiumsimulation meldet:\n\n"
                        + str(tritium_summary["warning"])
                        + "\n\nRoute trotzdem exportieren?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if answer != QMessageBox.StandardButton.Yes:
                        return

                for idx,e in enumerate(self.route):
                    p=(float(e["x"]),float(e["y"]),float(e["z"]))
                    remaining=distance(p,self.target)

                    jump_distance = 0.0 if idx == 0 else float(e["jump"])
                    tri = tritium_rows[idx] if idx < len(tritium_rows) else None

                    tank_after = tri["tank_after"] if tri else ""
                    market_after = tri["market_after"] if tri else ""
                    fuel_used = tri["fuel_used"] if (tri and idx > 0) else ""
                    restock = "Yes" if tri and int(tri.get("restock", 0)) > 0 else "No"

                    w.writerow([
                        str(e["name"]),
                        repr(jump_distance),
                        repr(float(remaining)),
                        tank_after,
                        market_after,
                        fuel_used,
                        "No",
                        "No",
                        restock,
                    ])

            self.route_created.emit(str(route_path))
            self.status_label.setText(f"CTSVision-Route erstellt: {route_path.name}")
            QMessageBox.information(
                self,
                APP_NAME,
                f"Route wurde erstellt und an CTSVision übergeben.\n\n"
                f"Startsystem: {self.route[0]['name']}\n"
                f"Sprungziele: {len(self.route)-1}\n"
                f"Datei: {route_path}"
            )
        except Exception as exc:
            QMessageBox.critical(self,APP_NAME,f"Route konnte nicht erstellt werden.\n\n{exc}")
