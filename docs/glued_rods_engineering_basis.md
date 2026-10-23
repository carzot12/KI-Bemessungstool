# Eingeklebte Gewindestangen – Engineering-Basis

## Quellenlage und Anwendungsbereich

Der gesamte Ordner `Unterlagen` wurde nach deutschen und englischen
Bezeichnungen für eingeklebte Stäbe, Klebstoffe, Verankerung, Tragfähigkeit,
Abstände und Versagen durchsucht. Die für den Calculator unmittelbar
verwendbaren Quellen sind:

- `OENORM_B_1995-1-1_2023_08_15_de.pdf`, Anhang I (Seiten 198–202) und
  Anhang J (Seite 203): normative Anwendungsgrenzen, Fertigungsbedingungen,
  Widerstand, Mindestabstände, Mindesteinklebelänge und Klebfugenfestigkeit.
- `MA_Köberl_2018-02-28.pdf`, Seiten 17–20, 33–34 und 46–47:
  Eingaben, Rechenweg und Referenzergebnisse für stirnseitig, parallel zur
  Faser eingeklebte Gewindestangen unter axialem Zug.

Weitere Treffer in den Unterlagen behandeln überwiegend Grundlagen,
Versuche, Verstärkungen oder andere Verbindungsmittel. Sie wurden nicht als
zusätzliche Rechenregel verwendet.

Der implementierte Bereich ist auf axial beanspruchte, parallel zur Faser
eingeklebte metrische Gewindebolzen in Brettschicht- oder Balkenschichtholz
beschränkt. Zulässig sind nur Nenndurchmesser 6–30 mm, Nutzungsklasse 1 oder
2 und ein Klebstoffsystem mit gültigem europäischem Eignungsnachweis. Die
Ausführung muss zusätzlich der konkreten Klebstoffzulassung und den
Herstellerrichtlinien folgen.

## Technisches Modell

### Eingabeparameter

- Bemessungszugkraft `force_ed_kn`
- Holzquerschnitt `width_b_mm`, `height_h_mm`
- Gewindestange: `rod_diameter_mm`, `tensile_stress_area_mm2`,
  `rod_yield_strength_n_mm2`, `gamma_m1_steel`, Stabgüte
- Bohrung und Verklebung: `hole_diameter_mm`, `effective_embedment_mm`,
  `adhesive_system_qualified`
- Gruppe: `rod_count`, `rows`, `columns`, `spacing_a2_mm`, `edge_a4_c_mm`,
  `uniform_group_load_confirmed`
- Holz: Produkt, Festigkeitsklasse, `timber_tension_strength_n_mm2`,
  `k_mod`, `gamma_m_timber`, Nutzungsklasse
- Verbindung: `gamma_m_connection`

Die rechnerische Klebfugendicke ist `(d_bohrloch - d) / 2`. Die Unterlagen
geben dafür keine allgemeine zulässige Bandbreite an; der Calculator prüft
daher nur, dass das Bohrloch größer als der Stab ist. Die konkrete
Klebstoffzulassung bleibt zwingend.

### Geometrie und Grenzwerte

- `l_ef,min = max(0,5 d²; 10 d)`
- bei axialer Beanspruchung und Stäben parallel zur Faser:
  `a2 >= 5 d`, `a4,c >= 2,5 d`
- Klebfugenwerte sind nur bis `l_ef = 1000 mm` dokumentiert
- Nettofläche: `A_net = b h - n pi d_bohrloch² / 4`
- wirksame Holzfläche am Stabende: höchstens `36 d²` je Stab

### Material- und Bemessungsparameter

Die Festigkeits- und Sicherheitswerte werden explizit eingegeben. Der
Calculator besitzt keine versteckte Materialtabelle und erfindet keine
Klebstoffwerte. `f_k1,k` wird ausschließlich aus Tabelle NA.J.1 ermittelt:

- bis 250 mm: `4,00 N/mm²`
- über 250 bis 500 mm: `5,25 - 0,005 l_ef`
- über 500 bis 1000 mm: `3,5 - 0,0015 l_ef`

### Nachweise und Versagensmechanismen

Jeder Nachweis liefert `Ed`, `Rd`, Ausnutzung, Status, Quelle und die
maßgebenden Parameter:

1. Stahlversagen: `n fy,b Aef / gamma_M1`
2. Klebfugen-/Holzversagen entlang der Bohrlochwandung:
   `n pi d l_ef f_k1,k k_mod / gamma_M,Verbindung`
3. Holzversagen am Stabende/Nettoquerschnitt:
   `A_eff ft,0,k k_mod / gamma_M,Holz`

Bei mehreren Stäben muss Stahlversagen maßgebend sein, wenn eine
ungleichmäßige Gruppenbeanspruchung nicht ausgeschlossen werden kann. Diese
Normbedingung geht zusätzlich in den Gesamtstatus ein.

Nicht implementiert sind Abscheren, kombinierte Beanspruchung,
Queranschlüsse, Brand, Ermüdung, Gebrauchstauglichkeit, Dauerhaftigkeit und
Produktdetails einer konkreten Klebstoff-ETA.

## Referenzfall

Köberl, GL24h:

- Querschnitt 80 × 80 mm
- 4 Stangen M8, Anordnung 2 × 2
- Bohrloch 11 mm; rechnerische Klebfugendicke 1,5 mm
- `a2 = 40 mm`, `a4,c = 20 mm`
- `Aef = 36,6 mm²`, Stahlgüte 8.8, `fy,b = 640 N/mm²`
- `l_ef = 1000 mm`, `f_k1,k = 2,0 N/mm²`
- GL24h: `ft,0,k = 19,2 N/mm²`
- kurze Einwirkung, Nutzungsklasse 2: `k_mod = 0,9`
- `gamma_M,BSH = 1,25`, `gamma_M,Verbindung = 1,30`, `gamma_M1 = 1,00`

Dokumentierter Sollwiderstand: **83,2 kN**, maßgebend Holz-Nettoquerschnitt.
Der Calculator liefert ungerundet **83,218645 kN**, gerundet **83,2 kN**.
Abweichung zum publizierten gerundeten Wert: **0,018645 kN / 0,0224 %**.

Die Quelle gibt keine Einwirkung `Ed` vor, sondern ermittelt die Kapazität.
Der Regressionstest setzt für den Grenztest `Ed = 83,2 kN`; validiert wird
der unabhängig davon berechnete Widerstand.

## Variantengenerator

Es werden keine Durchmesser-, Längen- oder Anordnungsreihen erfunden. Der
Generator akzeptiert ausschließlich vom Aufrufer explizit übergebene,
quellenbelegte Kandidaten, berechnet sie deterministisch, verwirft
unzulässige Geometrien und sortiert nach maßgebendem Widerstand.

## Offene Punkte

- Konkretes Klebstoffprodukt samt gültiger ETA, Fertigungsparametern,
  Bohrloch-/Klebfugengrenzen, Temperatur- und Feuchtebedingungen fehlt.
- Für eine reale Gruppenbemessung ist projektspezifisch zu bestätigen, ob
  gleichmäßige Lastverteilung ausgeschlossen bzw. sichergestellt ist.
- Die Dokumente liefern für den Referenzfall keinen Bemessungswert der
  Einwirkung; validiert wird deshalb die ausgewiesene Tragfähigkeit.
- Für einen automatisch erzeugten Variantenraum fehlen dokumentierte
  Produktreihen. Kandidaten müssen aus einer konkreten Zulassung kommen.
