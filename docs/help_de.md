# CTSVision Hilfe

Diese Hilfe beschreibt die wichtigsten Funktionen von CTSVision und soll vor allem bei der Einrichtung, beim Start einer Route und bei der Fehlersuche helfen.

## Erste Schritte

1. Elite Dangerous starten.
2. CTSVision starten.
3. Eine Route auswählen.
4. Den Elite-Journalordner prüfen.
5. Vor der ersten Nutzung die benötigten Referenzbilder mit dem Vision Wizard erstellen.
6. Optional die Tankfunktion und das automatische Beenden von Elite Dangerous testen.
7. Die Route sofort oder zu einer geplanten Startzeit starten.

CTSVision arbeitet bewusst vorsichtig: Wenn ein benötigter Spielzustand nicht sicher erkannt wird, wird der Ablauf abgebrochen, statt unkontrolliert weitere Tasteneingaben auszuführen.

## Route auswählen

Mit **„Route auswählen…“** wird eine CSV-Datei mit der Carrier-Route geladen.

Unterstützt werden unter anderem Routen aus:

- Elite Dangerous Discovery (EDD)
- Spansh - Fleet Carrier Router 

Die geladene Route wird im Hauptfenster angezeigt. Über **„Routen-Info“** können zusätzlich Gesamtstrecke, Sprungzahl, Tritiumbedarf, Fortschritt und das nächste Ziel angezeigt werden.

## Route von Hand planen

Mit **„Route von Hand planen“** kann eine Fleet-Carrier-Route manuell anhand der XYZ-Koordinaten der Elite-Galaxiekarte erstellt werden.

Diese Funktion ist besonders für Reisen in weit entfernte oder noch wenig erkundete Gebiete gedacht. Dort können Systeme existieren, die in externen Routendiensten wie EDD oder Spansh noch nicht bekannt sind und deshalb nicht automatisch für eine Carrier-Route ausgewählt werden können.

Der Routenplaner berechnet deshalb **keine Systemnamen automatisch**. Stattdessen berechnet er jeweils einen theoretischen Punkt in Richtung des gewünschten Ziels. In der Elite-Galaxiekarte wird anschließend in der Nähe dieses Punktes ein tatsächlich vorhandenes System gesucht.

### Orientierung der Koordinaten

Für die Darstellung im manuellen Routenplaner gilt:

- **X** = links / rechts
- **Z** = unten / oben auf der 2D-Kartenebene
- **Y** = Schicht bzw. Höhe im 3D-Raum

Man kann sich die Y-Achse wie mehrere X/Z-Kartenebenen vorstellen, die übereinander bzw. untereinander liegen.

### Eine manuelle Route erstellen

1. **Startsystem** und dessen X-, Y- und Z-Koordinaten eintragen.
2. Die gewünschten **Zielkoordinaten** eintragen.
3. Die Soll-Sprungweite festlegen. Für einen Carrier mit maximal 500 Lj sind **495 Lj** ein sinnvoller Ausgangswert.
4. **„Route starten / neu berechnen“** wählen.
5. CTSVision zeigt den nächsten theoretischen Suchpunkt an.
6. In der Elite-Galaxiekarte möglichst nahe an diesen Koordinaten ein reales System suchen.
7. Den **Systemnamen und die tatsächlichen XYZ-Koordinaten** dieses Systems eintragen.
8. Mit **„Entfernung prüfen“** kontrollieren, ob das System innerhalb der maximalen Carrier-Sprungweite liegt.
9. Mit **„System übernehmen + weiter“** das System zur Route hinzufügen.
10. CTSVision berechnet nun vom tatsächlich gewählten System aus den nächsten Suchpunkt.

Dieser Ablauf wird wiederholt, bis die gewünschte Route erstellt ist.

Wichtig ist, immer die **tatsächlichen Koordinaten des gefundenen Systems** einzutragen. Der nächste Suchpunkt wird nicht vom vorherigen theoretischen Sollpunkt, sondern vom real gewählten System aus berechnet. Dadurch bleiben die folgenden Carrier-Sprünge korrekt.

### Route an CTSVision übergeben

Ist die manuelle Route fertig, kann sie mit **„Route an CTSVision übergeben“** als CTSVision-kompatible CSV-Datei gespeichert und direkt als aktuelle Route übernommen werden.

Das Startsystem wird dabei nicht als Sprungziel eingetragen. Der erste Eintrag der erzeugten CTSVision-Route ist das erste System, zu dem der Carrier tatsächlich springen soll.

