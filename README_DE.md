# CTSVision

> **Computer-Vision- und OCR-Framework für Elite Dangerous**

![CTSVision Banner](dosc/images/ctsvision_banner.png)

CTSVision ist ein modulares **Computer-Vision-Framework** für **Elite
Dangerous**.

Der Schwerpunkt liegt auf einer zuverlässigen Zustands- und
Menüerkennung durch Referenzbilder, OCR (PaddleOCR) und der Auswertung
der Elite-Journaldateien.

Das Framework bildet die Grundlage für verschiedene Module und Werkzeuge
rund um Bildverarbeitung, Analyse und Zustandsüberwachung.

------------------------------------------------------------------------

# ✨ Funktionen

-   Vision-basierte Menüerkennung
-   OCR-Texterkennung mit PaddleOCR
-   Live-Auswertung der Elite-Journaldateien
-   Vision Wizard zum Erstellen von Referenzbildern
-   Debug- und Diagnosewerkzeuge
-   Auflösungsabhängige Referenzbilder
-   Native Linux-Unterstützung
-   Python / PySide6 / OpenCV

------------------------------------------------------------------------

# 🏗 Architektur

``` text
Elite Dangerous
        │
        ▼
+----------------------+
|    Vision Engine     |
+----------------------+
        │
 ┌──────┼───────────┐
 │      │           │
OCR   Journal   Referenzen
 │      │           │
 └──────┼───────────┘
        ▼
 Zustandsanalyse
        │
        ▼
 Optionale Module
```

------------------------------------------------------------------------

# 📂 Projektstruktur

``` text
CTSVision/
├── automation_gui.py
├── vision.py
├── vision_wizard.py
├── journal_monitor.py
├── tank_controller.py
├── ocr/
├── references/
├── config/
├── tools/
└── assets/
```

------------------------------------------------------------------------

# 👁 Vision Wizard

Der Vision Wizard erstellt Referenzbilder passend zu deiner
Bildschirmauflösung.

## Best Practice

-   Referenzbilder immer **so klein wie möglich und nur so groß wie
    nötig** erstellen.
-   Nur unveränderliche Elemente wie Menüs, Symbole oder Schaltflächen
    aufnehmen.
-   Dynamische Hintergründe (Sterne, Nebel oder Planeten) möglichst
    vermeiden.

Dadurch bleibt die Bilderkennung deutlich robuster und zuverlässiger.

------------------------------------------------------------------------

# 🔎 OCR

CTSVision verwendet **PaddleOCR** zur Erkennung von:

-   Tankfüllständen
-   Inventar
-   Transferlisten
-   Menütexten
-   Benutzeroberflächen

------------------------------------------------------------------------

# 📖 Journal-Monitor

-   Automatische Erkennung der aktuellen Journaldatei
-   Unterstützt Journalwechsel während des Spiels
-   Echtzeit-Auswertung von Elite-Ereignissen
-   Grundlage für Zustandsanalysen

------------------------------------------------------------------------

# 🛠 Debug-Werkzeuge

-   Screenshot-Aufnahme
-   Template-Matching-Test
-   OCR-Debug
-   Detaillierte Protokollierung
-   Vergleich von Referenzbildern

------------------------------------------------------------------------

# ⚙ Voraussetzungen

-   Linux (getestet unter Pop!\_OS)
-   Python 3.11 oder neuer
-   Elite Dangerous
-   PaddleOCR
-   PySide6
-   OpenCV

------------------------------------------------------------------------

# 🚀 Installation

``` bash
git clone https://github.com/Faber38/CTSVision.git
cd CTSVision

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python automation_gui.py
```

------------------------------------------------------------------------

# ❤️ Projektphilosophie

CTSVision trifft keine unsicheren Entscheidungen.

Kann der aktuelle Spielzustand nicht eindeutig erkannt werden, wird der
Ablauf sicher angehalten.

Beispiele:

-   Menü nicht sicher erkannt → Stopp
-   OCR unsicher → Stopp
-   Referenz fehlt → Stopp
-   Falsche Arbeitsfläche → Stopp

**Robustheit steht immer an erster Stelle.**

------------------------------------------------------------------------

# 🗺 Roadmap

-   ✅ Vision Wizard
-   ✅ OCR-Engine
-   ✅ Journal-Monitor
-   ✅ Tank Wizard
-   ✅ Debug-Werkzeuge
-   ⬜ Route Wizard
-   ⬜ Plugin-System
-   ⬜ Einstellungen
-   ⬜ Statistiken

------------------------------------------------------------------------

# 📄 Lizenz

Dieses Projekt steht unter der **GNU General Public License v3.0**.

Weitere Informationen befinden sich in der Datei **LICENSE**.

------------------------------------------------------------------------

Entwickelt von **CMDR Faber38** für die Elite-Dangerous-Community.

**Fly safe -- o7**
