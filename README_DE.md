# CTSVision

> **Computer-Vision-, OCR- und Journal-Framework für Elite Dangerous**

[🇩🇪 Deutsch](README_DE.md) | [🇬🇧 English](README.md)

## ⚠️ Wichtiger Hinweis – Frontier Developments / Elite Dangerous

CTSVision automatisiert bestimmte Abläufe bei der Nutzung eines Fleet Carriers in **Elite Dangerous**. Die Richtlinien von Frontier Developments untersagen bestimmte Formen der Spielautomatisierung. Fleet-Carrier-Automatisierung kann als Verstoß gegen diese Richtlinien gewertet werden.

**Die Verwendung von CTSVision kann daher zu Verwarnungen, Einschränkungen, einer vorübergehenden Sperre oder anderen Maßnahmen gegen deinen Elite-Dangerous-Account führen.**

CTSVision ist ein unabhängiges Community-Projekt und steht **in keiner Verbindung zu Frontier Developments, wird nicht von Frontier Developments unterstützt und ist nicht von Frontier Developments genehmigt**.

**Die Verwendung dieser Software erfolgt vollständig auf eigenes Risiko.**

Bitte informiere dich vor der Verwendung von CTSVision über die aktuellen **Elite Dangerous Terms of Use, die EULA und den Frontier Code of Conduct**.

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

Tipp: Beim Erstellen der Referenzbilder können die Koordinatenfelder im Vision Wizard mit den Pfeiltasten ↑ ↓ sehr genau verändert werden. Das ist besonders hilfreich, wenn der Auswahlrahmen auf dem Spielbildschirm nicht oder nur schlecht sichtbar ist.

## Empfehlungen

- Referenzbilder immer **so klein wie möglich und nur so groß wie nötig** erstellen.
- Nur statische Elemente wie Menüs, Symbole oder Schaltflächen aufnehmen.
- Sterne, Nebel, Planeten oder andere dynamische Hintergründe vermeiden.
- Nach Änderungen der Bildschirmauflösung oder UI-Skalierung neue Referenzbilder erstellen.
- Die erzeugten Referenzbilder anschließend mit dem Vision Wizard testen.
- Für das automatische Nachtanken sollte möglichst immer **dasselbe Schiff** verwendet werden. Empfehlenswert ist ein Schiff mit **möglichst großem Laderaum**, da die Positionen der Menüs je nach Schiffstyp leicht unterschiedlich sein können.

## Projektphilosophie

CTSVision trifft keine unsicheren Entscheidungen.

**Robustheit vor Geschwindigkeit.**

### Version 1.9.2
✨ Neu
- **Robustere OCR-Erkennung der Carrier-Kapazität.**
  Kann die Carrier-Kapazität / Used Capacity nicht plausibel gelesen werden, versucht CTSVision
  die OCR-Erkennung jetzt bis zu drei Mal. Erst wenn auch der dritte Versuch fehlschlägt,
  wird der Automatiklauf aus Sicherheitsgründen abgebrochen.
- **Neuer kontrollierter Routenstopp „Route stoppen bei...“.**
  Eine laufende Route kann jetzt entweder nach dem aktuell laufenden Sprung oder nach einem
  frei wählbaren noch offenen Sprungziel sauber angehalten werden.
- **Stoppziel direkt aus der aktuellen Route auswählbar.**
  CTSVision zeigt nur noch offene Routenziele an und kennzeichnet das momentan laufende Ziel
  zusätzlich als aktuellen Sprung.
- **Datensicherer Abschluss vor dem Routenstopp.**
  Der ausgewählte Sprung wird vollständig abgeschlossen. CTSVision wartet noch auf den bestätigten
  `CarrierJump`, die Tankprüfung, gegebenenfalls das automatische Nachtanken, die vierminütige
  Carrier-Abkühlzeit und das vollständige Schreiben der Carrier-Historie.
  Erst danach wird kein weiteres Sprungziel gestartet.
- **Stoppziel während der laufenden Route änderbar.**
  Über „Route stoppen bei...“ kann während der Fahrt ein anderes noch offenes Ziel ausgewählt werden.
- **Integrierte Hilfe aktualisiert.**
  Die neue Routenstopp-Funktion, die OCR-Wiederholungsprüfung und der datensichere Ablauf
  sind jetzt in der deutschsprachigen Hilfe dokumentiert.

### Version 1.9.1
✨ Neu
- **Carrier- und Tritium-Historie hinzugefügt.**
  CTSVision protokolliert erfolgreiche Carrier-Sprünge jetzt dauerhaft in einer eigenen Historie.
  Gespeichert werden unter anderem Start- und Zielsystem, Sprungdistanz, Carrier-Masse / Used Capacity,
  Tankstand vor und nach dem Sprung, geplanter und tatsächlicher Tritiumverbrauch sowie die Abweichung.
