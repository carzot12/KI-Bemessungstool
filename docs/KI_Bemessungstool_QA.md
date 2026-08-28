# KI-Bemessungstool – Q&A-Spickzettel

## 1. Rechnet die KI die Verbindung selbst?

Nein. Tragfähigkeiten, Ausnutzungen, Materialwerte, Normchecks und der maßgebende Nachweis werden deterministisch in Python berechnet. Das LLM versteht Sprache, wählt kontrollierte Funktionen und formuliert Erklärungen.

## 2. Ist das einfach ChatGPT mit einer Statik-Prompt?

Nein. Es ist eine eigene Desktop-App, die optional ein GPT-Modell über die OpenAI API nutzt. Entscheidend sind Technical State, Tool-Schemas, Rechenkern, Validator und Optimierer außerhalb des Modells.

## 3. Welches Modell wird verwendet?

Standardmäßig `gpt-5-mini`. Die Modell-ID kann über `OPENAI_MODEL` geändert werden. Die App prüft den Modellzugriff beim Start des Online-Agenten.

## 4. Was passiert ohne API-Key?

Die App schaltet in einen lokalen, engeren Regelmodus. Berechnung, Optimierung, Materialien, UI und Berichte funktionieren weiterhin lokal; freie Sprachfähigkeit ist eingeschränkt.

## 5. Wo liegt der API-Key?

Nicht im Code. Er wird aus `OPENAI_API_KEY` oder auf macOS aus dem Schlüsselbunddienst „KI-Bemessungstool OpenAI“ geladen.

## 6. Was wird an OpenAI übertragen?

Im Online-Chat: Systemanweisung, Benutzertext, bisheriger Online-Chatverlauf, technischer Kontext und Toolergebnisse. Dazu können Eingaben, Ausnutzungen, Widerstände und Quellenmetadaten gehören. Lokale PDF-/Normdateien werden nicht hochgeladen.

## 7. Bleiben alle Daten lokal?

Nein, nicht im Online-Chat. Rechenkern, Optimierer, Materialien, UI und Berichte sind lokal; der LLM-Kontext geht an die externe API. Kompakt- und Manuellmodus rechnen lokal.

## 8. Was verhindert erfundene technische Zahlen?

Technische Zahlen sollen nur aus freigegebenen Tools kommen. Tool-Schemas, Parameter-Allowlist, User-Fixierungen und Python-Ergebnisse begrenzen den Agenten. Die UI liest Ergebniszahlen direkt aus Python, nicht aus dem Antworttext.

## 9. Kann die KI trotzdem halluzinieren?

Ja, sprachlich. Sie könnte ein korrektes Ergebnis falsch zusammenfassen. Sie kann über die freigegebenen Tools aber Widerstände, Ausnutzung oder Validatorstatus nicht direkt setzen.

## 10. Ist das Ergebnis normgerecht?

Es ist innerhalb eines engen implementierten ÖNORM-Profils geprüft. Es ist keine vollständige Normimplementierung und keine freigegebene Bemessungssoftware. Mehrere Details sind ausdrücklich noch nicht verifiziert.

## 11. Welche Normen sind berücksichtigt?

Vor allem ÖNORM EN 1995-1-1:2019 und nationale Ergänzungen aus ÖNORM B 1995-1-1:2023; Materialquellen verweisen außerdem auf EN 338 und EN 14080. IHBV-Unterlagen dienen als Kontroll-/Erklärquellen.

## 12. Werden Normtexte per KI durchsucht?

Nein. Es gibt nur eine kleine kuratierte Laufzeit-Wissensbasis mit Aussagen und Quellenmetadaten. Kein Vektorindex, keine Embeddings und kein Volltext-Retrieval sind implementiert.

## 13. Welche Punkte sind noch nicht verifiziert?

Ein separater unbeanspruchter Endabstand `a3,c`, ein beanspruchter Randabstand `a4,t` und ein separater Holz-Bohrlochdurchmesser fehlen im V1-Eingabemodell. Sie erscheinen als „NOCH NICHT VERIFIZIERT“.

