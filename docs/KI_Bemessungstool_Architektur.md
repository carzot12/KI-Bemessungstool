# KI-Bemessungstool: Architektur und Entwicklungsprozess

Stand der Analyse: 27. August 2026. Grundlage ist der aktuelle Arbeitsstand des Repositorys einschließlich uncommitteter Änderungen und der sichtbaren Git-Historie. Dieses Dokument beschreibt den Prototyp, nicht eine bauaufsichtlich freigegebene Bemessungssoftware.

## Statuslegende

- **IMPLEMENTIERT**: im aktuellen Code vorhanden und aufrufbar.
- **TEILWEISE IMPLEMENTIERT**: vorhanden, aber fachlich, normativ oder funktional begrenzt.
- **NICHT IMPLEMENTIERT / GEPLANT**: im aktuellen Code nicht vorhanden; gegebenenfalls Zukunftsperspektive.

## 1. Ziel des Prototyps

Der Prototyp untersucht zugbeanspruchte Stabdübel-Zuglaschenstöße mit einem oder zwei innenliegenden Stahlblechen. Er verbindet drei bewusst getrennte Fähigkeiten:

1. einen deterministischen Python-Rechenkern für Tragfähigkeiten und Nachweise,
2. einen deterministischen Variantenoptimierer und eine normative Zulässigkeitsprüfung,
3. einen optionalen LLM-Agenten für natürliche Sprache, Tool-Auswahl und sprachliche Erläuterung.

Die für den Vortrag fachlich korrekte Kernaussage lautet:

> Die KI ersetzt nicht die statische Berechnung. Sie orchestriert den Engineering-Prozess und interpretiert Ergebnisse des deterministischen Rechenkerns.

Diese Aussage trifft auf die Online-Agentenarchitektur zu. Ohne API-Schlüssel läuft ein regelbasierter lokaler Dialogmodus, aber weiterhin derselbe Rechenkern.

## 2. Entwicklungsgeschichte

Die Historie unterstützt die Aussage, dass nicht mit einem frei rechnenden LLM begonnen wurde. Die genaue Entstehung vor dem ersten sichtbaren Commit lässt sich aus Git nicht beweisen; die folgenden Schritte sind dagegen belegt:

| Zeitraum/Commit | belegte Entwicklungsschicht |
|---|---|
| `7cffe30` | erster sichtbarer Stand mit eigenständigem Python-Rechenkern `calculations/stabduebel.py` und klassischer App – noch ohne LLM-Agent |
| `fca9b66` | zentrale Holzmaterialdatenbank mit 948 Zeilen Kennwerten |
| 11.08.2026, `3214ac7` | erst danach KI-gestützter Stabdübel-Prototyp mit `assistant.py`, Optimierer und Prompt auf dem vorhandenen Rechenkern |
| 11.08.2026, `890df81` | Ausbau der V1-Oberfläche |
| 11./12.08.2026, `cc368cb`, `6ad4e5d` | Mehrdurchmesser-Optimierung, lokale Wissens-/Quellenbasis und technische Darstellung |
| 11.08.2026, `1335f98` | separater rechnerischer Ein-Blech-Fall und normativer Audit |
| spätestens 13.08.2026, Baseline `0b61353` | LLM-Agent mit Engineering-Tools, Technical State, Materialverwaltung, Validator, umfangreiche Tests |
| 24./25.08.2026, `5a392c2` und Folgecommits | React-/pywebview-Oberfläche, DesktopBridge, Serializer, Demo-Snapshot, Rückwärtsbemessung und Quellenprüfung |
| 27.08.2026, `c1cf1d0` und Folgecommits | Berichtserstellung, Varianten-/Präsentationsworkflow und UI-Überarbeitung |

Die heutige Schichtenfolge ist:

1. **Fachliches Datenmodell** – `StabduebelInput`, `Check`, `StabduebelResult`.
2. **Deterministischer Rechenkern** – einzelne Nachweisfunktionen und `calculate_stabduebel`.
3. **Materialverwaltung** – JSON-Daten und typsicherer Repository-Zugriff.
4. **Normative Validierung** – getrennte ÖNORM-/Geometriechecks.
5. **Optimierer** – diskreter Suchraum, vollständige Kernberechnung je Kandidat, Ranking.
6. **Technical State** – Parameter, Herkunft, Fixierungen, Ergebnisse, vorheriger Zustand.
7. **Engineering-Tools** – kontrollierte Fassade um vorhandene Python-Funktionen.
8. **LLM-Agent** – natürliche Sprache und Tool-Orchestrierung über die OpenAI Responses API.
9. **DesktopBridge** – freigegebene Grenze zwischen Web-UI und Python.
10. **React-/Desktop-Oberfläche** – Chat, Kompakt-, Manuell-, Varianten-, Nachweis-, Quellen- und Berichtsansicht.
11. **Technische Darstellung** – SVG-Sichten aus serialisierter Ergebnisgeometrie.
12. **Berichtserstellung** – lokale PDF-Erstellung mit ReportLab.

Die Trennung ist wichtig, weil ein Sprachmodell probabilistisch formuliert, während Nachweise reproduzierbar sein müssen. Außerdem können Rechenkern, Validator und Optimierer unabhängig vom LLM getestet und über Chat, Kompaktformular oder manuelle Eingabe wiederverwendet werden.

## 3. Systemarchitektur

### 3.1 Tatsächlicher Ablauf

