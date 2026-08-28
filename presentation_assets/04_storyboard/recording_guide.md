# Manueller Aufnahmeablauf

Die native pywebview-App konnte in der aktuellen Automationsumgebung nicht zuverlässig gesteuert werden. Deshalb wurden keine simulierten Videos erzeugt. Die folgenden Abläufe sind für eine saubere manuelle Aufnahme vorbereitet.

## Vorbereitung

1. Bildschirmauflösung mindestens 1920 x 1080 einstellen.
2. App-Fenster auf 16:9-nahe Größe bringen und mittig platzieren.
3. Desktop-Icons und andere Fenster aus dem Aufnahmebereich entfernen.
4. App mit `python3 app.py` starten.
5. Aufnahme auf das App-Fenster beschränken; keine Musik und kein Voice-over aufnehmen.
6. Maus ruhig bewegen und nach jedem wichtigen Zustand 1-2 Sekunden warten.

## Gemeinsamer Demo-Fall

- Projektname: `Demo Zuglaschenstoß`
- Last: `140 kN`
- Holz: `GL24h`
- Querschnitt: `200 x 240 mm`
- Nutzungsklasse: `NK1`
- Lasteinwirkungsdauer: `mittel`
- Entwurfsziel: `wirtschaftliche Lösung`

Vollständiger Prompt:

> Bemesse mir einen Zuglaschenstoß für 140 kN mit GL24h und einem Holzquerschnitt von 200 × 240 mm. NK1, Lasteinwirkungsdauer mittel. Finde eine wirtschaftliche Lösung.

## Video A - `demo_01_prompt_to_design.mp4`

Zieldauer: 20-30 Sekunden.

1. Neuer Entwurf; zwei Sekunden leere App stehen lassen.
2. Projektname `Demo Zuglaschenstoß` eintragen.
3. Prompt ruhig in das Chatfeld einfügen.
4. Eine Sekunde mit vollständig sichtbarem Prompt warten.
5. Enter drücken.
6. User-Nachricht und Thinking-Punkte zwei Sekunden sichtbar lassen.
7. Nach Erscheinen des Ergebnisses zwei Sekunden warten.
8. Langsam den Fokus auf technische Darstellung, BESTE LÖSUNG, η und Varianten bewegen.
9. Endzustand drei Sekunden stehen lassen.

Während dieses Ablaufs zusätzlich aufnehmen:

- `02_ki_prompt_loading.png` während der Thinking-Punkte.
- `03_ki_result.png` nach vollständigem Ergebnis.
- `04_seitenansicht.png` mit der KI-Empfehlung.
- Danach nacheinander dieselbe Variante in `Draufsicht`, `Schnitt A-A` und `3D` öffnen und als `05_draufsicht.png`, `06_schnitt_AA.png`, `07_3D.png` sichern.

## Varianten und Bewertung

1. Variantenansicht öffnen und `08_varianten.png` aufnehmen.
2. Zum Entwurf zurückkehren.
3. Prompt senden: `Warum empfiehlst du genau diese Variante?`
4. Antwort vollständig abwarten und `09_ki_bewertung.png` aufnehmen.

## Video B - `demo_02_ai_iteration.mp4`

Zieldauer: 15-25 Sekunden.

1. Mit vollständig sichtbarer Ausgangslösung beginnen.
2. Prompt senden: `Optimiere die Verbindung jetzt mit möglichst wenigen Stabdübeln.`
3. Thinking-State mindestens eine Sekunde zeigen.
4. Aktualisierte BESTE LÖSUNG, Varianten und technische Darstellung zeigen.
5. Endzustand drei Sekunden halten und zusätzlich `10_ki_optimierung.png` aufnehmen.

## Video C - `demo_03_reverse_design.mp4`

Zieldauer: 15-20 Sekunden.

1. Mit der aktuell gewählten Verbindung beginnen.
2. Prompt senden: `Wie viel Zugkraft kann die aktuell gewählte Verbindung maximal aufnehmen, wenn die Geometrie unverändert bleibt?`
3. Thinking-State kurz zeigen.
4. Maximallast, fixierte Geometrie und maßgebenden Nachweis zeigen.
5. Endzustand drei Sekunden halten und zusätzlich `11_rueckwaertsbemessung.png` aufnehmen.

## Screenshot-Kontrolle

- Alle technischen Ansichten müssen dieselbe empfohlene Variante zeigen.
- Projektname und Eingabedaten müssen dem gemeinsamen Demo-Fall entsprechen.
- Keine Menüs, Terminalfenster, Benachrichtigungen oder Mauszeiger über wichtigen Zahlen.
- Text und Maßketten bei 100-prozentiger Ansicht kontrollieren.

