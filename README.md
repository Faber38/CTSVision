🚀 CTSVision

Automatisierung für Fleet Carrier in Elite Dangerous

CTSVision ist ein Linux-Programm zur Automatisierung vonFleet-Carrier-Abläufen in Elite Dangerous.

Im Mittelpunkt stehen Computer Vision, OCR und die Auswertungdes Elite-Journals. Dadurch werden Spielzustände erkannt undEntscheidungen anhand des tatsächlichen Bildschirminhalts getroffen --nicht anhand fester Zeitabläufe.

✨ Funktionen

Automatische Fleet-Carrier-Sprünge

Vision-basierte Menünavigation

OCR-Auswertung des Tritium-Tankfüllstands

Automatisches Betanken des Fleet Carriers

Tankfunktion separat testbar

Statusanzeige des Tankvorgangs

Fortsetzen einer gespeicherten Route

Ausführung unter Linux (getestet mit Pop!_OS)

📦 Installation

Erstinstallation:

./install.sh

Programm starten:

./start.sh

🖼️ Ersteinrichtung

Vor dem ersten Automatiklauf müssen mit dem Vision Wizard dieReferenzbilder erstellt werden.

Da sich Monitore, Auflösungen und Grafikeinstellungen unterscheiden,geschieht dies einmalig auf jedem Rechner.

💡 Empfehlung

Für die höchste Erkennungsgenauigkeit sollte immer dasselbe Schifffür Carrier-Sprünge und das automatische Betanken verwendet werden.

Unterschiedliche Schiffe besitzen leicht abweichende Cockpitansichten.Schon kleine Pixelverschiebungen können die Bilderkennung beeinflussen.

Daher wird empfohlen:

immer dasselbe Schiff verwenden

während eines Automatiklaufs nicht das Schiff wechseln

nach einem dauerhaften Schiffwechsel die Referenzbilder neuerstellen

🖥️ Systemvoraussetzungen

Linux

Python 3.11 oder neuer

X11

Elite Dangerous: Odyssey

🖥️ Empfohlene Arbeitsumgebung

Für einen zuverlässigen Automatikbetrieb wird empfohlen, Elite Dangerousallein auf einer eigenen Arbeitsfläche (Virtual Desktop) auszuführen.

CTSVision arbeitet ausschließlich mit dem sichtbaren Bildschirminhalt vonElite Dangerous. Änderungen am Fensterinhalt – etwa durch überlagerndeFenster oder einen Wechsel auf eine andere Anwendung – können dieBilderkennung beeinträchtigen oder zu einem Abbruch des Automatiklaufsführen.

Daher wird empfohlen:

Elite Dangerous als einziges sichtbares Fenster auf dieser Arbeitsflächeauszuführen.

Das Elite-Fenster während des Automatiklaufs nicht zu minimieren oder zuüberdecken.

Während eines Automatiklaufs nicht auf andere Anwendungen innerhalbderselben Arbeitsfläche zu wechseln.

Programme wie Browser, Discord oder EDDiscovery auf einer separatenArbeitsfläche zu verwenden.

⛽ Tritium-Position

Je nach Fleet Carrier und Warenbestand kann sich der Eintrag TRITIUMan einer unterschiedlichen Position innerhalb der Transferliste befinden.

Mit der Einstellung „Tritium-Position“ kann festgelegt werden, anwelcher Stelle CTSVision mit der Suche beginnen soll.

Funktionsweise

Nachdem das Transferfenster geöffnet wurde, setzt CTSVision den Fokuszunächst mit einem einmaligen W in die Warenliste.

Erst ab dieser Position beginnt die Zählung.

Beispiele:

Einstellung

Bedeutung

0

Erste Listenzeile

-5

Fünf Zeilen nach unten

-20

Zwanzig Zeilen nach unten

-44

Vierundvierzig Zeilen nach unten

3

Drei Zeilen nach oben

Anschließend prüft CTSVision den Bereich per OCR.

Wird TRITIUM dort nicht gefunden, wird automatisch ein kleinerBereich oberhalb und unterhalb der eingestellten Position durchsucht.Dadurch muss die komplette Warenliste in den meisten Fällen nicht mehrdurchlaufen werden, was den Tankvorgang deutlich beschleunigt.

📝 Feedback

Fehlermeldungen, Screenshots und Logdateien helfen dabei, CTSVisionweiter zu verbessern.

🛣️ Roadmap

Version 1.0 ✅

Vision-System

OCR

Fleet-Carrier-Sprünge

Automatische Tankfunktion

Tankstatus

Route fortsetzen

Geplante Erweiterungen

Mehrere Schiffprofile

Erweiterte Vision-Profile

Weitere Komfortfunktionen

❤️ Danke

Vielen Dank für dein Interesse an CTSVision.

Fly safe, Commander!

CMDR Faber38

Version: 1.0.1 Status: Stable