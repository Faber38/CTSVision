# Changelog

Alle wichtigen Änderungen an **CTSVision** werden in dieser Datei dokumentiert.

Das Projekt orientiert sich an den Empfehlungen von
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/) und
[Semantic Versioning](https://semver.org/lang/de/).

---

## [1.5.0] - 2026-07-24

### Hinzugefügt

- Erweiterter Vision Wizard zum Erstellen und Prüfen auflösungsabhängiger Referenzbilder.
- Robuste Zustands- und Menüerkennung mit OpenCV Template Matching.
- OCR-Auswertung mit PaddleOCR für Tankfüllstände, Inventar- und Transferansichten.
- Live-Auswertung der Elite-Journaldateien.
- Tank Wizard mit sicherem Prüfmodus.
- Schutz vor Eingaben auf der falschen Arbeitsfläche.
- Ausführliche Debug- und Diagnoseausgaben.
- Verbesserte Referenzverwaltung und strukturierter Referenzkatalog.
- Überarbeitete deutsche und englische Projektdokumentation.

### Verbessert

- Referenzbilder können deutlich kleiner und gezielter erstellt werden.
- Dynamische Bildbereiche wie Sterne, Nebel und Planeten lassen sich aus den Referenzen heraushalten.
- Die Erkennung verschiedener Bildschirmauflösungen wurde robuster gestaltet.
- Unsichere Spielzustände führen zu einem kontrollierten Stopp.
- Die Menüführung kann nach unerwarteten Zuständen wieder einen definierten Ausgangspunkt suchen.
- Die Tritium-Erkennung in langen Transferlisten wurde beschleunigt.
- Die Erkennung des orangefarbenen Auswahlbalkens ersetzt die frühere Abhängigkeit vom kleinen Auswahlpfeil.
- Projektbeschreibung und Benutzeroberfläche wurden auf **Computer Vision, OCR und Journal-Analyse** ausgerichtet.

### Geändert

- CTSVision wird als modulares **Computer-Vision-, OCR- und Journal-Framework** positioniert.
- Einzelne Funktionen werden als optionale Module auf Basis der gemeinsamen Vision-Komponenten geführt.
- Die Dokumentation verwendet eine neutralere und technisch präzisere Beschreibung des Projekts.

---

## [1.0.1]

### Hinzugefügt

- Konfigurierbare Einstellung **„Tritium-Position“**.
- Frei wählbarer Startpunkt für die Suche innerhalb der Transferliste.
- Zusätzliche Suche in mehreren Zeilen oberhalb und unterhalb der Startposition.

### Verbessert

- Die Tritiumzeile wird über den orangefarbenen Auswahlbalken erkannt.
- Schnellere Verarbeitung langer Warenlisten.
- Verbesserte Kompatibilität mit unterschiedlichen Auflösungen, UI-Skalierungen und Fleet-Carrier-Konfigurationen.

---

## [1.0.0] - 2026-07-21

### Hinzugefügt

- Erste stabile Veröffentlichung von CTSVision.
- Vision-basierte Menü- und Zustandserkennung.
- Vision Wizard zum Erstellen und Prüfen von Referenzbildern.
- OCR-Auswertung des Carrier-Tankfüllstands.
- Modul zur Verarbeitung und Fortsetzung gespeicherter Carrier-Routen.
- Tritium- und Tankmodul mit integriertem Prüfmodus.
- Journal-Auswertung zur Erkennung relevanter Spielereignisse.
- Grafische Benutzeroberfläche auf Basis von PySide6.
- Tankstatus-Anzeige in der Benutzeroberfläche.
- Installations- und Startskripte für Linux.
- Deutsche Projektdokumentation.

### Unterstützte Plattformen

- Linux
- Pop!_OS (getestet)
- X11

---

## Geplant

### Version 2.0

- Mehrsprachige Benutzeroberfläche.
- Sprachabhängige Referenz- und OCR-Profile.
- Windows-Unterstützung.
- Plattformabhängige Linux- und Windows-Backends.
- Plugin-System.
- Erweiterte Vision-Module.
- Zusätzliche Einstellungen und Statistiken.
