from __future__ import annotations

"""Zentraler, wiederverwendbarer Zugriff auf die Holzkennwerte."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


DEFAULT_TIMBER_DATA_PATH = Path(__file__).with_name("timber.json")
REQUIRED_STABDUEBEL_PROPERTIES = ("rho_k", "ft_0_k", "fv_k")


@dataclass(frozen=True, slots=True)
class TimberMaterial:
    """Eine Holzfestigkeitsklasse einschließlich aller JSON-Kennwerte."""

    grade: str
    product: str
    subtype: str
    properties: Mapping[str, Any]

    def value(self, property_name: str) -> float:
        """Gibt einen numerischen Kennwert zurück oder meldet fehlende Daten."""
        try:
            value = self.properties[property_name]
        except KeyError as exc:
            raise KeyError(
                f"Kennwert '{property_name}' fehlt für Holzklasse '{self.grade}'."
            ) from exc
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(
                f"Kennwert '{property_name}' der Holzklasse '{self.grade}' "
                "ist nicht numerisch."
            )
        return float(value)


class TimberMaterialRepository:
    """Lädt Vollholz- und Brettschichtholzklassen zentral aus timber.json."""

    def __init__(self, data_path: str | Path = DEFAULT_TIMBER_DATA_PATH) -> None:
        self.data_path = Path(data_path)
        self._materials = self._load()

    def grades(self) -> tuple[str, ...]:
        """Alle vorhandenen Klassen in der Reihenfolge der JSON-Datei."""
        return tuple(self._materials)

    def get(self, grade: str) -> TimberMaterial:
        """Liefert die Materialdaten einer Festigkeitsklasse."""
        try:
            return self._materials[grade]
        except KeyError as exc:
            available = ", ".join(self.grades())
            raise KeyError(
                f"Unbekannte Holzfestigkeitsklasse '{grade}'. "
                f"Verfügbar: {available}"
            ) from exc

    def _load(self) -> dict[str, TimberMaterial]:
        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Holzmaterialdatei nicht gefunden: {self.data_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ungültige Holzmaterialdatei {self.data_path}: {exc}"
            ) from exc

        materials: dict[str, TimberMaterial] = {}
        self._add_group(materials, raw.get("solid_timber"), "solid_timber", "")

        glulam = raw.get("glulam")
        if not isinstance(glulam, dict):
            raise ValueError("In timber.json fehlt der Bereich 'glulam'.")
        for subtype, grades in glulam.items():
            self._add_group(materials, grades, "glulam", subtype)

        if not materials:
            raise ValueError("timber.json enthält keine Holzfestigkeitsklassen.")
        return materials

    @staticmethod
    def _add_group(
        materials: dict[str, TimberMaterial],
        grades: object,
        product: str,
        subtype: str,
    ) -> None:
        if not isinstance(grades, dict):
            raise ValueError(f"In timber.json fehlt der Materialbereich '{product}'.")

        for grade, properties in grades.items():
            if grade in materials:
                raise ValueError(f"Doppelte Holzfestigkeitsklasse '{grade}'.")
            if not isinstance(properties, dict):
                raise ValueError(f"Ungültige Kennwerte für Holzklasse '{grade}'.")

            missing = [
                name for name in REQUIRED_STABDUEBEL_PROPERTIES
                if name not in properties
            ]
            if missing:
                raise ValueError(
                    f"Holzklasse '{grade}' enthält nicht alle für die "
                    f"Stabdübelbemessung benötigten Kennwerte: {', '.join(missing)}"
                )

            materials[grade] = TimberMaterial(
                grade=grade,
                product=product,
                subtype=subtype,
                properties=MappingProxyType(dict(properties)),
            )
