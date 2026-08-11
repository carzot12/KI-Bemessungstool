from __future__ import annotations

"""Normative Bemessungsbeiwerte für die unterstützten Holzprodukte.

Quelle: ÖNORM EN 1995-1-1:2019, Tabelle 3.1 (kmod) und Tabelle 2.3
(Teilsicherheitsbeiwerte), übernommen durch ÖNORM B 1995-1-1:2023.
"""

from collections.abc import Mapping

from .timber import TimberMaterial


SERVICE_CLASSES = (1, 2, 3)
LOAD_DURATION_CLASSES = ("ständig", "lang", "mittel", "kurz", "sehr kurz")
KMOD_SOURCE = "ÖNORM EN 1995-1-1:2019, Tabelle 3.1"
GAMMA_M_SOURCE = "ÖNORM EN 1995-1-1:2019, Tabelle 2.3"

# Tabelle 3.1 weist für Vollholz und Brettschichtholz dieselben Werte aus.
_KMOD_SOLID_TIMBER: Mapping[int, Mapping[str, float]] = {
    1: {"ständig": 0.60, "lang": 0.70, "mittel": 0.80, "kurz": 0.90, "sehr kurz": 1.10},
    2: {"ständig": 0.60, "lang": 0.70, "mittel": 0.80, "kurz": 0.90, "sehr kurz": 1.10},
    3: {"ständig": 0.50, "lang": 0.55, "mittel": 0.65, "kurz": 0.70, "sehr kurz": 0.90},
}
_KMOD_BY_PRODUCT = {
    "solid_timber": _KMOD_SOLID_TIMBER,
    "glulam": _KMOD_SOLID_TIMBER,
}

# Der bestehende Stabdübel-Rechenkern verwendet gamma_M für Verbindungen.
GAMMA_M_CONNECTIONS = 1.30


def normalize_load_duration(value: str) -> str:
    normalized = " ".join(value.strip().lower().replace("-", " ").split())
    aliases = {
        "ständig": "ständig",
        "staendig": "ständig",
        "ständige einwirkung": "ständig",
        "lang": "lang",
        "lange einwirkung": "lang",
        "lange lasteinwirkungsdauer": "lang",
        "mittel": "mittel",
        "mittlere einwirkung": "mittel",
        "mittlere lasteinwirkungsdauer": "mittel",
        "kurz": "kurz",
        "kurze einwirkung": "kurz",
        "kurze lasteinwirkungsdauer": "kurz",
        "sehr kurz": "sehr kurz",
        "sehr kurze einwirkung": "sehr kurz",
        "sehr kurze lasteinwirkungsdauer": "sehr kurz",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unbekannte Klasse der Lasteinwirkungsdauer '{value}'. "
            f"Zulässig sind: {', '.join(LOAD_DURATION_CLASSES)}."
        ) from exc


def get_kmod(
    material: TimberMaterial | str,
    service_class: int,
    load_duration_class: str,
) -> float:
    """Liefert kmod ausschließlich aus der implementierten ÖNORM-Tabelle."""
    product = material.product if isinstance(material, TimberMaterial) else material
    if product not in _KMOD_BY_PRODUCT:
        raise ValueError(f"Für die Materialgruppe '{product}' ist kein kmod hinterlegt.")
    if service_class not in SERVICE_CLASSES:
        raise ValueError("Die Nutzungsklasse muss 1, 2 oder 3 sein.")
    duration = normalize_load_duration(load_duration_class)
    return _KMOD_BY_PRODUCT[product][service_class][duration]


def get_connection_gamma_m() -> float:
    """Teilsicherheitsbeiwert für Verbindungen nach Tabelle 2.3."""
    return GAMMA_M_CONNECTIONS
