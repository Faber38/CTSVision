![CTSVision Header](docs/ctsvision_banner.png)

# 🚀 CTSVision

## Automatisierung für Fleet Carrier in Elite Dangerous

**CTSVision** ist ein Linux-Programm zur Automatisierung von
Fleet-Carrier-Abläufen in *Elite Dangerous*.

Im Mittelpunkt stehen **Computer Vision**, **OCR** und die Auswertung
des Elite-Journals. Dadurch werden Spielzustände erkannt und
Entscheidungen anhand des tatsächlichen Bildschirminhalts getroffen --
nicht anhand fester Zeitabläufe.

------------------------------------------------------------------------

# ✨ Funktionen

-   Automatische Fleet-Carrier-Sprünge
-   Vision-basierte Menünavigation
-   OCR-Auswertung des Tritium-Tankfüllstands
-   Automatisches Betanken des Fleet Carriers
-   Tankfunktion separat testbar
-   Statusanzeige des Tankvorgangs
-   Fortsetzen einer gespeicherten Route
-   Ausführung unter Linux (getestet mit Pop!\_OS)

------------------------------------------------------------------------

# 📦 Installation

Erstinstallation:

``` bash
./install.sh
```

Programm starten:

``` bash
./start.sh
```

------------------------------------------------------------------------

# 🖼️ Ersteinrichtung

Vor dem ersten Automatiklauf müssen mit dem **Vision Wizard** die
Referenzbilder erstellt werden.

Da sich Monitore, Auflösungen und Grafikeinstellungen unterscheiden,
geschieht dies einmalig auf jedem Rechner.

------------------------------------------------------------------------

# 💡 Empfehlung

Für die höchste Erkennungsgenauigkeit sollte **immer dasselbe Schiff**
für Carrier-Sprünge und das automatische Betanken verwendet werden.

Unterschiedliche Schiffe besitzen leicht abweichende Cockpitansichten.
Schon kleine Pixelverschiebungen können die Bilderkennung beeinflussen.

Daher wird empfohlen:

-   immer dasselbe Schiff verwenden
-   während eines Automatiklaufs nicht das Schiff wechseln
-   nach einem dauerhaften Schiffwechsel die Referenzbilder neu
    erstellen

------------------------------------------------------------------------

# 🖥️ Systemvoraussetzungen

-   Linux
-   Python 3.11 oder neuer
-   X11
-   Elite Dangerous: Odyssey

------------------------------------------------------------------------

# 🖥️ Empfohlene Arbeitsumgebung

Für einen zuverlässigen Automatikbetrieb wird empfohlen, **Elite Dangerous
allein auf einer eigenen Arbeitsfläche (Virtual Desktop)** auszuführen.

CTSVision arbeitet ausschließlich mit dem sichtbaren Bildschirminhalt von
Elite Dangerous. Änderungen am Fensterinhalt – etwa durch überlagernde
Fenster oder einen Wechsel auf eine andere Anwendung – können die
Bilderkennung beeinträchtigen oder zu einem Abbruch des Automatiklaufs
führen.

Daher wird empfohlen:

- Elite Dangerous als einziges sichtbares Fenster auf dieser Arbeitsfläche
  auszuführen.
- Das Elite-Fenster während des Automatiklaufs nicht zu minimieren oder zu
  überdecken.
- Während eines Automatiklaufs nicht auf andere Anwendungen innerhalb
  derselben Arbeitsfläche zu wechseln.
- Programme wie Browser, Discord oder EDDiscovery auf einer separaten
  Arbeitsfläche zu verwenden.

------------------------------------------------------------------------

# 📝 Feedback

Fehlermeldungen, Screenshots und Logdateien helfen dabei, CTSVision
weiter zu verbessern.

------------------------------------------------------------------------

# 🛣️ Roadmap

## Version 1.0 ✅

-   Vision-System
-   OCR
-   Fleet-Carrier-Sprünge
-   Automatische Tankfunktion
-   Tankstatus
-   Route fortsetzen

## Geplante Erweiterungen

-   Mehrere Schiffprofile
-   Erweiterte Vision-Profile
-   Weitere Komfortfunktionen

------------------------------------------------------------------------

# ❤️ Danke

Vielen Dank für dein Interesse an CTSVision.

**Fly safe, Commander!**

**CMDR Faber38**

------------------------------------------------------------------------

**Version:** 1.0.0\
**Status:** Stable