Vor dem Start der Automatik sollte die erzeugte Route wie gewohnt noch einmal über **„Routen-Info“** kontrolliert werden.

## Journalordner

CTSVision überwacht das Elite-Dangerous-Journal, um wichtige Ereignisse wie einen erfolgreichen **CarrierJump** zu erkennen.

Der richtige Journalordner muss einmal ausgewählt werden. Die Einstellung wird gespeichert.

Wird ein CarrierJump erkannt, markiert CTSVision das Ziel als erledigt und aktualisiert sofort den Routenfortschritt.

## Vision Wizard

Der Vision Wizard erstellt die Referenzbilder, mit denen CTSVision die Elite-Oberfläche erkennt.

### Referenzbilder erstellen

- Referenzbilder immer **so klein wie möglich und nur so groß wie nötig** erstellen.
- Möglichst nur statische Elemente aufnehmen.
- Sterne, Nebel, Planeten und andere wechselnde Hintergründe vermeiden.
- Nach Änderungen an Auflösung oder UI-Skalierung die Referenzen erneut erstellen.
- Nach der Aufnahme die Referenz mit **„Vergleichen“** testen.

### Bereich markieren

Mit **„Bereich markieren“** kann ein Rahmen über Elite gelegt und mit der Maus positioniert werden.

Falls der Rahmen nicht sichtbar ist oder sich schlecht bedienen lässt, können die Werte **X, Y, Breite und Höhe** direkt verändert werden.

**Tipp:** Die Zahlenfelder lassen sich besonders genau mit den Pfeiltasten **↑ / ↓** verändern. Das ist oft die einfachste Methode, um einen Referenzausschnitt pixelgenau einzustellen.

### Vorschau

Die obere Ansicht zeigt die mitgelieferte Vorlage aus `assets/templates/`.

Die untere Live-Vorschau zeigt den momentan gewählten Ausschnitt aus dem Elite-Fenster.

## Tank Wizard

Der Tank Wizard richtet die Referenzbilder für die automatische Tritium-Funktion ein.

Dazu gehören unter anderem:

- Tankanzeige
- Tritiumdepot
- Inventar
- Transferliste
- Tritium-Erkennung

Die Referenzen sollten nach der Einrichtung ebenfalls geprüft werden.

## Tankfunktion prüfen

Mit **„Tankfunktion prüfen“** kann die Tanknavigation vor einer längeren Route getestet werden.

Der Test verwendet dieselben Vision- und Navigationskomponenten wie die automatische Tankroutine.

Der aktuelle Prüfschritt öffnet das Tritiumdepot und bestätigt den erkannten Zustand. Es wird dabei kein unnötiger Tritium-Transfer erzwungen.

## Automatisch betanken

Ist **„Carrier automatisch betanken“** aktiviert, prüft CTSVision vor dem ersten Routensprung den Carrier-Tank.

Nach jedem CarrierJump kann die Tankroutine parallel zur vierminütigen Abkühlzeit laufen.

Ein weiterer Sprung wird erst gestartet, wenn:

- die Abkühlzeit beendet ist und
- die Tankroutine erfolgreich abgeschlossen wurde.

### Tankgrenze

Die Tankgrenze bestimmt, ab welchem Füllstand nachgetankt werden soll.

**105 %** dient als Testmodus.

### Tritium-Position

Die Tritium-Position beschreibt die erwartete Position von TRITIUM in der Transferliste.

- Positive Werte: Bewegung mit **W** nach oben.
- Negative Werte: Bewegung mit **S** nach unten.
- Bei `0` wird zuerst die aktuelle Position geprüft.

## Startzeit festlegen

Eine Route kann sofort oder zu einer festgelegten Uhrzeit gestartet werden.

Ist **„Startzeit festlegen“** aktiviert, wartet CTSVision bis zum angegebenen Zeitpunkt.

Die eingestellte Startzeit gilt nur für den ersten Sprung. Danach läuft die Route automatisch weiter.

## Automatik starten

Mit **„Automatik starten“** beginnt CTSVision die Carrier-Route.

Vor jedem Sprung stellt CTSVision zunächst einen bekannten Ausgangszustand her und navigiert anschließend über die Carrier-Menüs zur Galaxiekarte.

Das Ziel wird automatisch in der Galaxiekarte gesucht und der Sprung angefordert.

Nach dem im Journal bestätigten CarrierJump wird das Ziel als erledigt markiert.

## Route fortsetzen

Der Routenfortschritt wird gespeichert.

Nach einem Neustart von CTSVision kann eine bereits begonnene Route wieder geladen und fortgesetzt werden.

