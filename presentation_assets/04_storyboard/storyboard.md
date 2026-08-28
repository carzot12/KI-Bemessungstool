# Storyboard: KI-Bemessungstool

Kommunikationsziel: Das Fachpublikum soll verstehen, dass freie Sprache den Entwurfsprozess steuert, während Berechnung, Variantenprüfung und Dokumentation nachvollziehbar aus dem deterministischen Rechenkern stammen.

## SZENE 1 - Ausgangslage

- Problem: Klassische Bemessung verteilt Eingabe, Variantenvergleich und Dokumentation häufig auf manuelle Arbeitsschritte oder mehrere Excel-Blätter.
- Empfohlenes Medium: einfache Auftaktfolie mit Titel und einer reduzierten Excel-/Formularansicht aus dem bestehenden Vortragsmaterial; noch kein App-Video.
- Kernaussage: Nicht die einzelne Formel ist das Problem, sondern der fragmentierte Arbeitsablauf rundherum.
- Dauer: 20-30 Sekunden.
- Möglicher Sprechertext: "Die Nachweise sind beherrschbar. Zeit kostet vor allem das wiederholte Eingeben, Variieren, Vergleichen und Dokumentieren. Genau an dieser Prozesskette setzt der Prototyp an."
- PowerPoint-Übergang: Verblassen.

## SZENE 2 - Freie Sprache im KI Workspace

- Empfohlenes Medium: `01_screenshots/01_app_start.png`, anschließend manuell aufzunehmendes `02_demo_videos/demo_01_prompt_to_design.mp4`.
- Kernaussage: Der Entwurf beginnt mit einer fachlichen Aufgabenbeschreibung statt ausschließlich mit einer starren Eingabemaske.
- Dauer: 25-35 Sekunden.
- Möglicher Sprechertext: "Ich formuliere den Bemessungsfall so, wie ich ihn einer Kollegin oder einem Kollegen beschreiben würde. Die Nachricht erscheint sofort, während der Assistent den Auftrag verarbeitet."
- PowerPoint-Übergang: Morph vom statischen Screenshot zum deckungsgleich platzierten Video.

## SZENE 3 - Sprache steuert den Rechenkern

- Empfohlenes Medium: noch manuell aufzunehmende Screenshots `02_ki_prompt_loading.png` und `03_ki_result.png`.
- Kernaussage: Die KI strukturiert die Anforderungen; die technischen Ergebnisse stammen aus dem deterministischen Berechnungskern.
- Dauer: 30-40 Sekunden.
- Möglicher Sprechertext: "Die KI interpretiert Projekt, Last, Material, Querschnitt und Entwurfsziel. Danach übernimmt der deterministische Kern. Für den Demo-Fall empfiehlt er tatsächlich zwei 6-mm-Bleche und sechs Stabdübel Ø16 bei rund 85 Prozent Ausnutzung."
- PowerPoint-Übergang: Verblassen; Ergebnisfolie nach kurzer Ladefolie.

## SZENE 4 - Automatisch untersuchter Variantenraum

- Empfohlenes Medium: manuell aufzunehmender Screenshot `08_varianten.png`.
- Kernaussage: Aus vielen berechneten Möglichkeiten werden nachvollziehbare Vergleichsvarianten kuratiert.
- Dauer: 30-40 Sekunden.
- Möglicher Sprechertext: "Im Testfall wurden 4.560 Varianten untersucht und 413 als technisch geeignet bewertet. Für die Entscheidung zeigt das Werkzeug eine kompakte Auswahl mit Geometrie, Ausnutzung, Reserve und maßgebendem Nachweis."
- PowerPoint-Übergang: Morph aus der Ergebnisansicht in die Variantenansicht.

## SZENE 5 - Empfehlung und Trade-offs

- Empfohlenes Medium: manuell aufzunehmender Screenshot `09_ki_bewertung.png`.
- Kernaussage: Die KI benennt den Grund für die Empfehlung, ohne die deterministischen Nachweise zu ersetzen.
- Dauer: 25-35 Sekunden.
- Möglicher Sprechertext: "Die Empfehlung ist keine Blackbox-Zahl. Der Assistent ordnet die Variante im Zielkonflikt zwischen Verbindungsmittelanzahl, Reserve und kompakter Geometrie ein."
- PowerPoint-Übergang: Verblassen.

## SZENE 6 - Iterativer Entwurf

- Empfohlenes Medium: manuell aufzunehmendes `02_demo_videos/demo_02_ai_iteration.mp4`, ersatzweise `10_ki_optimierung.png`.
- Kernaussage: Ein geändertes Ziel wird sprachlich formuliert und führt zu einem neuen, erneut berechneten Variantenraum.
- Dauer: 20-30 Sekunden.
- Möglicher Sprechertext: "Mit dem Satz 'möglichst wenige Stabdübel' ändere ich nicht einzelne Felder, sondern das Entwurfsziel. Die neue Lösung wird vollständig neu bewertet und visualisiert."
- PowerPoint-Übergang: Morph; gleiche App-Position vor und nach der Neuberechnung.

## SZENE 7 - Rückwärtsbemessung

- Empfohlenes Medium: manuell aufzunehmendes `02_demo_videos/demo_03_reverse_design.mp4`, ersatzweise `11_rueckwaertsbemessung.png`.
- Kernaussage: Bei fixierter Geometrie kann die maximal tragfähige Zugkraft als eigene Fragestellung berechnet werden.
- Dauer: 20-25 Sekunden.
- Möglicher Sprechertext: "Jetzt bleibt die Geometrie unverändert. Variiert wird ausschließlich die Zugkraft, bis der maßgebende Nachweis die Grenze bestimmt."
- PowerPoint-Übergang: Verblassen; Zoom nur gezielt auf den Wert der Maximallast.

## SZENE 8 - Technische Dokumentation

- Empfohlenes Medium: `01_screenshots/12_pdf_bericht.png` und `03_pdf/Demo_Zuglaschenstoss_Bericht.pdf`.
- Kernaussage: Eingaben, aktuelle Geometrie, Mindestwerte, Nachweise, Empfehlung und technische Zeichnungen werden konsistent dokumentiert.
- Dauer: 30-40 Sekunden.
- Möglicher Sprechertext: "Der Prozess endet nicht beim grünen Haken. Der Bericht übernimmt exakt die aktuelle ConnectionGeometry, trennt Mindest- und Istwerte und dokumentiert auch die maßgebenden Nachweise und Quellen."
- PowerPoint-Übergang: Morph von der App-Berichtsansicht auf die gerenderte PDF-Seite; danach ruhiges Verblassen zur Schlussaussage.

## Empfohlener Abschluss

Schlussaussage: "KI ersetzt nicht den Rechenkern. Sie macht den technisch kontrollierten Entwurfsprozess dialogfähig, iterativ und dokumentierbar."

