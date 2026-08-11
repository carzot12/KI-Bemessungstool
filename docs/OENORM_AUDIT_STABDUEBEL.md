# Fachlicher Audit – Stabdübel-Zuglaschenstoß (V1)

Stand: 11.08.2026. Normprofil: `OENORM`. Anwendungsfall: Zug parallel zur
Faser (α = 0°), rechteckiger Holzquerschnitt, innenliegende Stahlbleche.

## Verwendete Projektunterlagen

- ÖNORM EN 1995-1-1:2019: Abschnitte 2.4.3, 3.1.3, 8.1.3, 8.2.3,
  8.5.1, 8.6, 10.4.4 und Anhang A; insbesondere Tabelle 8.5.
- ÖNORM B 1995-1-1:2023: nationale Erläuterung zu 8.1.3, nationale
  Ergänzungen zu 8.6 (1)/(2), Tabelle NA.8.4-E2 und nationale Ergänzung
  zu Anhang A, Gleichung (A.1).
- MA Köberl (2018): Abschnitt 2-3.3.2, Tabelle 2-9 und Gleichungen
  (2.6) bis (2.22) als fachliche Erläuterung.
- `Zugstoß_Stabdübelanschluss_Berechnungsbeispiel.pdf` nur als numerische
  Referenz. Dessen ausdrückliche DIN-Verweise, insbesondere für `d0`, wurden
  nicht als österreichische Regel übernommen.

## Gegenüberstellung des bestehenden Rechenkerns

| Thema | Aktueller Code | Norm/MA | Bewertung / Empfehlung |
|---|---|---|---|
| Materialwerte | `rho_k`, `ft_0_k`, `fv_k` kommen aus `timber.json` | Produkt-/Festigkeitsklassennormen; MA als Recheninput | Zentrale Datenübergabe bestätigt. Vollständige Primärquellenprüfung aller JSON-Klassen war nicht Gegenstand der vier priorisierten Unterlagen. |
| Bemessungswert Holz | `kmod * fk / gamma_M` | ÖNORM EN 1995-1-1, 2.4.3 | Formelstruktur bestätigt. Die konkrete Wahl `kmod=0,80` wird nicht aus Nutzungsklasse und Lasteinwirkungsdauer hergeleitet: noch nicht verifiziert. |
| `gamma_M` Holz | Eingabewert 1,30 | national festzulegender Wert | Wert ist plausibel im Referenzfall, aber die automatische Zuordnung zur Produktsituation fehlt: noch nicht verifiziert. |
| Lochleibung Holz | `0,082(1-0,01d)rho_k` | ÖNORM EN 1995-1-1, (8.32); MA (2.6) | Bestätigt für Kraft parallel zur Faser. |
| Fließmoment | `0,30 fu,k d^2,6` | ÖNORM EN 1995-1-1, (8.30); MA (2.7) | Bestätigt. |
| `n_eff` | Gleichung entsprechend (8.34) | ÖNORM EN 1995-1-1, (8.34); MA (2.12) | Bestätigt für Reihen in Faserrichtung. |
| Mehrschnittige Holztragfähigkeit | getrennte Scherfugen und kompatible Teilmodelle | ÖNORM B, Erläuterung zu 8.1.3; MA (2.8)–(2.13) | Aufbau für den festen vierschnittigen V1-Fall bestätigt. Eine Verallgemeinerung auf eine andere Blech-/Scherflächenzahl ist nicht belegt und wird von der neuen Zulässigkeitsprüfung verhindert. |
| Nettoquerschnitte Holz | getrennte Seiten-/Mittelholzmodelle, Referenzfaktoren | MA (2.14)/(2.15), Referenzrechnung | Numerisch regressionsgesichert; die besondere Reduktion `kt_e_side=0,40` ist aus den priorisierten ÖNORM-Stellen noch nicht eindeutig hergeleitet. |
| Stahlblech Zug / Verbindungsmittel / Blockversagen | Formeln nach EC3-Logik | MA (2.16)/(2.17) und Referenzrechnung | Numerisch regressionsgesichert. Vollständige Prüfung gegen ÖNORM EN 1993 war nicht Teil der vorgegebenen Normbasis: noch nicht vollständig verifiziert. |
| Blockscheren Holz | Zugmodell mit Faktor 1,50 | ÖNORM B, nationale Ergänzung zu Anhang A (A.1) | Abweichungsrisiko: 1,50 ist nur mit Sicherung gegen Aufspalten zulässig, sonst 1,00. Im Eingabemodell fehlt diese Angabe. Keine stille Formeländerung; empfohlen ist ein fachlich freizugebender boolescher Eingabeparameter und Standard 1,00. |
| Stabdübelstahl | S235 und `fu,k=360` | ÖNORM B, Tabelle NA.8.4-E2 | Referenzwert bestätigt. Die Konsistenz von Stahlsorte und frei eingebbarem `fu,k` wird noch nicht automatisch geprüft. |
| Lochdurchmesser `d0` | 13 mm; wird nur in Stahlblechnachweisen verwendet | ÖNORM EN 1995-1-1, 10.4.4 regelt das vorgebohrte Loch im Holz | Das Referenzbeispiel leitet 13 mm ausdrücklich aus DIN/NA ab. Da im Code kein eigener Holz-Bohrlochdurchmesser existiert, ist die österreichische Holztoleranz noch nicht verifizierbar. `d0` wurde nicht automatisch umgedeutet. |
| Dübellänge / Rücksprung | wirksame Seitenholzdicke wird algebraisch geprüft | Referenzrechnung / MA | Numerisch gesichert; Fertigungs- und Einbautoleranzen außerhalb 10.4.4 noch nicht vollständig verifiziert. |