```text
Benutzer
  ├─ Chat in natürlicher Sprache
  │    └─ React UI → DesktopBridge.send_message
  │         ├─ mit API-Key: LLMAgent → kontrollierte EngineeringTools
  │         └─ ohne API-Key: lokaler Parser/Orchestrator
  ├─ Kompakteingabe
  │    └─ React UI → DesktopBridge.compact_calculate → lokaler Orchestrator
  └─ Manuelle Eingabe
       └─ React UI → DesktopBridge.manual_calculate
                      ↓
              Technical State / StabduebelInput
                      ↓
           MaterialRepository + kmod-Tabelle
                      ↓
          Optimierer (bei Entwurfsauftrag)
                      ↓
      calculate_stabduebel (deterministischer Kern)
                      ↓
       validate_oenorm (Zulässigkeit/Geometrie)
                      ↓
       StabduebelResult / OptimizationResult
                      ↓
       Serializer → React UI / SVG / Varianten
                      └─ optional: lokaler PDF-Bericht
```

Die manuelle Eingabe umgeht LLM und Optimierer für die erste Berechnung. Die Kompakteingabe erzeugt einen strukturierten lokalen Entwurfsauftrag. Nur der Chat nutzt bei vorhandenem Schlüssel tatsächlich die externe API.

### 3.2 Schichten, Ein- und Ausgaben

| Schicht | Aufgabe | Relevante Module | Input | Output/Abhängigkeiten |
|---|---|---|---|---|
| Fachmodell | vollständige Anschlussparameter und Ergebnisobjekte | `calculations/stabduebel.py` | Zahlen, Klassen, Geometrie | `StabduebelInput`, `StabduebelResult` |
| Material | Holzklassen und Bemessungsbeiwerte | `infopol/materials/timber.json`, `timber.py`, `timber_design.py` | Holzklasse, NK, Dauer | `rho_k`, `ft,0,k`, `fv,k`, `kmod`, `γM` |
| Rechenkern | Tragfähigkeiten/Ausnutzungen | `calculations/stabduebel.py` | validierter `StabduebelInput` | sieben Checks bei zwei Blechen, fünf bei einem Blech |
| Validator | Norm-/Geometrieprofil | `calculations/oenorm_validation.py` | Input und optional Ergebnis | strukturierte `ValidationCheck`s |
| Optimierer | Varianten erzeugen, rechnen, filtern, ranken | `ai/optimizer.py` | Basisinput, Fixierungen, Ziel | `OptimizationResult` |
| State/Dialog | Gesprächskontext und technische Herkunft | `ai/assistant.py` | Parameteränderungen und Ergebnisse | aktueller/vorheriger Zustand, Fixierungen, Varianten |
| Tools | erlaubte Agentenaktionen | `ai/agent.py` | streng beschriebene Funktionsargumente | strukturierte Python-Ergebnisse |
| LLM-Agent | Toolwahl und natürliche Antwort | `ai/agent.py`, Promptdatei | Chatverlauf + Engineering-Kontext | Toolaufrufe und Antworttext |
| Bridge | freigegebene UI-Python-Schnittstelle | `desktop/bridge.py` | JSON-Payloads | versionierter UI-Snapshot |
| Serialisierung | reine View Models | `desktop/serializers.py` | State/Resultate | JSON für UI, Varianten und SVG |
| UI | Interaktion und Präsentation | `frontend/src/App.tsx` | Snapshot und Benutzereingaben | Chat, Formulare, Ergebnisansichten |
| Darstellung | technische SVG-Geometrie | `frontend/src/visualization/*` | `VisualizationModel` | Seiten-, Drauf-, Schnitt- und 3D-SVG |
| Bericht | lokale PDF-Ausgabe | `desktop/reports.py` | serialisierter Snapshot | Berechnungs- oder Variantenbericht |

## 4. Rolle des LLM

### 4.1 Welches LLM wird verwendet?

- **Anbieter/API:** OpenAI, Python-SDK `openai`, Responses API (`client.responses.create`).
- **Default-Modell:** `gpt-5-mini`.
- **Konfiguration:** Umgebungsvariable `OPENAI_MODEL`; damit ist die Modell-ID austauschbar, sofern das Konto Zugriff darauf hat und das Modell die verwendeten Funktionen unterstützt.
- **Verfügbarkeitsprüfung:** `client.models.retrieve(MODEL)`.
- **API-Key:** zuerst `OPENAI_API_KEY`, auf macOS alternativ Schlüsselbunddienst `KI-Bemessungstool OpenAI`; der Schlüssel ist nicht im Repository eingebettet.
- **Fehlerverhalten:** Ein konfigurierter, aber fehlerhafter Online-Zugang fällt nicht still auf den lokalen Modus zurück; die UI meldet den LLM-Fehler.