- **Carrier-Masse / Used Capacity per OCR.**
  Vor dem Öffnen der Galaxiekarte liest CTSVision die aktuelle Carrier-Kapazität automatisch aus dem
  Carrier-Management aus und verwendet den Wert für die Verbrauchsauswertung.
- **Tankmessung für die Historie läuft immer.**
  Der Tritiumtank wird vor dem ersten Routensprung und nach jedem `CarrierJump` per OCR geprüft,
  unabhängig davon, ob das automatische Nachtanken aktiviert ist.
- **Automatisches Nachtanken von der Tankprüfung getrennt.**
  Die Option heißt jetzt **„Carrier bei Bedarf automatisch betanken“**.
  Ist sie deaktiviert, wird der Tankstand weiterhin für die Historie erfasst, es wird jedoch kein Tritium übertragen.
- **Neues Fenster „Carrier-Historie“.**
  Die gesammelten Messwerte können direkt in CTSVision als übersichtliche Tabelle mit Gesamtwerten,
  Durchschnittswerten und Verbrauchsabweichungen angezeigt werden.
- **Sprungdetails per Mausklick.**
  Ein Klick auf eine Tabellenzeile öffnet eine separate Detailansicht mit allen gespeicherten Rohdaten des Sprungs.
- **Backup und Wiederherstellung der Historie.**
  Die komplette Carrier-Historie kann gesichert und später wiederhergestellt werden.
  Vor einer Wiederherstellung wird die vorhandene Historie zusätzlich automatisch gesichert.
- **Excel-Export hinzugefügt.**
  Die Carrier-Historie kann als formatierte `.xlsx`-Datei für Excel oder LibreOffice exportiert werden.
- **Sicheres Löschen der Historie.**
  Das Löschen aller Messdaten ist nur nach zwei aufeinanderfolgenden Sicherheitsabfragen möglich.
- **Manueller Routenplaner mit Historien-Kalibrierung.**
  Der XYZ-Routenplaner kann reale CTSVision-Verbrauchsmessungen aus der Carrier-Historie auswerten
  und die vorhandene Tritium-Prognose damit kalibrieren.
  Mindestens 5 gültige Messungen sind erforderlich; ab 10 Messungen wird die Kalibrierung empfohlen.
  Die ursprüngliche Verbrauchsformel bleibt dabei als Basis erhalten.

### Version 1.9
✨ Neu
- **Integrierte Hilfe hinzugefügt.**
  CTSVision enthält jetzt eine direkt aus dem Hauptfenster aufrufbare deutschsprachige Hilfe.
  Sie beschreibt die wichtigsten Funktionen, Einstellungen, Assistenten, Sicherheitsmechanismen
  und die Bedienung der Routen- und Tankautomatik.
- **Manueller XYZ-Routenplaner hinzugefügt.**
  Carrier-Routen können jetzt auch vollständig von Hand anhand der XYZ-Koordinaten
  der Elite-Galaxiekarte geplant werden.
  Der Routenplaner ist besonders für weit entfernte oder wenig erforschte Gebiete gedacht,
  in denen Systeme möglicherweise noch nicht in EDD oder Spansh bekannt sind.
- **Schrittweise Planung mit realen Systemen.**
  CTSVision berechnet jeweils einen theoretischen Suchpunkt in Richtung Ziel
  (standardmäßig 495 Lj). Anschließend wird in der Galaxiekarte ein reales System
  in der Nähe dieses Punktes gewählt und mit seinen tatsächlichen XYZ-Koordinaten eingetragen.
  Der nächste Suchpunkt wird immer vom tatsächlich gewählten System aus neu berechnet.
- **Prüfung der Carrier-Sprungweite.**
  Vor der Übernahme eines Systems wird kontrolliert, ob die reale Entfernung
  innerhalb der maximalen Carrier-Sprungweite liegt.
- **Direkte Übergabe an CTSVision.**
  Eine fertig geplante manuelle Route kann als CTSVision-kompatible CSV-Datei gespeichert
  und direkt als aktuelle Route übernommen werden.
- **„Route fortsetzen“ deutlich verbessert.**
  Nach einem Abbruch oder unerwarteten Beenden von CTSVision kann jetzt angegeben werden,
  in welchem Routensystem sich der Carrier tatsächlich befindet.
  Das ist besonders wichtig, wenn Elite Dangerous einen bereits angeforderten Carrier-Sprung
  noch ausgeführt hat, CTSVision den zugehörigen `CarrierJump` aber nicht mehr empfangen konnte.
