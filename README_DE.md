# CTSVision

> **Computer-Vision-, OCR- und Journal-Framework für Elite Dangerous**

[🇩🇪 Deutsch](README_DE.md) | [🇬🇧 English](README.md)

## Was ist CTSVision?

CTSVision ist ein Open-Source-Projekt zur Analyse der Benutzeroberfläche von **Elite Dangerous**.

![CTSVision Banner](docs/images/ctsvision_banner.png)

Das Framework kombiniert **Computer Vision**, **OCR (PaddleOCR)** und **Journal-Auswertung**, um Spielzustände zuverlässig zu erkennen.

### Funktionen
- Vision-basierte Menüerkennung
- OCR (PaddleOCR)
- Journal-Monitor
- Vision Wizard
- Referenzbildverwaltung
- Debug-Werkzeuge
- Native Linux-Unterstützung
- Modulare Architektur

# 🚀 Quick Start

## 1. Repository herunterladen

```bash
git clone https://github.com/Faber38/CTSVision.git
cd CTSVision
```

## 2. Installation

Führe das Installationsskript aus:

```bash
chmod +x install.sh start.sh
./install.sh
```

Das Skript erstellt automatisch:

- die Python Virtual Environment
- installiert alle benötigten Python-Pakete
- richtet CTSVision für den ersten Start ein

## 3. CTSVision starten

Nach erfolgreicher Installation genügt zukünftig:

```bash
./start.sh
```

Das Startskript

- aktiviert automatisch die Python-Umgebung,
- prüft, ob **Elite Dangerous** bereits läuft,
- und startet anschließend CTSVision.

---

# 👁 Erster Start

Vor der ersten Verwendung sollten mit dem **Vision Wizard** Referenzbilder für die eigene Bildschirmauflösung erstellt werden.

Eine gute Qualität der Referenzbilder ist entscheidend für eine zuverlässige Bilderkennung.

## Empfehlungen

- Referenzbilder immer **so klein wie möglich und nur so groß wie nötig** erstellen.
- Nur statische Elemente wie Menüs, Symbole oder Schaltflächen aufnehmen.
- Sterne, Nebel, Planeten oder andere dynamische Hintergründe vermeiden.
- Nach Änderungen der Bildschirmauflösung oder UI-Skalierung neue Referenzbilder erstellen.
- Die erzeugten Referenzbilder anschließend mit dem Vision Wizard testen.

## Projektphilosophie

CTSVision trifft keine unsicheren Entscheidungen.

**Robustheit vor Geschwindigkeit.**

## Roadmap
### Version 1.5
- Vision Wizard
- OCR
- Journal Monitor
- Tank Wizard
- Workspace-Schutz

![CTSVision Banner](docs/images/Haupt.png)

### Version 2.0
- Mehrsprachigkeit
- Windows-Unterstützung
- Plugin-System

GNU GPL v3.0

Entwickelt von **CMDR Faber38**
