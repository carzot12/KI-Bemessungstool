# Briefing: Demo-Medienpaket KI-Bemessungstool

## Thema und Zielpublikum

Der Vortrag zeigt einen Prototyp für die KI-gestützte Bemessung von Holzbauverbindungen. Das Zielpublikum kommt aus Holzbau, Bauingenieurwesen und Forschung. Die Präsentation soll technisch seriös, ruhig und nachvollziehbar wirken.

## Zweck des Prototyps

Das Werkzeug verbindet eine dialogorientierte Bedienung mit einem deterministischen Rechenkern. Die KI interpretiert Anforderungen, steuert Entwurfsziele und erläutert Varianten. Berechnungsformeln, Normprüfungen und technische Ergebnisse bleiben im überprüfbaren Rechenkern.

## Wichtigste KI-Funktionen

- Bemessungsauftrag in natürlicher Sprache erfassen.
- Fehlende Entwurfsparameter im definierten Variantenraum bestimmen.
- Tatsächlich berechnete Varianten kuratieren und erläutern.
- Entwurfsziele sprachlich ändern, beispielsweise weniger Stabdübel.
- Bei fixierter Geometrie eine Rückwärtsbemessung der maximalen Zugkraft anstoßen.
- Einen konsistenten technischen PDF-Bericht erzeugen.

## Unterschied zu Excel

Excel bildet häufig einzelne Rechenschritte oder Tabellen gut ab. Der Prototyp adressiert zusätzlich den durchgängigen Prozess: Anforderungen verstehen, Varianten erzeugen, Zielkonflikte erläutern, Geometrie visualisieren, Änderungen iterativ ausführen und das Ergebnis dokumentieren. Die KI ersetzt dabei nicht den deterministischen Nachweis.

## Konsistenter Demo-Fall

- Projekt: Demo Zuglaschenstoß
- Ft,Ed: 140 kN
- Holz: GL24h
- Querschnitt: 200 x 240 mm
- Nutzungsklasse: NK1
- Lasteinwirkungsdauer: mittel
- Entwurfsziel: wirtschaftliche Lösung

Tatsächlich berechnete Empfehlung des Demo-Laufs:

- 2 innenliegende Stahlbleche
- Blechdicke 6 mm
- 6 Stabdübel Ø16 mm je Stoßseite, Anordnung 2 x 3
- maßgebend: Verbindungsmittel im Holz
- Ausnutzung rund 85,3 Prozent
- 4.560 Varianten untersucht, 413 technisch geeignet

## Präsentationsstil

- Heller, technischer und reduzierter Stil.
- Rot der Marke nur für Akzente und Hervorhebungen.
- Große App-Screenshots statt kleinteiliger Collagen.
- Übergänge überwiegend Morph oder Verblassen.
- Zoom nur für einzelne technische Details.
- Keine 3D-, Dreh- oder Wirbelübergänge.
- Ein statischer Screenshot kann deckungsgleich durch ein Video ersetzt werden, sodass die Oberfläche scheinbar lebendig wird.

## Vorhandene Dateien

### Screenshots

- `01_screenshots/01_app_start.png`: sauber zugeschnittene, leere native App.
- `01_screenshots/01_app_start_full_desktop.png`: unbeschnittene Originalaufnahme als Reserve.
- `01_screenshots/12_pdf_bericht.png`: erste Seite des echten Demo-Berichts.

Die Screenshots 02 bis 11 müssen gemäß `04_storyboard/recording_guide.md` manuell aufgenommen werden, weil keine zuverlässige UI-Steuerung verfügbar war.

### Videos

Es wurden keine MP4-Dateien simuliert. Die drei vorgesehenen Aufnahmen sind in `02_demo_videos/README.md` und `04_storyboard/recording_guide.md` exakt beschrieben.

### PDF

- `03_pdf/Demo_Zuglaschenstoss_Bericht.pdf`: echter Berechnungsbericht des konsistenten Demo-Falls.

### PowerPoint-Assets

- `05_powerpoint_assets/holzbau_forschung_logo.png`: vorhandenes Markenlogo.

## Empfohlene Reihenfolge

1. Ausgangslage und Medienbruch.
2. Leerer KI Workspace.
3. Prompt und Thinking-State.
4. Berechnetes Ergebnis und technische Darstellung.
5. Variantenraum.
6. Erläuterte KI-Empfehlung.
7. Iteration mit weniger Stabdübeln.
8. Rückwärtsbemessung.
9. Technischer PDF-Bericht.
10. Schlussaussage: KI macht den deterministischen Entwurfsprozess dialogfähig und dokumentierbar.