`calculations/stabduebel.py` wurde bewusst nicht verändert. Der klar erkannte
Punkt zum Faktor 1,50 kann ohne Information zur Aufspaltsicherung nicht
fallbezogen korrekt entschieden werden.

## Automatisch implementierte Regeln

Das Modul `calculations/oenorm_validation.py` prüft deterministisch:

- `a1 >= 5d`, `a2 >= 3d`, `a3,t >= max(7d; 80 mm)` und
  `a4,c >= 3d` für α = 0° (Tabelle 8.5),
- `6 mm < d < 30 mm` sowie Warnung bei `d > 24 mm`,
- mindestens zwei Stabdübel und mindestens vier Scherflächen,
- Modellkonsistenz `Scherflächen = 2 * innenliegende Stahlbleche`,
- Einpassen der symmetrischen Dübellage in die Querschnittshöhe,
- Einpassen des modellierten Holz-/Stahl-Schichtaufbaus in die Breite,
- optional das Ergebnis aller sieben vorhandenen Tragfähigkeitsnachweise.

Separate Werte für `a3,c`, `a4,t` und das Holzbohrloch fehlen. Diese Checks
werden sichtbar als `NOCH NICHT VERIFIZIERT` geführt und machen keine
erfundene Annahme. Für die V1-Geometrie wird der vorhandene Wert `a4,c` als
symmetrischer oberer/unterer Randabstand verwendet; diese Eingabekonvention
ist im Querschnitts-Fit explizit benannt.

Der Optimierer berechnet weiterhin jede Variante mit
`calculate_stabduebel`, darf aber nur Varianten auswählen, die zusätzlich
`validation.admissible` erfüllen. Eine unzulässige feste Benutzervorgabe wird
nicht stillschweigend ersetzt. Insbesondere ist ein einzelnes innenliegendes
Stahlblech im festen V1-Modell nur zweischnittig und erfüllt damit die
österreichische Mindestanforderung von vier Scherflächen nicht.

## Tests und verbleibende Grenzen

Der Golden Test fixiert die bekannten Zwischenwerte und Widerstände des
140-kN-Beispiels. Negative Tests decken zu kleine Abstände, beide
Durchmessergrenzen, Warnbereich, zu wenige Dübel/Scherflächen, inkonsistente
Bleche/Scherflächen, nicht passende Höhe/Breite, hohe Zugkraft und zu kleinen
Nettoquerschnitt ab. Bestehende Material-, Parser- und Conversation-State-
Tests laufen gemeinsam mit.

Vor einer Freigabe bleiben insbesondere zu klären:

1. Aufspaltsicherung und Faktor 1,50/1,00 beim Holz-Blockscheren,
2. automatische Herleitung von `kmod` und `gamma_M`,
3. normative Herkunft von `kt_e_side=0,40`,
4. getrennte Lochdurchmesser für Holz und Stahl,
5. separate Eingaben für `a3,c` und `a4,t` sowie verfügbare Bauteillänge,
6. vollständige EC3-Prüfung der Stahlblechnachweise,
7. Konstruktionsregeln für andere als genau zwei innenliegende Bleche.

Die enum-basierte Auswahl `NormProfile.OENORM` bereitet eine spätere strikt
getrennte DIN-Implementierung vor. DIN-Regeln sind nicht implementiert und
werden aktuell nirgends zur Zulässigkeitsentscheidung herangezogen.