**„Route fortsetzen“** aktualisiert die Anzeige, ohne den gespeicherten Fortschritt zurückzusetzen.

## Route neu starten

Mit **„Route neu starten“** wird der gespeicherte Fortschritt der aktuellen Route auf null gesetzt.

Bereits erledigte Sprünge werden danach wieder als offen behandelt.

Diese Funktion sollte nur verwendet werden, wenn die Route wirklich von vorne begonnen werden soll.

## ED-Beenden testen

Mit **„ED-Beenden testen“** kann der automatische Spielende-Ablauf unabhängig von einer Route geprüft werden.

Der PC wird bei diesem Test **niemals ausgeschaltet**.

CTSVision prüft zunächst, ob das Odyssey-Menü mit **FORTSETZEN** bereits geöffnet ist. Falls nicht, wird Menü 1 sicher hergestellt. Dazu kann CTSVision bei Bedarf schrittweise mit **BACKSPACE** zurückgehen.

Anschließend wird das Odyssey-Menü geöffnet und über die Referenz `exit_menu_fortsetzen` bestätigt.

Erst nach erfolgreicher Erkennung werden die Tasteneingaben zum Beenden von Elite Dangerous ausgeführt.

## Elite nach Routenabschluss beenden

Ist **„Elite Dangerous nach erfolgreichem Routenabschluss beenden“** aktiviert, wird Elite nur nach einem vollständig erfolgreichen Abschluss der Route beendet.

Bei Fehler, Abbruch oder manuellem Stop bleibt Elite geöffnet.

Für die sichere Erkennung des Odyssey-Menüs wird die Vision-Referenz:

`exit_menu_fortsetzen`

benötigt.

Fehlt diese Referenz, bricht CTSVision den Beenden-Ablauf ab und führt die eigentlichen Tasteneingaben zum Beenden nicht aus.

## PC ausschalten

Ist **„PC ausschalten“** aktiviert, darf der PC erst nach erfolgreichem Abschluss der Route heruntergefahren werden.

Wenn Elite automatisch beendet werden soll, wartet CTSVision zusätzlich darauf, dass der Elite-Prozess tatsächlich nicht mehr erkannt wird.

Wird Elite weiterhin erkannt, wird der PC aus Sicherheitsgründen **nicht** ausgeschaltet.

## Dark Mode

Mit **„Dark“** kann zwischen hellem und dunklem CTSVision-Design umgeschaltet werden.

Die Einstellung wird gespeichert und beim nächsten Start wieder verwendet.

Der Dark Mode gilt auch für das Routeninfo-Fenster und die Hilfe.

## Updates

CTSVision prüft beim Start, ob auf GitHub eine neuere Version verfügbar ist.

Ist ein Update verfügbar, ändert sich die Versionsanzeige.

Vor einer automatischen Installation wird ein Backup erstellt.

Persönliche Daten wie Konfiguration, Referenzbilder und eigene Routen sollen beim Update erhalten bleiben.

## Single-Instance-Schutz

CTSVision kann nur einmal gleichzeitig gestartet werden.

Wird versucht, eine zweite Instanz zu öffnen, erscheint ein Hinweis und der zweite Start wird beendet.

Dadurch wird verhindert, dass zwei Automationen gleichzeitig Tastatur- oder Mausbefehle an Elite senden.

## Fehler und Problemlösung

### Ein Menü wird nicht erkannt

- Prüfen, ob Elite und CTSVision auf derselben aktiven Arbeitsfläche liegen.
- Referenzbild im Vision Wizard erneut vergleichen.
- Auflösung und UI-Skalierung prüfen.
- Referenz bei Bedarf neu aufnehmen.
- Dynamische Bereiche im Referenzausschnitt vermeiden.

### Referenzbild fehlt

Fehlende Referenzen können über den jeweiligen Wizard neu erstellt werden.

Für das automatische Beenden von Elite wird zusätzlich `exit_menu_fortsetzen` benötigt.

### Automatik stoppt nach einem Fehler

Das ist beabsichtigt.

CTSVision soll bei einem unsicheren Zustand nicht blind weitere Tasteneingaben ausführen.

Die Fehlermeldung und gegebenenfalls der Bildvergleich helfen dabei, die betroffene Referenz zu finden.

## Sicherheitshinweis

CTSVision automatisiert bestimmte Abläufe in Elite Dangerous.

Die Nutzung erfolgt auf eigenes Risiko. Bitte beachte die aktuellen Regeln, Nutzungsbedingungen und Richtlinien von Frontier Developments.
