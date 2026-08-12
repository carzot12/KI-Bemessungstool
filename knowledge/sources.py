from __future__ import annotations

"""Kleine Laufzeit-Wissensbasis ohne urheberrechtlich geschützte Volltexte.

Die Einträge sind Referenzen und verifizierte Metadaten. Normative Regeln und
Rechenwerte werden weiterhin ausschließlich durch die vorhandenen Python-
Module bereitgestellt. Die IHBV-Unterlagen sind Kontroll- und Erklärquellen.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceReference:
    topics: tuple[str, ...]
    document: str
    reference: str
    scope: str
    priority: int


IHBV_EXAMPLES = "IHBV Beispielsammlung ÖNORM, Ausgabe 2022"
IHBV_TABLES = "IHBV Holzbau-Kompakt Tabellenwerk, Ausgabe 2017"
OENORM_EN = "ÖNORM EN 1995-1-1:2019"
OENORM_B = "ÖNORM B 1995-1-1:2023"

SOURCE_REFERENCES: tuple[SourceReference, ...] = (
    SourceReference(
        ("mindestabstände", "a1", "a2", "a3", "a4"), OENORM_EN,
        "Tabelle 8.5", "Maßgebende Mindestabstände für Stabdübel", 1,
    ),
    SourceReference(
        ("johansen", "stahlblech", "zweischnittig"), OENORM_EN,
        "Abschnitt 8.2.3, Gleichung (8.11)",
        "Stahlblech als Mittelteil einer zweischnittigen Verbindung", 1,
    ),
    SourceReference(
        ("stabdübel", "scherflächen", "national"), OENORM_B,
        "Nationale Ergänzung zu Abschnitt 8.6",
        "Österreichische Zusatzanforderungen des implementierten Normprofils", 2,
    ),
    SourceReference(
        ("zuglaschenstoß", "stabdübel", "referenzbeispiel"),
        IHBV_EXAMPLES,
        "Abschnitt IV.2.1.1, Seiten IV.5-IV.7",
        "Zweischnittiger Holz-Holz-Zuglaschenstoß mit außenliegenden Holzlaschen; Kontrollfall, nicht der derzeit implementierte Stahlblechaufbau.",
        3,
    ),
    SourceReference(
        ("nettoquerschnitt", "zuglaschenstoß"), IHBV_EXAMPLES,
        "Abschnitt IV.2.1.1, Seite IV.7",
        "Nettoquerschnitte der Holzlaschen und des Mittelholzes", 3,
    ),
    SourceReference(
        ("stahlblechnachweis", "stahlblech", "mehrschnittig"), IHBV_EXAMPLES,
        "Abschnitt IV.2.1.3, Seiten IV.11-IV.15",
        "Mehrschnittige Holz-Stahlblech-Verbindung; Stahlblechnachweise werden auf EN 1993-1-1 und EN 1993-1-8 verwiesen", 3,
    ),
    SourceReference(
        ("gamma_m", "gamma_m_verbindung"), IHBV_TABLES, "Tabelle III.3",
        "Teilsicherheitsbeiwerte für Holz und Verbindungen", 4,
    ),
    SourceReference(
        ("kmod", "nutzungsklasse", "kled", "lasteinwirkungsdauer"),
        IHBV_TABLES, "Tabelle III.5",
        "Zuordnung von Nutzungsklasse und Klasse der Lasteinwirkungsdauer", 4,
    ),
    SourceReference(
        ("holzkennwerte", "c24", "zugfestigkeit", "rohdichte"),
        IHBV_TABLES, "Tabelle III.9", "Kennwerte von Vollholz", 4,
    ),
    SourceReference(
        ("mindestabstände", "a1", "a2", "a3", "a4", "stabdübel"),
        IHBV_TABLES, "Tabellen V.1-V.4",
        "Mindestabstände für Stabdübel und Passbolzen nach Durchmesser", 4,
    ),
    SourceReference(
        ("lochleibungsfestigkeit", "fh"), IHBV_TABLES, "Tabelle V.8",
        "Lochleibungsfestigkeit parallel zur Faserrichtung", 4,
    ),
    SourceReference(
        ("fließmoment", "myrk"), IHBV_TABLES, "Tabelle V.14",
        "Charakteristisches Fließmoment stiftförmiger Verbindungsmittel", 4,
    ),
    SourceReference(
        ("johansen", "versagensmechanismen", "holz-holz"),
        IHBV_TABLES, "Tabelle V.18",
        "Johansen-Modi für zweischnittige Holz-Holz-Verbindungen", 4,
    ),
    SourceReference(
        ("johansen", "versagensmechanismen", "stahlblech", "zweischnittig"),
        IHBV_TABLES, "Tabelle V.22",
        "Johansen-Modi bei innenliegendem Stahlblech", 4,
    ),
    SourceReference(
        ("tragfähigkeit", "mindestholzdicke", "holz-holz"),
        IHBV_TABLES, "Tabelle V.25",
        "Tabellierte Tragfähigkeit unter Einhaltung der Mindestholzdicken", 4,
    ),
    SourceReference(
        ("tragfähigkeit", "mindestholzdicke", "stahlblech"),
        IHBV_TABLES, "Tabelle V.29",
        "Holz-Stahlblech-Verbindungen; Kontrollwerte und Mindestholzdicken", 4,
    ),
    SourceReference(
        ("n_eff", "wirksame verbindungsmittelanzahl"),
        IHBV_TABLES, "Tabelle V.34",
        "Wirksame Verbindungsmittelanzahl in Abhängigkeit von a1", 4,
    ),
)


# Abgelesene Referenzwerte aus IV.2.1.1. Sie dienen nur Regression und
# Quellenvergleich, nicht als Laufzeit-Ersatz für Rechenformeln.
IHBV_ZUGLASCHENSTOSS_2022 = {
    "connection": "Holz-Holz, außenliegende Holzlaschen, zweischnittig",
    "implemented_connection": False,
    "force_ed_kn": 60.0,
    "timber_grade": "C24",
    "middle_section_mm": (100.0, 160.0),
    "outer_lamella_section_mm": (65.0, 160.0),
    "dowel_diameter_mm": 12.0,
    "dowel_steel_grade": "S235",
    "service_class": 2,
    "load_duration_class": "mittel",
    "k_mod": 0.80,
    "gamma_m": 1.30,
    "gamma_m_connection": 1.30,
    "rho_k_kg_m3": 350.0,
    "ft_0_k_n_mm2": 14.5,
    "spacings_mm": {"a1": 60.0, "a2": 70.0, "a3_t": 100.0, "a4_c": 45.0},
    "fh_0_k_n_mm2": 25.3,
    "my_rk_nmm": 6.91e4,
    "fv_rk_per_fastener_shear_plane_kn": 7.45,
    "fv_rd_per_fastener_shear_plane_kn": 4.58,
    "n_eff": 3.35,
    "connection_resistance_kn": 61.4,
    "connection_utilization": 0.98,
    "outer_net_area_mm2": 8.84e3,
    "outer_net_utilization": 0.57,
    "middle_net_area_mm2": 1.36e4,
    "middle_net_utilization": 0.49,
}


def find_sources(topic: str) -> tuple[SourceReference, ...]:
    normalized = topic.casefold().replace("ß", "ss").replace("-", "_").strip()
    return tuple(
        reference for reference in SOURCE_REFERENCES
        if any(
            normalized in item.casefold().replace("ß", "ss")
            or item.casefold().replace("ß", "ss") in normalized
            for item in reference.topics
        )
    )


def source_summary(topic: str) -> str:
    references = find_sources(topic)
    if not references:
        return ""
    return "; ".join(
        f"{item.document}, {item.reference} ({item.scope})"
        for item in references
    )
