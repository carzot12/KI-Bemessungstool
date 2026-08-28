# KI-Bemessungstool – Vortragszusammenfassung

## Problemstellung

Die Vorbemessung einer Holzbauverbindung verlangt viele zusammenhängende Entscheidungen: Material, Last, Querschnitt, Nutzungsklasse, Verbindungsmittel, Abstände, Stahlbleche, Nachweise und Varianten. Ein klassisches Rechenblatt kann diese Aufgaben sehr gut berechnen, setzt aber voraus, dass der Benutzer seine Anforderung in die vorgesehenen Felder und Abläufe übersetzt.

Der Prototyp untersucht eine konkrete Forschungsfrage: Kann ein Sprachmodell als verständliche Bedien- und Orchestrierungsschicht dienen, ohne selbst die statische Berechnung zu übernehmen?

## Warum KI?

KI wird hier nicht für Formeln eingesetzt. Besonders nützlich ist sie bei:

- natürlicher Sprache und unstrukturierten Anforderungen,
- Erkennung von Entwurfszielen wie „möglichst wenige Stabdübel“,
- Rückfragen bei fehlenden Angaben,
- kontextbezogenen Änderungen und Folgefragen,
- Auswahl kontrollierter Engineering-Funktionen,
- verständlicher Erklärung berechneter Ergebnisse.

Tragfähigkeiten, Ausnutzungen, Materialwerte, Mindestabstände und Normchecks bleiben deterministisch in Python.

## Entwicklung des Prototyps

Die Git-Historie zeigt einen schrittweisen Aufbau: Der erste sichtbare Stand enthält bereits den eigenständigen Python-Rechenkern, der nächste die zentrale Materialdatenbank. Erst danach folgen Assistent und Optimierer, Mehrdurchmesser-Suche, Ein-/Zwei-Blech-Modelle, Wissensbasis, LLM-Agent mit Toolzugriff, React-/Desktop-Oberfläche, technische Darstellung, Variantenworkflow und PDF-Berichte.

Das System wurde damit nicht als „LLM rechnet Statik“ konzipiert. Das Sprachmodell wurde als oberste Orchestrierungsschicht über bereits getrennte Fachmodule gesetzt.

## Architektur

```text
Benutzer
→ Chat, Kompaktformular oder manuelle Eingabe
→ React-Oberfläche
→ DesktopBridge
→ optionaler LLM-Agent oder lokaler Parser
→ Technical State
→ Optimierer
→ deterministischer Rechenkern
→ ÖNORM-/Geometrievalidator
→ Ergebnis-Snapshot
→ UI, technische Zeichnung und lokaler PDF-Bericht
```

Die manuelle Berechnung braucht kein LLM. Auch Kompaktberechnungen laufen lokal. Nur der Online-Chat sendet Kontext an die OpenAI API.

## Was macht die KI?

**Implementiert:** Sprache verstehen, Parameter und Ziele erkennen, Fehlstellen feststellen, Rückfragen stellen, kontrollierte Tools auswählen, Berechnungen/Optimierungen anstoßen, bereits berechnete Varianten vergleichen und Ergebnisse sprachlich erklären.

**Teilweise:** Empfehlungen und Berichtseinfluss. Die technische Auswahl stammt aus Python; das LLM kann sie begründen. Die Auswahl von Berichtvarianten erfolgt derzeit aber über die Oberfläche, nicht per Chattool.

**Nicht implementiert:** freie Normrecherche, Berechnung eigener Widerstände, vollständige Normprüfung oder selbstständige Erzeugung neuer Verbindungstypen.

## Was macht Python?

Python ist die technische Quelle der Wahrheit:

- Materialkennwerte aus einer lokalen Datenbasis,
- `kmod` und Teilsicherheitsbeiwert,
- Nettoquerschnitts-, Stahl-, Verbindungsmittel- und Blocknachweise,
- Ausnutzungen und maßgebender Nachweis,
- Geometrie-/ÖNORM-Checks,
- Variantenbildung, Filterung und Ranking,
- Rückwärtsbemessung durch wiederholte Kernberechnung,
- strukturierte Daten für Oberfläche und Bericht.

## Optimierung

Der Prototyp untersucht diskret Ø8, 10, 12, 16, 20 und 24 mm, Anordnungen `n=1…4` und `m=2…6`, ein oder zwei Stahlbleche, 5/6 mm Blechdicke sowie mögliche Schichtaufteilungen. Explizite Benutzervorgaben bleiben geschützt.