Die Responses API kann Texteingaben verarbeiten und eigene, typisierte Funktionen aufrufen; genau dieses Muster verwendet die App ([offizielle OpenAI API-Referenz](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)). Modelle sind eigenständige API-Ressourcen und nicht dasselbe wie ChatGPT als fertiges Produkt ([offizielle Modellübersicht](https://developers.openai.com/api/docs/models)).

### 4.2 Begriffe

- **LLM:** ein großes Sprachmodell, das Textkontext verarbeitet und probabilistisch Text oder strukturierte Aktionen erzeugt.
- **GPT-Modell:** eine konkrete Modellfamilie bzw. Modell-ID. Hier ist standardmäßig `gpt-5-mini` konfiguriert.
- **OpenAI API:** die Programmierschnittstelle, über die diese Desktop-App das Modell aufruft.
- **ChatGPT:** ein fertiges OpenAI-Produkt mit eigener Oberfläche und Produktfunktionen. Diese App ist nicht „ChatGPT eingebaut“, sondern ein eigener Client der API.
- **KI-Agent:** in diesem Repository die Kombination aus LLM, Systemanweisung, Engineering-Kontext, Tool-Schemas, Toolschleife und State. Der Agent kann Aktionen auswählen; rechnen darf er nur über Python-Tools.

### 4.3 Aufgabenmatrix des Agenten

| Fähigkeit | Status | Tatsächlicher Mechanismus / Fundstelle |
|---|---|---|
| natürliche Sprache interpretieren | **IMPLEMENTIERT** | Online: `LLMAgent.respond`; offline: `_fallback_extract` |
| Parameter erkennen | **IMPLEMENTIERT** | `update_design`-Schema sowie lokale Regex-Extraktion |
| fehlende Parameter erkennen | **IMPLEMENTIERT** | `_missing_required_parameters`, Tool `get_missing_information` |
| Rückfragen stellen | **IMPLEMENTIERT** | Clarification-State und natürliche Agentenantwort |
| Intents/Entwurfsziele verstehen | **IMPLEMENTIERT** | Online durch Agent/Toolwahl; offline über Intent-Schema und Regeln |
| Engineering-Tools auswählen | **IMPLEMENTIERT (nur online)** | Responses-API-Funktionsaufrufe in `ai/agent.py` |
| Berechnung/Optimierung starten | **IMPLEMENTIERT** | Tools `calculate_design`, `optimize_design`; lokal direkte Orchestrierung |
| Varianten vergleichen | **IMPLEMENTIERT** | ausschließlich bereits berechnete Varianten über `compare_variants` |
| bestehenden Entwurf ändern | **IMPLEMENTIERT** | `update_design`, State und anschließende Neuberechnung |
| Ergebnisse erklären | **IMPLEMENTIERT** | `explain_calculation` liefert deterministische Fakten; LLM formuliert |
| Empfehlungen formulieren | **TEILWEISE IMPLEMENTIERT** | Auswahl/Rangfolge aus Python; Text aus Templates bzw. LLM |
| Folgefragen mit Kontext | **IMPLEMENTIERT** | `message_history`, `agent_context`, `DialogueMemory` |
| Rückwärtsberechnung auslösen | **IMPLEMENTIERT** | `calculate_maximum_load`; Zielausnutzung im lokalen Orchestrator |
| Berichtsinhalte beeinflussen | **TEILWEISE IMPLEMENTIERT** | Empfehlungstext gelangt in Bericht; Variantenwahl erfolgt über UI, nicht über Agenten-Tool |
| Normvolltexte frei durchsuchen | **NICHT IMPLEMENTIERT** | nur kleine kuratierte Metadaten-/Quellenbasis |

## 5. Rolle des deterministischen Rechenkerns

Das LLM erzeugt ausdrücklich **nicht**:

- Tragfähigkeiten und Widerstände,
- Ausnutzungen,
- Materialkennwerte,
- `kmod` und `γM`,
- Johansen-Modi und wirksame Verbindungsmittelanzahl,
- Nettoquerschnitts-, Stahl-, Verbindungsmittel- und Blocknachweise,
- Mindestabstands- und Geometrieentscheidungen,
- maßgebenden Check und technischen Gesamtstatus.

Diese Werte entstehen in `calculations/stabduebel.py`, `infopol/materials/*` und `calculations/oenorm_validation.py`. Das LLM kann sie sprachlich falsch wiedergeben, aber die strukturierten Ergebnisfelder der UI werden direkt aus Python serialisiert. Das LLM erhält keine Funktion, um Widerstände oder Ausnutzungen direkt zu überschreiben.

### Geführte Nachweise

Zwei Bleche: Seitenholz-Nettoquerschnitt, Mittelholz-Nettoquerschnitt, Stahlblechzug, Verbindungsmittel im Stahlblech, Blockversagen Stahlblech, Verbindungsmittel im Holz und Blockscheren im Holz.

Ein Blech: Seitenholz-Nettoquerschnitt, Stahlblechzug, Verbindungsmittel im Stahlblech, Blockversagen Stahlblech und Verbindungsmittel im Holz. Mittelholz und Holz-Blockscheren sind für diesen Aufbau ausdrücklich nicht anwendbar.

## 6. Engineering Tools

Der Online-Agent erhält genau zwölf freigegebene Funktionen aus `TOOL_DEFINITIONS`:

| Tool | Zweck und Eingaben | Rückgabe / State-Wirkung |
|---|---|---|
| `get_current_design` | keine Eingaben | kompakter aktueller Engineering-Kontext; keine Änderung |
| `update_design` | erlaubte Parameter, Herkunft, Quelle, Autonomiemodus | validiert/normalisiert Parameter; aktualisiert State und Fixierungen |
| `calculate_design` | keine Eingaben | lokale Berechnung des aktuellen Designs; Resultat und Fehlstellen |
| `optimize_design` | Ziel + optionale Constraints | setzt Ziel/Autonomie, startet deterministischen Optimierer, speichert Auswahl |
| `compare_variants` | Variantennummern + Constraints | nur bereits berechnete kompakte Varianten; keine neue Formel |
| `calculate_maximum_load` | optionale Constraints | Bisektionssuche mit wiederholten Kernaufrufen; Geometrie bleibt fest |
| `validate_design` | keine Eingaben | aktuelle ÖNORM-/Geometriechecks |
| `get_previous_design` | keine Eingaben | vorheriger State/Resultat |
| `restore_previous_design` | keine Eingaben | tauscht aktuellen und Undo-State |
| `get_missing_information` | keine Eingaben | tatsächlich fehlende Pflichtangaben |
| `search_knowledge_base` | Suchtext | kuratierte Wissenseinträge und Quellenmetadaten; keine State-Änderung |
| `explain_calculation` | Thema | deterministische Fakten zu Auswahl oder maßgebendem Check |

Das `update_design`-Schema erlaubt Last, Holzklasse, Querschnitt, NK/Dauer, Dübel/Bleche, Schichtdicken, Anordnung und Abstände. Unbekannte Felder werden abgewiesen. Null-/Nichtpositiv-Platzhalter werden herausgefiltert. Als `USER_FIXED` akzeptiert das Tool nur Werte, die ein zusätzlicher lokaler Parser in der tatsächlichen Benutzernachricht wiedererkennt. Nicht-benutzerseitige Updates dürfen bestehende Fixierungen nicht überschreiben.

Kontrollierter Tool-Zugriff ist sicherer als freies LLM-Rechnen, weil Argumente eingeschränkt, Zustandsänderungen nachvollziehbar und Ergebnisse reproduzierbar sind. Er verhindert jedoch keine falsche sprachliche Zusammenfassung nach einem korrekten Toolergebnis.

## 7. Technical State

`ConversationState` speichert unter anderem:

- aktuelle Parameter und `fixed_parameters`,
- Herkunft und Quellen je Parameter,
- maximale/minimale Ausnutzung und Optimierungsziel,
- gewünschten Dübelcount und Top-N,
- aktuellen, letzten erfolgreichen und vorherigen Entwurf,
- letztes Optimierungsergebnis und letzte Maximallast,
- Anschlussfall und Scherflächen,
- offene Rückfrage, Undo-State, Empfehlung und Berichtsauswahl.

### Herkunft und Veränderbarkeit

- **USER_FIXED:** ausdrücklich durch den Benutzer gesetzt; der Optimierer darf diese Werte nicht verändern.
- **OPTIMIZED:** aus der letzten Auswahl; bei einer neuen ausdrücklichen Optimierung wieder variabel.
- **AI_DERIVED / KNOWLEDGE_DERIVED / DERIVED:** vom System hergeleitet; dürfen keine User-Fixierung überschreiben.
- **Optimierungsvariablen:** normalerweise Durchmesser, `n`, `m`, Blechzahl, Blechdicke sowie freie Seiten-/Mittelholzaufteilung. Abstände werden ebenfalls durchmesserabhängig erzeugt, sofern sie nicht fixiert sind.

Chat, Kompakt und Manuell nutzen denselben Assistant-State und Rechenkern. Kompakt setzt die Grundbedingungen und ein Ziel über einen lokalen strukturierten Auftrag. Manuell berechnet den exakten Formularinput direkt und markiert übergebene Felder als fixiert. Folgefragen bauen auf dem erhaltenen State auf.

### Beispiel „Probier Ø12.“

1. Der Agent erkennt `dowel_diameter_d_mm = 12`.
2. `update_design` bzw. `_apply` speichert den Wert als **USER_FIXED**.
3. Vorheriger State wird für Undo gesichert.
4. Sind Pflichtangaben vorhanden, wird neu gerechnet/optimiert.
5. Ø12 bleibt fix. Andere nicht ausdrücklich fixierte Größen – etwa `n`, `m`, Blechzahl/-dicke und Schichtaufteilung – dürfen je nach Intent und Ziel weiter variiert werden.

## 8. Optimierung

### 8.1 Suchraum

| Variable | automatischer Suchraum |
|---|---|
| Dübel-Ø | 8, 10, 12, 16, 20, 24 mm; automatische Kandidaten bevorzugen 12/16 mm |
| `n` längs | 1 bis 4 |
| `m` quer | 2 bis 6 |
| Stahlbleche | 1 oder 2 |
| Blechdicke | 5 oder 6 mm |
| Zwei-Blech-Schichtaufteilung | freie `t1`-Werte im 5-mm-Raster; `t2` aus exakter Breitensumme |
| Ein-Blech-Schichtaufteilung | symmetrisches `t1 = (b-ts)/2` |
| Abstände | wenn nicht fixiert: bei Ø12 bleiben Basiswerte; sonst `a1=5d`, `a2=3d`, `a3,t=max(7d,80)`, `a4,c=3d` |

Die Breite `b`, Höhe `h`, Last, Holzklasse, Nutzungsklasse und Lasteinwirkungsdauer sind im üblichen autonomen Entwurf Grundbedingungen. Explizit gesetzte Variablen werden aus dem Suchraum auf ihren Einzelwert reduziert.

Die theoretische Produktmenge hängt von `b` und Fixierungen ab. Beim analysierten Referenzfall `b=200 mm` entstehen vor Rechenfehlerfiltern 4.800 Schleifenkombinationen; 4.560 konnten als Varianten tatsächlich berechnet werden, 413 waren für 140 kN technisch feasible. Diese Zahlen sind ein gemessener aktueller Referenzlauf, keine feste Produktgarantie.

### 8.2 Lebenszyklus einer Variante

- **erzeugt:** Kombination im diskreten Suchraum.
- **berechnet:** `calculate_stabduebel` lief ohne Input-/Rechenfehler; erst dann zählt sie zu `evaluated_count`.
- **normativ/geometrisch zulässig:** `validate_oenorm(...).admissible` ist wahr.
- **technisch ausreichend:** alle Rechenkernchecks sind erfüllt und Ausnutzung liegt innerhalb der gesetzten Grenzen.
- **feasible:** normativ/geometrisch zulässig **und** technisch ausreichend.
- **shortlisted/curated:** bis zu zwölf unterschiedliche Signaturen `(Blechzahl, Ø, n, m)`, inklusive Auswahl, Ø12-/Ø16-Alternativen und Reservevariante.
- **empfohlen:** Minimum des Ziel-Rankings innerhalb der bevorzugten Kandidaten.

### 8.3 Ranking

- **BALANCED_DESIGN:** zunächst weniger Bleche, dann weniger Dübel, Durchmesserpräferenz 12 vor 16, Nähe zu 85 % Ausnutzung, dann Verbindungsfläche.
- **MIN_FASTENER_COUNT:** Dübelanzahl zuerst, dann Blechzahl, Nähe zu 85 %, Durchmesserpräferenz und Fläche.
- **COMPACT_GEOMETRY:** Verbindungsfläche zuerst.
- **LOWER_UTILIZATION / mehr Reserve:** Nähe zum fest codierten Ziel 65 %, nicht absolut minimale Ausnutzung.
- **MAXIMIZE_UTILIZATION:** höchste noch zulässige Ausnutzung zuerst.
- **MIN_PLATE_THICKNESS:** dünnstes Blech, danach Dübelzahl und Ausnutzung. Das Ziel ist im Backend vorhanden, aber nicht als eigene Standardoption im Kompaktformular angeboten.

„Wirtschaftlich“ bedeutet hier eine heuristische Rangfolge, **keine Kostenrechnung**. Materialpreise, Fertigungszeit und CO₂ sind nicht modelliert.

## 9. Normintegration

### 9.1 Norm als Rechenregel

Deterministisch implementiert sind unter anderem:

- Materialkennwerte aus `timber.json` mit Quellenmetadaten ÖNORM EN 338/14080,
- `kmod` nach ÖNORM EN 1995-1-1 Tabelle 3.1 und `γM=1,30` nach Tabelle 2.3,
- Mindestabstände `a1`, `a2`, `a3,t`, `a4,c`, Durchmesserbereich und nationale Zusatzbedingungen im Validator,
- Johansen-bezogene Verbindungsmittelnachweise; beim Ein-Blech-Fall Gleichung (8.11),
- Stahl- und Holzteilnachweise entsprechend der implementierten Referenzformeln.

### 9.2 Norm als Wissensquelle

`knowledge/sources.py` enthält kleine, manuell kuratierte Aussagen und Quellenmetadaten zu ÖNORM EN/B, IHBV-Tabellen und Referenzfällen. Es enthält keine Volltext-Retrieval-Pipeline, keine Embeddings, keinen Vektorindex und keine automatische Aktualisierung. Die zur Entwicklung abgelegten Text-/Bildextrakte unter `tmp/pdfs` werden vom Laufzeitcode nicht durchsucht.

Quellen im UI und Bericht stammen aus den `source`-Feldern der Validatorchecks. Damit besteht eine echte konzeptionelle Trennung zwischen **Norm als Rechenregel** und **Norm als Erklär-/Quellenreferenz**, aber die Wissensseite ist nur klein und manuell.

### 9.3 Wichtige Validierungsgrenze

Die Status `WARNING` und `NOCH NICHT VERIFIZIERT` gelten technisch als „nicht fehlgeschlagen“; `TechnicalValidationResult.admissible` prüft nur auf `FAILED`. Aktuell als nicht verifiziert markiert sind ein separater `a3,c`, `a4,t` und ein separater Holz-Bohrlochdurchmesser. „Admissible“ bedeutet deshalb Zulässigkeit innerhalb des implementierten engen Profils, nicht vollständige Normabdeckung.

## 10. Vorwärtsbemessung

Beispiel: „Bemesse mir einen Zuglaschenstoß für 140 kN mit GL24h, 200 × 240 mm, möglichst wenige Stabdübel.“

1. React übergibt den Text an `DesktopBridge.send_message`.
2. Online erhält der LLM-Agent Chatverlauf und `ENGINEERING_CONTEXT_JSON`; offline extrahiert der lokale Parser.
3. Last, Holzklasse, Querschnitt und Ziel werden im State gespeichert; ausdrücklich erkannte Werte werden fixiert.
4. `_missing_required_parameters` stellt fest, dass Nutzungsklasse und Lasteinwirkungsdauer fehlen.
5. Die App fragt diese Angaben nach; sie werden nicht automatisch als User-Vorgabe erfunden.
6. Nach „NK1, mittel“ lädt `_build_input` Materialwerte, `kmod` und `γM`.
7. Der Optimierer erzeugt Varianten für alle nicht fixierten Entwurfsgrößen.
8. Jede berechenbare Variante durchläuft `calculate_stabduebel` und `validate_oenorm`.
9. Nur zulässige, bestandene Varianten innerhalb der Ausnutzungsgrenzen sind feasible.
10. `MIN_FASTENER_COUNT` rankt die feasible Kandidaten; die Auswahl wird aktueller State.
11. UI-Snapshot zeigt Ergebnis, bis zu zwölf kuratierte Alternativen, Nachweise, Quellen und technische Geometrie.
12. Online formuliert das LLM eine kurze Antwort auf Basis der Toolresultate; die Bridge kürzt eine Entwurfsänderung zusätzlich auf eine standardisierte Kernmeldung.
13. Ein PDF kann anschließend auf ausdrückliche UI-Aktion lokal erzeugt werden. Es wird nicht automatisch nach jeder Berechnung erstellt.

## 11. Rückwärtsbemessung

### Vorwärts

```text
Last fix + Randbedingungen fix/teilfix
→ Geometrie/Verbindungsmittel im Suchraum variieren
→ geeignete Verbindung auswählen
```

### Rückwärts

```text
aktuell berechnete Geometrie vollständig fix
→ ausschließlich Ft,d variieren
→ Grenzlast oder Last bei Zielausnutzung bestimmen
```

**Maximallast – IMPLEMENTIERT:** `_maximum_load_text` verwendet `last_result.input`, verdoppelt zunächst eine obere Lastgrenze und führt danach 60 Bisektionsschritte aus. Jeder Schritt ruft den echten Rechenkern und den Validator auf. Die gespeicherte Geometrie wird nicht optimiert. Die höchste Last, die zugleich rechnerisch bestanden und normativ zulässig ist, wird als `lastMaximumLoad` gespeichert.

**Last bei 90 % – IMPLEMENTIERT, mit Grenze:** `_load_for_target_utilization` variiert ebenfalls nur die Last und führt 60 Bisektionsschritte auf die maximale Ausnutzung aus. Anders als die Maximallastsuche ruft diese Funktion den ÖNORM-Validator nicht in jedem Schritt auf; sie setzt voraus, dass der aktuelle Ausgangsentwurf bereits gültig ist. Das Ergebnis wird ebenfalls unter `lastMaximumLoad` gespeichert, obwohl es semantisch eine Ziellast und nicht zwingend die Maximallast ist.

## 12. Variantenbewertung

Variantenvergleiche dürfen nur bereits von Python berechnete Varianten zurückgeben. Die UI kann Varianten voranzeigen und über `adopt_variant` als aktuellen Entwurf übernehmen. Die Empfehlung im Serializer ist ein deterministischer Textbaustein, der auf der Python-Rangfolge basiert; im Online-Chat kann das LLM dieselben Fakten natürlich formulieren.

Bekannte Grenze: `adopt_variant` ersetzt `state.parameters` durch den kompletten Input, aktualisiert aber die Menge `fixed_parameters` nicht ausdrücklich. Die Herkunftssemantik nach einer UI-Übernahme ist daher weniger sauber als bei einer Chatänderung.

## 13. Berichtserstellung

**IMPLEMENTIERT:** ReportLab erzeugt lokal entweder:

- einen A4-Berechnungsbericht mit Grundbedingungen, Konstruktion, Nachweisen, KI-Einschätzung, optionaler Tragfähigkeitsuntersuchung und Quellen oder
- einen A4-Querformat-Variantenbericht mit ausgewählten Varianten und Empfehlung.

Die Daten kommen ausschließlich aus dem serialisierten Snapshot. Der Bericht enthält keine vom LLM neu berechneten Werte. Varianten werden im UI per Checkbox für den Bericht ausgewählt; der Chat-Agent besitzt dafür kein Tool. Der Satz „Nimm die drei wichtigsten Varianten in den Bericht“ ist deshalb **nicht als Chataktion implementiert**. Ohne UI-Auswahl nimmt der Variantenbericht nur Variante 1 auf.

## 14. Datenschutz und API

### Lokal

- Python-Rechenkern, Validator und Optimierer,
- Material- und kleine Wissensbasis,
- React-/pywebview-Oberfläche,
- technische SVG-Darstellung,
- PDF-Erstellung und lokale Dateien,
- Kompakt- und manuelle Berechnung,
- lokaler Fallback-Dialog.

### Extern bei aktivem LLM

An die OpenAI Responses API gehen:

- die Systemanweisung,
- die aktuelle Benutzernachricht,
- der bisherige Online-`message_history`-Chatverlauf,
- `agent_context` als JSON: aktueller/vorheriger Entwurf, Ergebniszusammenfassungen einschließlich Inputs, Optimierungsstatistik, Fixierungen/Herkunft, Fehlstellen, Anschlussfall, Varianten und Quellenmetadaten,
- nach Toolaufrufen die strukturierten Toolergebnisse; diese können vollständige Eingaben, Checks, Widerstände, Ausnutzungen und Validierungsfehler enthalten.

Normvolltexte und lokale PDF-Dateien werden nicht hochgeladen. Die kuratierten Quellenmetadaten können über Toolergebnisse übertragen werden. Kompakt- und manuelle Eingaben verwenden `execute_local_command` bzw. direkte Berechnung und lösen selbst keinen LLM-Aufruf aus. Die UI-Anzeige „Speicherstatus lokal“ darf deshalb nicht als Aussage „alle Daten bleiben lokal“ verstanden werden, sobald der Online-Agent genutzt wird.

## 15. Sicherheitsgrenzen und Halluzinationen

### Vorhandene Schutzmechanismen

- geschlossenes Tool-Schema und `additionalProperties: false` bei zentralen Agentenaktionen,
- Allowlist für Parameter und Aliasnormalisierung,
- Prüfung, ob angebliche User-Werte wirklich im Usertext erkennbar sind,
- `USER_FIXED`-Schutz vor AI-/Knowledge-Updates,
- deterministische Materialdaten, Berechnung und Validierung,
- strukturierte Ergebnisse und UI-Snapshots direkt aus Python,
- Begrenzung auf acht Toolschleifen pro Agentenantwort,
- klarer Scope im Prompt und lokale Abweisung anderer Verbindungstypen,
- Tests für Agent, Dialog, Optimierung, Normfälle und Rückwärtsbemessung.

### Was ein halluzinierendes LLM nicht direkt ändern kann

Es kann nicht über ein freigegebenes Feld Widerstand, Ausnutzung, `passed`, maßgebenden Check oder Validatorstatus setzen. Diese Werte werden neu durch Python erzeugt.

### Verbleibende Risiken

- Das LLM kann korrekte Toolresultate sprachlich falsch, unvollständig oder zu sicher zusammenfassen.
- Die Toolfelder `constraints` bei Optimierung/Variantenvergleich sind offen als Objekt beschrieben; die Python-Allowlist begrenzt erst beim Dispatch.
- Quellenmetadaten und Normimplementierung sind manuell gepflegt und können veralten oder fehlerhaft sein.
- Nicht verifizierte Validatorpunkte blockieren derzeit die Gesamtzulässigkeit nicht.
- Fachformeln und nationale Regeln benötigen unabhängige fachliche Validierung; der Modulkommentar warnt ausdrücklich vor Produktivfreigabe.
- Der lokale Regex-Modus ist enger als das LLM und versteht nicht beliebige Sprache.
- Es gibt keine formale Freigabe, Signatur, Audit-Trail-Persistenz oder Benutzerrollen.

## 16. Vergleich mit Excel

| Aspekt | sehr gutes automatisiertes Excel-Blatt | aktueller KI-Prototyp |
|---|---|---|
| Eingabe | strukturierte Zellen/Formulare | Chat, Kompakt- oder Manuellmodus |
| nötiges Benutzerwissen | Kenntnis von Eingabefeldern und Modelllogik | natürliche Anforderungen möglich; Pflichtangaben bleiben nötig |
| Berechnung | deterministisch, auditierbar | ebenfalls deterministisch in Python |
| Varianten | Tabellen, Makros oder Solver möglich | eingebauter diskreter Suchraum und kuratierte Varianten |
| Optimierung | Solver/Makros können leistungsfähiger sein | sprachlich wählbare, aber heuristische Ziele |
| Entwurfsziele | explizite Zielfunktion | natürliche Formulierung wird auf feste Ziele abgebildet |
| Interaktion | zell-/formularorientiert | kontextbezogene Folgefragen und Änderungen |
| Rückwärtsbemessung | problemlos programmierbar | eingebaut für aktuelle Geometrie |
| Interpretation | meist Dokumentation/Formelkommentare | kurze kontextbezogene Erläuterung durch LLM/Templates |
| Empfehlungen | als Regeln/Makros implementierbar | Rangfolge aus Python, natürliche Begründung |
| Dokumentation | sehr transparent bei guter Pflege | strukturierter PDF-Bericht; Prototypstatus |
| Flexibilität | sehr hoch für bekannte Modelle | höher bei Sprache, derzeit enger fachlicher Scope |

Der Mehrwert gegenüber einem **sehr guten** Excel-Modell liegt nicht in „besserer Mathematik“. Er liegt in der sprachlichen Zugangsschicht, kontextbezogenen Folgeinteraktion, Orchestrierung mehrerer deterministischer Funktionen und der leichteren Begründung bereits berechneter Varianten. Excel kann dieselben Formeln, Solverläufe und Berichte abbilden und ist bei Zellprüfung oft transparenter. Der Prototyp zeigt deshalb vor allem ein anderes Bedien- und Orchestrierungsmodell.

### Warum überhaupt KI?

Deterministisch besser: Formeln, Tragfähigkeiten, Materialtabellen, Validierung, Normchecks, Ranking bei festgelegter Zielfunktion und Berichtszahlen.

LLM-vorteilhaft: unstrukturierte Sprache, Intent- und Zielerkennung, kontextbezogene Rückfragen, flexible Folgefragen, Auswahl des passenden Engineering-Tools und natürliche Erklärung. Berichtstext ist grundsätzlich ein geeigneter LLM-Anwendungsfall, im aktuellen PDF aber nur teilweise über die gespeicherte Empfehlung eingebunden.

## 17. Grenzen

### Technische Grenzen

- nur zugbeanspruchter Stabdübel-Zuglaschenstoß;
- diskreter, eng festgelegter Suchraum;
- keine echte Kosten-, Fertigungs- oder CO₂-Optimierung;
- kein generischer Solver und keine weiteren Verbindungsmittel;
- technische Darstellung ist SVG-basiert und aktuell in Überarbeitung.

### Wissenschaftliche/normative Grenzen

- keine vollständige Normabdeckung;
- `a3,c`, `a4,t` und Holz-Bohrlochdurchmesser nicht separat verifiziert;
- Ein-Blech-Fall rechnerisch vorhanden, im aktuellen österreichischen Profil wegen zwei statt mindestens vier Scherflächen unzulässig;
- Referenzformeln, Rundung, Sonderfälle und Anwendungsgrenzen müssen extern fachlich validiert werden;
- keine automatische Normänderung oder Versionsmigration.

### Prototyp-Grenzen

- LLM-Ausgaben können variieren und API-Verfügbarkeit ist extern abhängig;
- lokaler Modus ist nur eng regelbasiert;
- Bericht und UI sind Präsentationsfunktionen, keine prüffähige Statiksoftware;
- keine persistente Projektverwaltung oder revisionssichere Nachweiskette.

### Teststatus dieser Analyse

Der aktuelle Referenz-Optimierungslauf ließ sich ausführen. Der vollständige Testlauf ist im aktuellen Arbeitsstand **nicht grün bestätigt**: Der erste `pytest`-Aufruf verwendete einen unpassenden Importpfad, das Conda-Python enthält kein `pytest`, und ein expliziter Python-3.12-Lauf wurde nach 8:09 Minuten mit 9 bestandenen und 3 fehlgeschlagenen Tests abgebrochen. Die beobachteten Fehler betrafen Gesamt-Dübelzahl, Zurücksetzen eines neuen Entwurfs und den erwarteten Wortlaut beim Ein-Blech-Fall. Die Antworten im Fehlerprotokoll zeigen, dass in dieser Umgebung der konfigurierte Online-Agent beteiligt war; dadurch ist zumindest ein Teil der Dialogtests modellabhängig. Es wurden auftragsgemäß keine Tests oder Produktdateien korrigiert.

## 18. Weiterentwicklung

Die folgenden Punkte sind **GEPLANT / NOCH NICHT IMPLEMENTIERT** und passen zur bestehenden Architektur:

1. unabhängige fachliche Verifikation und vollständigeres ÖNORM-Profil;
2. separate Modellierung aller relevanten Rand-/Endabstände und Bohrlochgrößen;
3. Kosten-, Fertigungs-, Material- und CO₂-Zielfunktionen;
4. weitere Verbindungstypen, etwa Schrauben, eingeklebte Gewindestangen und Schrägverschraubungen;
5. Vergleich unterschiedlicher Verbindungssysteme statt nur Varianten eines Stabdübelsystems;
6. echtes, versioniertes Norm-Retrieval mit überprüfbaren Fundstellen und Lizenzkonzept;
7. revisionssichere Projekte, Audit-Trail und fachliche Freigabeworkflows;
8. agentenseitiges Berichtstool und kontrollierte narrative Berichtserstellung;
9. automatisierte visuelle Konsistenztests für technische Darstellungen;
10. optionales lokales LLM für sensible Projektkontexte;
11. systematische Evaluation von Extraktionsfehlern, Toolwahl und sprachlichen Halluzinationen;
12. Ausbau zu einem Forschungs-Copiloten, der Variantenstudien strukturiert dokumentiert, ohne die deterministische Fachrechnung zu ersetzen.

## Anhang A: Technischer Präsentationsworkflow

| User-Schritt | Intent/Agentenaufgabe | Python/Tool | State/Ergebnis |
|---|---|---|---|
| „140 kN GL24h 200 × 240, möglichst wenige“ | Parameter/Ziel erkennen | `update_design`, `get_missing_information` | Last/Holz/Querschnitt fix; Ziel `MIN_FASTENER_COUNT`; NK/Dauer fehlen |
| „NK1, mittel.“ | Restparameter speichern | `update_design`, dann `optimize_design` | Materialwerte/`kmod`; Variantenlauf und Auswahl |
| „Warum diese Variante?“ | aktuelle Fakten laden und erklären | `explain_calculation`/`compare_variants` | keine technische Änderung |
| „Probier Ø12.“ | explizite Änderung | `update_design`, Berechnung/Optimierung | Ø12 wird user-fixed; andere freie Größen dürfen variieren |
| „Geht es auch mit einem Blech?“ | Anschlussfall ändern/What-if | `update_design`, Rechenkern/Validator | Holz–Stahl–Holz wird gerechnet, aber österreichisch nicht zulässig |
| „Welche Variante würdest du nehmen?“ | berechnete Varianten bewerten | `compare_variants` | Empfehlung ohne neue technische Zahlen |
| „Wie viel hält die aktuelle Verbindung maximal?“ | Rückwärtsbemessung | `calculate_maximum_load` | nur Last variiert; Geometrie bleibt fix |
| „Welche Last entspricht 90 %?“ | Zielausnutzung | lokaler `_load_for_target_utilization`; im Online-Toolset kein eigenes benanntes Tool | nur Last variiert; Ergebnis im Maximallastfeld gespeichert |
| „Nimm die drei wichtigsten Varianten in den Bericht.“ | gewünschte Berichtsauswahl | **kein Agenten-Tool vorhanden** | muss derzeit über UI-Checkboxen erfolgen |

## Anhang B: Codefundstellen

- Agent/Tools: `ai/agent.py`
- Technical State, Dialog, Vor-/Rückwärtsbemessung: `ai/assistant.py`
- Prompt/Scope: `ai/prompts/stabduebel_system.txt`
- Optimierung/Ranking: `ai/optimizer.py`
- Rechenkern: `calculations/stabduebel.py`
- Validator: `calculations/oenorm_validation.py`
- Materialien: `infopol/materials/`
- Wissens-/Quellenbasis: `knowledge/sources.py`
- UI-Grenze: `desktop/bridge.py`
- Snapshots/Visualisierungsmodell: `desktop/serializers.py`
- Bericht: `desktop/reports.py`
- React-Oberfläche: `frontend/src/App.tsx`
- technische SVGs: `frontend/src/visualization/`
