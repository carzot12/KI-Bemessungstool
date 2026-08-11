# Fachlicher Audit: Anzahl innenliegender Stahlbleche

Stand: 11.08.2026. Anwendungsfall: tragender Stabdübel-Zuglaschenstoß,
reine Zugbeanspruchung parallel zur Faser, Normprofil ÖNORM.

## Entscheidung

Der Aufbau mit **einem innenliegenden Stahlblech** ist als klar getrennte
rechnerische Teiluntersuchung nach ÖNORM EN 1995-1-1, Gleichung (8.11),
implementiert. Er bildet eine zweischnittige Holz-Stahl-Holz-Verbindung mit
zwei Scherflächen. Nach ÖNORM B 1995-1-1:2023, nationaler Ergänzung zu
Abschnitt 8.6 (1), muss eine tragende Stabdübelverbindung jedoch mindestens
vier Scherflächen besitzen. Der Ein-Blech-Aufbau wird deshalb niemals als
österreichisch zulässig ausgegeben.

Der bestehende Aufbau mit **zwei innenliegenden Stahlblechen und vier
Scherflächen** bleibt der einzige derzeit national zulässige Aufbau.

## Gegenüberstellung

| Thema | 1 innenliegendes Stahlblech | 2 innenliegende Stahlbleche |
|---|---|---|
| Scherflächen | 2 | 4 |
| Nationale Zulässigkeit für den tragenden Stabdübelfall | Nicht zulässig: Mindestanforderung 4 Scherflächen nicht erfüllt | Mindestanforderung erfüllt |
| Holzaufbau | Zwei Seitenhölzer, kein separates Mittelholz des bestehenden vierschnittigen Modells | Zwei Seitenhölzer und ein Mittelholz zwischen den Blechen |
| Lastpfad Stahl | Ein Blech trägt die Gesamtlast; je eine Scherfuge auf beiden Seiten | Symmetrisches Normbild mit F/2 je Blech und zwei beteiligten Scherfugen je Blech |
| Johansen-Grundmodell | ÖNORM EN 1995-1-1, (8.11): Stahlblech als Mittelteil einer zweischnittigen Verbindung | ÖNORM B, Bild NA.8.1-E1 und (NA.8.1-E1): kompatible Seitenholz-/Mittelholzscherfugen |
| Seitenholz | Zwei Seitenhölzer mit je halber Last; rechnerisch implementiert | Bestehendes Modell |
| Mittelholz | Nicht vorhanden; bestehender Mittelholz-Nettoquerschnitt und dessen Scherfugen sind nicht anwendbar | Vorhanden und im Rechenkern abgebildet |
| Stahlblechzug | Ein Blech unter Gesamtlast; rechnerisch implementiert | Bestehender Ansatz für zwei Bleche |
| Stahl-Lochleibung / Abscheren | Lastaufteilung auf ein Blech; rechnerisch implementiert | Bestehender, numerisch regressionsgesicherter Ansatz |
| Verbindungsmittel im Holz | (8.11) liefert zwar ein zweischnittiges Grundmodell, dieses hebt die nationale Vier-Scherflächen-Regel nicht auf | Bestehende Kombination kompatibler Scherfugen |
| `n_eff` und Mindestabstände | Grundsätzlich unverändert anwendbar | Bestehend anwendbar |
| Blockscheren Holz | Neue Bruchflächen für den anderen Holzaufbau erforderlich; bestehende Summation ist nicht anwendbar | Bestehender Aufbau nach Anhang A / MA |
| Blockversagen Stahl | Ein-Blech-Geometrie und Gesamtlast rechnerisch implementiert | Bestehender Ansatz |
| Gesamtergebnis | Bereits normativ unzulässig; keine Tragfähigkeitsoptimierung zulässig | Im derzeit verifizierten V1 unter weiteren bekannten Vorbehalten berechenbar |

## Geprüfte Quellen

- ÖNORM EN 1995-1-1:2019, Abschnitt 8.1.3: Scherfugen mehrschnittiger
  Verbindungen sind als Teile zweischnittiger Verbindungen zu betrachten;
  Versagensmechanismen müssen kompatibel sein.
- ÖNORM EN 1995-1-1:2019, Abschnitt 8.2.3, insbesondere (8.11):
  Stahlblech als Mittelteil einer zweischnittigen Verbindung.
- ÖNORM B 1995-1-1:2023, nationale Erläuterung zu 8.1.3, Bild
  NA.8.1-E1 und (NA.8.1-E1): vierschnittige Verbindung mit zwei
  innenliegenden Blechen; zwei Scherfugen je Blech und F/2 je Blech.
- ÖNORM B 1995-1-1:2023, nationale Ergänzung zu 8.6 (1): mindestens
  vier Scherflächen und mindestens zwei Stabdübel für eine tragende
  Verbindung.
- MA Köberl (2018), Abschnitt 2-3.3.2 und Gleichungen (2.8) bis (2.13):
  behandelt ausschließlich den vierschnittigen Aufbau mit zwei
  innenliegenden Stahlblechen. Sie liefert keine Freigabe für den
  Ein-Blech-Aufbau.

## Weitere Stahlblechanzahlen

ÖNORM B weist darauf hin, dass (NA.8.1-E1) für mehr als zwei Stahlbleche
sinngemäß zu erweitern ist. Das reicht für die aktuelle Implementierung nicht
aus: Im Eingabemodell fehlen individuelle Dicken aller Holzzwischenlagen,
die zugehörige Lastaufteilung und verifizierte Block-/Nettoquerschnittsmodelle.
Die MA behandelt diesen Aufbau nicht. Drei oder mehr Bleche werden deshalb
ebenfalls nicht freigeschaltet.

## Für eine spätere Erweiterung benötigt

Eine andere konstruktive Ein-Blech-Lösung könnte nur untersucht werden, wenn
sie trotz eines Blechs mindestens vier Scherflächen ausbildet. Dafür werden
mindestens benötigt:

1. ein eindeutiges Anschlussdetail mit Holzlagen, Blechlage und Lastpfad,
2. eine fachliche Bestätigung, dass dieses Detail die nationale
   Vier-Scherflächen-Regel erfüllt,
3. hergeleitete Nettoquerschnitte für alle Holzteile,
4. kompatible Johansen-Teilmodelle je Scherfuge,
5. Blockscheren- und Stahlblech-Blockversagensmodelle für genau diese
   Geometrie,
6. einen unabhängigen numerischen Referenzfall.

Bis dahin darf der Optimierer einen Ein-Blech-Aufbau berechnen und als
unzulässige Vergleichsgeometrie anzeigen, aber niemals als geeignete oder
erfüllte Lösung auswählen.