Jede Variante wird wirklich gerechnet und validiert. Erst danach darf sie als feasible gelten. Ziele sind unter anderem wenige Dübel, kompakte Geometrie, mehr Reserve, hohe zulässige Ausnutzung oder eine ausgewogene Empfehlung. „Wirtschaftlich“ ist derzeit eine Heuristik, keine Kostenrechnung.

## Beispielworkflow

1. „Bemesse 140 kN, GL24h, 200 × 240 mm, möglichst wenige Stabdübel.“
2. System erkennt Grundbedingungen und fragt nach Nutzungsklasse und Lasteinwirkungsdauer.
3. „NK1, mittel.“
4. Python erzeugt, berechnet, validiert und rankt Varianten.
5. „Warum diese Variante?“ – die KI erklärt nur Fakten aus dem Ergebnis.
6. „Probier Ø12.“ – Ø12 wird fixiert, freie Größen werden neu untersucht.
7. „Geht ein Blech?“ – rechnerisch ja untersuchbar; im aktuellen österreichischen Profil wegen nur zwei Scherflächen nicht zulässig.
8. „Wie viel hält die aktuelle Verbindung?“ – nur die Last wird per Bisektion erhöht; die Geometrie bleibt unverändert.
9. Varianten können in der UI für einen lokalen PDF-Bericht ausgewählt werden.

## Ein Blech und zwei Bleche

- **Ein Blech:** Holz–Stahl–Holz, zwei Scherfugen, eigener rechnerischer Johansen-Fall nach Gleichung (8.11). Fünf Teilnachweise sind implementiert. Der Validator schließt ihn im aktuellen österreichischen Profil wegen der geforderten vier Scherflächen aus.
- **Zwei Bleche:** Holz–Stahl–Mittelholz–Stahl–Holz, vier Scherfugen. Sieben Rechenkernchecks und der validierte V1-Workflow sind implementiert.

## Normen und Quellen

Normen erscheinen in zwei Rollen:

- als deterministisch programmierte Rechen-/Validierungsregel,
- als kuratierte Quellenreferenz für Erklärung, UI und Bericht.

Es gibt kein echtes Volltext-Retrieval und keine automatische Normaktualisierung. Einige Punkte – `a3,c`, `a4,t` und separater Holz-Bohrlochdurchmesser – sind ausdrücklich noch nicht verifiziert. Deshalb ist das System ein Prototyp und keine freigegebene Bemessungssoftware.

## Unterschied zu Excel

Ein gutes Excel-Blatt kann genauso normgerecht rechnen, Varianten bilden, Solver verwenden und Berichte erzeugen. Der Mehrwert dieses Prototyps ist nicht eine bessere Formel, sondern:

- natürliche statt ausschließlich feldbasierter Interaktion,
- kontextbezogene Folgefragen,
- sprachliche Zuordnung von Entwurfszielen,
- Orchestrierung mehrerer Fachfunktionen,
- Erklärung und Begründung bereits berechneter Varianten.

Excel bleibt oft transparenter für die direkte Formelprüfung. Das KI-System bietet dafür eine flexiblere Interaktionsschicht über einem ebenfalls deterministischen Kern.

## Datenschutz

Rechenkern, Optimierer, Materialien, UI, Dateien und PDF-Berichte bleiben lokal. Im Online-Chat werden jedoch Benutzertext, Chatverlauf, technischer Kontext und Toolergebnisse an die OpenAI API gesendet. Normvolltexte und lokale PDF-Dateien werden nicht übertragen. „Alles lokal“ wäre daher für den Online-Modus falsch.

## Grenzen

- nur Stabdübel-Zuglaschenstöße,
- enger diskreter Suchraum,
- keine vollständige Normabdeckung,
- keine Kosten-/CO₂-Optimierung,
- sprachliche LLM-Ausgaben können variieren,
- externe API-Abhängigkeit im Online-Chat,
- technische Darstellung und Bericht sind Prototypfunktionen,
- keine kommerziell oder bauaufsichtlich freigegebene Statiksoftware.

## Potenzial für die Holzbauforschung

Die Architektur lässt sich auf weitere deterministische Fachmodelle erweitern: eingeklebte Gewindestangen, Schrägverschraubungen, weitere Verbindungssysteme, Kosten- und Materialoptimierung, versioniertes Norm-Retrieval, lokale LLMs und strukturierte Forschungsberichte. Entscheidend bleibt die Rollenverteilung: Fachmodelle rechnen, der Agent verbindet Anforderungen, Werkzeuge und Erklärung.

## Ein Satz für den Vortrag

> Die Innovation ist nicht, dass ein Sprachmodell Statik rechnet, sondern dass es einen überprüfbaren, deterministischen Engineering-Prozess natürlich bedienbar und dialogfähig macht.
