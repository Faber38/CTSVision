# Mitwirken an CTSVision

Vielen Dank für dein Interesse an CTSVision!

Egal ob Fehlerbericht, Verbesserungsvorschlag oder eigener Code – jeder Beitrag hilft dabei, CTSVision besser zu machen.

---

# Projektziel

CTSVision ist eine Open-Source-Software zur visuellen Automatisierung von **Elite Dangerous**.

Das Projekt verfolgt einen klaren Grundsatz:

**Keine Speicherzugriffe. Keine Code-Injektion. Keine Manipulation des Spiels.**

Alle Entscheidungen basieren ausschließlich auf:

- Bildauswertung
- Journal-Dateien von Elite Dangerous
- Tastatureingaben
- Maussteuerung

CTSVision verhält sich wie ein menschlicher Spieler und automatisiert ausschließlich wiederkehrende Bedienabläufe.

---

# Projektphilosophie

Das wichtigste Ziel von CTSVision ist Zuverlässigkeit.

Das Programm soll sich jederzeit selbst wieder in einen definierten Zustand bringen können.

Dazu gehören unter anderem:

- Erkennen des aktuellen Menüs
- Automatische Korrektur falscher Zustände
- Selbstheilende Navigation
- Neuaufbau von Referenzbildern mit dem Vision Wizard

Stabilität ist wichtiger als Geschwindigkeit.

---

# Fehler melden

Bitte verwende für Fehlerberichte die GitHub-Issues.

Hilfreiche Informationen sind:

- Betriebssystem
- Desktop-Umgebung
- X11 oder Wayland
- Bildschirmauflösung
- Skalierung
- Elite Dangerous Version
- CTSVision Version
- Log-Ausgabe
- Screenshot (falls hilfreich)

Bitte veröffentliche keine Passwörter, API-Schlüssel oder persönliche Daten.

---

# Verbesserungsvorschläge

Neue Ideen sind jederzeit willkommen.

Bei größeren Änderungen bitte zunächst ein GitHub-Issue eröffnen, damit die Umsetzung gemeinsam besprochen werden kann.

---

# Pull Requests

Bitte achte auf folgende Punkte:

- Eine Änderung pro Pull Request
- Verständliche Commit-Nachrichten
- Sauber strukturierter Code
- Vor dem Commit testen
- Neue Funktionen möglichst dokumentieren

---

# Programmierstil

Grundsätzlich gilt:

- Python 3
- Gut lesbarer Code
- Lesbarkeit vor Kürze
- So wenige Abhängigkeiten wie möglich
- Kommentare dort, wo sie sinnvoll sind

Eine einheitliche Codebasis ist wichtiger als persönlicher Programmierstil.

---

# Referenzbilder

Der Ordner

references/

enthält benutzerspezifische Referenzbilder.

Diese werden bewusst **nicht** versioniert.

Die allgemeinen Vorlagen befinden sich im Ordner

assets/templates/

und gehören zum Projekt.

---

# Langfristige Ziele

CTSVision soll sich zu einer vollständigen Automatisierungsplattform für Fleet Carrier in Elite Dangerous entwickeln.

Geplant sind unter anderem:

- Visuelle Navigation
- Selbstheilende Menüführung
- Automatische Carrier-Routen
- Automatisches Auftanken des Fleet Carriers
- Tritium-Management
- Verwaltung der Carrier-Dienste
- Zuverlässige Wiederherstellung nach Fehlern

---

# Fair Play

CTSVision greift nicht in den Speicher von Elite Dangerous ein und verändert keine Programmdateien.

Das Projekt nutzt ausschließlich offiziell verfügbare Informationen und simuliert Eingaben über Tastatur und Maus.

---

# Danke!

Jeder Beitrag – egal ob Fehlerbericht, Verbesserungsvorschlag oder Quellcode – hilft dabei, CTSVision weiterzuentwickeln.

Vielen Dank für deine Unterstützung!

**o7 Commander**