- **Routenfortschritt manuell korrigierbar.**
  CTSVision zeigt beim Fortsetzen den gespeicherten Stand, den gewählten aktuellen Standort
  und das daraus folgende nächste Sprungziel an. Erst nach Bestätigung wird der neue Fortschritt gespeichert.
- **Manuelle Routenplanung in der Hilfe dokumentiert.**
  Die integrierte Hilfe beschreibt die Orientierung der XYZ-Koordinaten,
  den Ablauf der manuellen Planung und die Übergabe der fertigen Route an CTSVision.

### Version 1.8
✨ Neu
- **Dark Mode** hinzugefügt.
  Die Darstellung kann direkt in CTSVision umgeschaltet werden und wird dauerhaft gespeichert.
  Der Dark Mode wird auch im separaten Routeninfo-Fenster verwendet.
- **Single-Instance-Schutz** hinzugefügt.
  CTSVision kann nicht mehr versehentlich mehrfach gleichzeitig gestartet werden.
- **Automatisches Beenden von Elite Dangerous überarbeitet und abgesichert.**
  Vor dem Beenden stellt CTSVision einen bekannten Menü-Zustand sicher.
  Falls erforderlich, wird mit BACKSPACE schrittweise bis zu Menü 1 zurückgegangen.
  Anschließend wird das Odyssey-Menü geöffnet und über die neue Vision-Referenz
  `exit_menu_fortsetzen` sicher erkannt, bevor die Tasteneingaben zum Beenden ausgeführt werden.
- **Testfunktion für das Beenden von Elite Dangerous** hinzugefügt.
  Über „ED-Beenden testen“ kann der Beenden-Ablauf unabhängig von einer Route geprüft werden.
  Der PC wird bei diesem Test niemals ausgeschaltet.
- **Vision Wizard erweitert.**
  Neue Referenz „ED-Beenden – FORTSETZEN“ für die sichere Erkennung des Odyssey-Menüs.
  Die Bildvorschau wurde verbessert und passt sich beim Vergrößern oder Verkleinern des Fensters
  korrekt an, ohne Referenzbilder abzuschneiden oder Bedienelemente zu verschieben.

### Version 1.7.1
✨ Neu
- Elite Dangerous kann nach erfolgreichem Abschluss der Sprungroute automatisch beendet werden.
  Dies erfolgt ausdrücklich nur, wenn die Automation erfolgreich abgeschlossen wurde.
- Wenn gewünscht, kann anschließend auch der PC automatisch ausgeschaltet werden.
  Der PC wird nur heruntergefahren, wenn Elite Dangerous zuvor erfolgreich beendet wurde.
- Automatische Update-Prüfung hinzugefügt.
  CTSVision prüft beim Start, ob eine neue Version auf GitHub verfügbar ist.
- Ist eine neue Version verfügbar, wird dies direkt in der Versionsanzeige angezeigt.
- Updates können direkt aus CTSVision heraus installiert werden.
  Vor der Installation wird automatisch ein Backup der bestehenden Installation erstellt.
- Persönliche Daten wie Konfiguration, Referenzbilder, Routen und Laufzeitdaten bleiben beim Update erhalten.
- Nach erfolgreicher Installation wird CTSVision automatisch neu gestartet.


### Version 1.6
 - Route wird direkt nach dem CarrierJump aktualisiert.
 - Das aktuelle Ziel wird unmittelbar als erledigt markiert.
 - Das nächste Sprungziel wird sofort in der GUI angezeigt.
 - Die Routenanzeige ist dadurch während der gesamten Abkühlzeit aktuell.
 - Tankprüfung vor dem ersten Sprung.
 - Vor dem ersten Sprung wird jetzt geprüft, ob genügend Tritium im Carrier vorhanden ist.
 - Falls erforderlich, wird automatisch nachgetankt.
 - Der erste Sprung startet erst nach erfolgreicher Tankprüfung.

Verbesserungen
Konsistenter Ablauf zwischen erstem und allen folgenden Sprüngen.
Immer aktueller Routenstatus während der Abkühlphase.
Höhere Sicherheit vor dem Start einer langen Carrier-Route.

### Version 1.5
- Vision Wizard
- OCR
- Journal Monitor
- Tank Wizard
- Workspace-Schutz

![CTSVision Banner](docs/images/Haupt.png)

## Roadmap

### Version 2.0
- Mehrsprachigkeit
- Windows-Unterstützung
- Plugin-System

GNU GPL v3.0

Entwickelt von **Faber38**