## 14. Blockiert „NOCH NICHT VERIFIZIERT“ die Zulässigkeit?

Derzeit nein. Im Code blockiert nur der Status `FAILED`. Das ist eine wichtige Grenze: „zulässig“ bedeutet nur zulässig im implementierten Profil.

## 15. Welche Verbindung wird unterstützt?

Nur ein zugbeanspruchter Stabdübel-Zuglaschenstoß mit ein oder zwei innenliegenden Stahlblechen. Schrauben, Nägel, Querkräfte, Biegeträger oder andere Systeme sind nicht freigegeben.

## 16. Ist der Ein-Blech-Fall implementiert?

Rechnerisch ja: Holz–Stahl–Holz, zwei Scherfugen und ein eigener Fall nach Gleichung (8.11). Im aktuellen österreichischen Validator ist er wegen weniger als vier Scherflächen immer gesamtunzulässig.

## 17. Warum wird ein unzulässiger Ein-Blech-Fall überhaupt gerechnet?

Damit Teilnachweise und der Modellunterschied transparent untersucht werden können. Der Optimierer darf ihn berechnen, aber nicht als österreichisch zulässige Lösung auswählen.

## 18. Was variiert der Optimierer?

Dübel-Ø, `n`, `m`, Blechzahl, Blechdicke und – sofern nicht fixiert – die Holzschichtaufteilung. Abstände werden bei freien Durchmessern aus dem definierten Suchraster abgeleitet.

## 19. Welche Durchmesser werden untersucht?

Automatisch Ø8, 10, 12, 16, 20 und 24 mm. Für die Empfehlung werden Ø12 und Ø16 bevorzugt, außer der Benutzer fixiert einen anderen unterstützten Durchmesser.

## 20. Wie groß ist der Variantenraum?

Er hängt von Querschnitt und Fixierungen ab. Beim 200-mm-Referenzquerschnitt entstehen theoretisch 4.800 Schleifenkombinationen; im aktuellen Referenzlauf waren 4.560 tatsächlich berechenbar und 413 für 140 kN feasible.

## 21. Was bedeutet „feasible“?

Die Variante wurde berechnet, besteht die implementierte Norm-/Geometrievalidierung, erfüllt alle Rechenkernchecks und liegt innerhalb der gesetzten Ausnutzungsgrenzen.

## 22. Was bedeutet „wirtschaftliche Empfehlung“?

Eine heuristische Rangfolge: unter anderem weniger Bleche, weniger Dübel, bevorzugte Durchmesser, Nähe zu 85 % Ausnutzung und Verbindungsfläche. Es ist keine Kostenrechnung.

## 23. Kann der Benutzer Werte sperren?

Ja. Eindeutig genannte Werte werden `USER_FIXED`. Der Optimierer darf sie nicht ändern. Frühere Optimiererwerte bleiben dagegen bei einer neuen Optimierung variabel.

## 24. Was passiert bei „Probier Ø12“?

Ø12 wird als ausdrückliche Vorgabe gespeichert und neu gerechnet. Last, Holz, Querschnitt und andere User-Vorgaben bleiben erhalten; nicht fixierte Anordnung, Blech- und Schichtgrößen dürfen weiter optimiert werden.

## 25. Wie funktioniert die Maximallast?

Die aktuelle berechnete Geometrie wird vollständig übernommen. Nur die Last wird erhöht und anschließend in 60 Bisektionsschritten eingegrenzt. Jeder Maximallast-Schritt verwendet Rechenkern und Validator.

## 26. Kann die Rückwärtsbemessung heimlich eine bessere Geometrie wählen?

Nein. Die Maximallastfunktion verwendet ausdrücklich den Input des aktuellen Ergebnisses und variiert nur `force_ed_kn`.

## 27. Wie wird die Last bei 90 % Ausnutzung bestimmt?

Ebenfalls per Bisektion bei unveränderter Geometrie. Diese Funktion richtet sich nach der maximalen Rechenkern-Ausnutzung; sie führt im Gegensatz zur Maximallastsuche nicht in jedem Schritt nochmals den Validator aus.

