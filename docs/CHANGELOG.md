# Changelog

Alle wichtigen Änderungen an **CTSVision** werden in dieser Datei dokumentiert.

Das Projekt orientiert sich an den Empfehlungen von
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/) und
[Semantic Versioning](https://semver.org/lang/de/).

---

## [1.9.4]

- Carrier-Kapazitätsparser wertet genau ein Zahlenpaar aus. Beschriftungen wie „USED CAPACITY“, „KAPAZITÄT“, „EINHEITEN“ und „UNITS“ werden vor der Ziffernnormalisierung abgegrenzt.
- Der verschobene Trenner `233872/5000` wird weiterhin als `23387/25000` erkannt, auch mit Beschriftungen. Eine einzelne zusätzliche Ziffer vor `25000` bleibt korrigierbar. Mehrere Angaben, weitere Zahlen, fehlende Trenner, unbekannte Beschriftungen und nicht unterstützte Fehlerformen führen zum sicheren Abbruch.
- Der bisherige Grenzwert 30.000 entfällt: Gültig sind 0 bis 25.000 für das Feld Used Capacity / 25.000. Dies ist nicht die Gesamtmasse des Carriers. Frontier dokumentiert selbst bei Überfüllung eine Anzeige von 25.000/25.000 ([Fleet Carriers Update – Patch 3](https://store.steampowered.com/news/posts/?appids=359320&enddate=1594916338&feed=steam_community_announcements)).
- `install.sh` gibt den Abschlusstext per Here-Document aus. Die Schritte für virtuelle Umgebung und Abhängigkeiten bleiben unverändert; Fehler beim Installieren brechen weiterhin ab.

- Einmalige, visuell abgesicherte Carrier-Zielkorrektur mit einer Sekunde Wartezeit und erneuter Zielprüfung. Bei unsicherer Erkennung kein Sprungklick; Stop wird berücksichtigt.
- Neue Referenz `galaxiekarte_carrier_symbol` samt Vorschau und Aufnahmehinweisen. Fehlende Katalogeinträge werden beim Laden im Speicher ergänzt, ohne persönliche Bilder oder Koordinaten zu ändern.
- Update-Kompatibilität mit v1.9.3: Dessen Installer behält `config/` bei; der neue Programmcode ergänzt den Wizard-Eintrag unabhängig davon.
- Schutz von `config.json`, `settings.json`, `route_state.json`, `references/`, `logs/` und CSV-Routen auch in Unterordnern. Rollback entfernt keine geschützten CSV-Routen.
- Releasebau über explizites Manifest mit Inhalts-, Syntax- und Versionsprüfung. Vorhandene Releaseverzeichnisse und ZIPs werden nicht überschrieben.
- Paket enthält keine persönlichen Konfigurationen, Referenzaufnahmen, CSV-Routen oder Carrier-Historie. Diese Paketregel schützt bereits beim Update durch den alten v1.9.3-Installer.

### Nach dem Update

Im Sprung-Wizard das Carrier-Symbol bei sichtbaren Machtspiele-Informationen mit darüber positionierter Maus eng aufnehmen, ohne zu klicken. Vorhandene eigene Symbolaufnahmen bleiben erhalten. Ohne passende Aufnahme bricht ein erforderlicher Korrekturversuch sicher ab.

### Lokale Freigabeprüfung

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_capacity_parser.py' -v`

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_install_script.py' -v`

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_carrier_target.py' -v`

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_release_update.py' -v`

Die Update-Integrationstests benötigen die lokalen ZIPs `release/CTSVision_v1.9.3.zip` (Originalversion) und `release/CTSVision_v1.9.4.zip` (mit `bash create_release.sh` erstellt). Sie verwenden temporäre Installationen und simulieren nur Prozessende und Neustart; die eigentliche Kopier- und Wiederherstellungslogik wird ausgeführt.

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
