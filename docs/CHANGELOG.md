# Changelog

Alle wichtigen Änderungen an CTSVision werden in dieser Datei dokumentiert.

Dieses Projekt orientiert sich an den Empfehlungen von
Keep a Changelog sowie Semantic Versioning.

---
## Version 1.0.1

### Verbesserungen

- Neue konfigurierbare Tritium-Position.
- Die Auswahl der Tritiumzeile erfolgt jetzt über den orangefarbenen Auswahlbalken statt über den kleinen Auswahlpfeil.
- Dadurch wurde die Kompatibilität mit unterschiedlichen Auflösungen und UI-Skalierungen deutlich verbessert.

### Verbesserungen

- Neue Einstellung **„Tritium-Position“** ergänzt.
- Die Tritiumsuche kann jetzt an einer frei wählbaren Position innerhalb der Transferliste beginnen.
- Dadurch werden auch sehr lange Warenlisten deutlich schneller durchsucht.
- Nach der eingestellten Startposition sucht CTSVision zusätzlich automatisch einige Zeilen oberhalb und unterhalb nach dem Eintrag **TRITIUM**.
- Verbesserte Kompatibilität mit unterschiedlichen Fleet-Carrier-Konfigurationen.

---

## [1.0.0] - 2026-07-21

### Hinzugefügt

- Erste stabile Veröffentlichung von CTSVision
- Vision-basierte Menüerkennung
- Vision Wizard zum Erstellen und Prüfen von Referenzbildern
- OCR-Auswertung des Carrier-Tankfüllstands
- Automatische Fleet-Carrier-Sprungsteuerung
- Automatisches Betanken des Fleet Carriers mit Tritium
- Tankfunktion mit integriertem Testmodus
- Paralleler Tankvorgang während der Sprung-Abkühlzeit
- Journal-Auswertung zur Ablaufsteuerung
- Speicherung und Fortsetzung von Routen
- Grafische Benutzeroberfläche auf Basis von PySide6
- Tankstatus-Anzeige in der Benutzeroberfläche
- Installations- und Startskripte für Linux
- Deutsche Dokumentation

### Unterstützte Plattformen

- Linux
- Pop!_OS (getestet)
- X11

---

## Zukünftig geplant

- Unterstützung mehrerer Schiffprofile
- Erweiterte Vision-Profile
- Weitere Komfortfunktionen