## 28. Was ist besser als Excel?

Nicht die Mathematik. Der Mehrwert ist natürliche Sprache, kontextbezogene Folgefragen, flexible Tool-Orchestrierung und verständliche Erklärung. Ein gutes Excel kann genauso normgerecht rechnen und optimieren.

## 29. Was kann Excel möglicherweise besser?

Direkte Zell-/Formeltransparenz, etablierte Prüfroutinen, einfache manuelle Nachvollziehbarkeit und je nach Umsetzung sehr leistungsfähige Solver- und Berichtsfunktionen.

## 30. Warum nicht alles mit dem LLM lösen?

Weil Formeln, Normchecks und Validierung reproduzierbar und testbar sein müssen. Das LLM ist besonders nützlich für Sprache und Orchestrierung, nicht als Ersatz für deterministische Fachrechnung.

## 31. Kann das LLM neue Normwerte aus dem Gedächtnis einsetzen?

Es soll und darf das laut Prompt nicht. Materialwerte kommen aus der lokalen Datenbasis, technische Normwerte aus Python bzw. kuratierten Quellenmetadaten. Eine sprachliche Fehlbehauptung bleibt trotzdem als Restrisiko.

## 32. Wie werden Varianten in den Bericht übernommen?

Über Checkboxen in der Variantenoberfläche. Der Agent hat derzeit kein Tool, um auf den Chatbefehl „Nimm drei Varianten in den Bericht“ die Auswahl zu setzen.

## 33. Enthält der PDF-Bericht KI-erfundene Zahlen?

Nein. Zahlen und Nachweise stammen aus dem serialisierten Python-Snapshot. Der Empfehlungstext kann KI-/Template-geprägt sein, wird aber als Einschätzung gekennzeichnet.

## 34. Ist die technische Darstellung Teil der Berechnung?

Nein. Sie visualisiert den Ergebnis-Snapshot als SVG. Sie erzeugt keine Tragfähigkeit und darf keine eigene technische Wahrheit schaffen.

## 35. Welche Tests gibt es?

Tests decken unter anderem Rechenkernreferenzen, Materialien, ÖNORM-Validator, Ein-Blech-Fall, Optimierung, Durchmesser, State/Dialog, LLM-Toolschleife, DesktopBridge, Rückwärtsbemessung und Präsentationsworkflow ab.

## 36. Ist der aktuelle Teststand vollständig grün?

Nein, nicht bestätigt. Ein Python-3.12-Lauf wurde nach 8:09 Minuten mit 9 bestandenen und 3 fehlgeschlagenen Tests abgebrochen. Die Fehler betrafen Dialog-/State-Erwartungen; die Protokolle zeigen Beteiligung des konfigurierten Online-Agenten. Einzelne Kern- und Optimierungsläufe waren ausführbar.

## 37. Ist das Tool prüffähige Statiksoftware?

Nein. Es ist ein Forschungs-/Präsentationsprototyp. Normstand, Anwendungsgrenzen, Rundungsregeln und Sonderfälle müssen vor einem realen Einsatz fachlich validiert werden.

## 38. Was wäre der nächste sinnvolle Schritt?

Zuerst vollständige fachliche Verifikation und ein strengerer Validator. Danach Kosten-/CO₂-Ziele, weitere Verbindungssysteme, versioniertes Norm-Retrieval, Audit-Trail und lokale LLM-Optionen.

## 39. Was ist die wichtigste Sicherheitsbotschaft?

Das LLM steuert und erklärt; die technische Zahl entsteht außerhalb des LLM. Trotzdem bleibt menschliche fachliche Prüfung notwendig, weil auch Code und Normmodell unvollständig oder falsch sein können.

## 40. Was ist die prägnanteste Schlussantwort?

Der Prototyp zeigt KI als dialogfähige Engineering-Schnittstelle über einem deterministischen Kern – nicht als Ersatz für Statik, Norm und verantwortliche Fachplanung.
