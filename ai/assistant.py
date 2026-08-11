from __future__ import annotations

"""Einfacher V1-Assistent: Sprache, Zustand, Material und Rechenaufruf."""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from calculations.stabduebel import StabduebelInput, StabduebelResult
from infopol.materials import TimberMaterialRepository

from .optimizer import OptimizationResult, optimize_stabduebel


PROMPT_PATH = Path(__file__).parent / "prompts" / "stabduebel_system.txt"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "force_ed_kn": {"type": ["number", "null"]},
        "timber_grade": {"type": ["string", "null"]},
        "dowel_diameter_d_mm": {"type": ["number", "null"]},
        "rows_parallel_n": {"type": ["integer", "null"]},
        "rows_perpendicular_m": {"type": ["integer", "null"]},
        "max_utilization": {"type": ["number", "null"]},
        "minimize_fasteners": {"type": "boolean"},
        "explain_governing": {"type": "boolean"},
    },
    "required": [
        "force_ed_kn",
        "timber_grade",
        "dowel_diameter_d_mm",
        "rows_parallel_n",
        "rows_perpendicular_m",
        "max_utilization",
        "minimize_fasteners",
        "explain_governing",
    ],
    "additionalProperties": False,
}


@dataclass(slots=True)
class ConversationState:
    parameters: dict[str, float | int | str] = field(default_factory=dict)
    fixed_parameters: set[str] = field(default_factory=set)
    max_utilization: float = 1.0
    minimize_fasteners: bool = False
    last_result: StabduebelResult | None = None
    last_optimization: OptimizationResult | None = None


@dataclass(frozen=True, slots=True)
class AssistantReply:
    text: str
    result: StabduebelResult | None
    used_llm: bool


class StabduebelAssistant:
    def __init__(self) -> None:
        self.state = ConversationState()
        self.materials = TimberMaterialRepository()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def reset(self) -> None:
        self.state = ConversationState()

    def respond(self, user_text: str) -> AssistantReply:
        if not user_text.strip():
            raise ValueError("Bitte eine Anforderung eingeben.")

        extracted, used_llm = self._extract(user_text)
        self._apply(extracted)

        if extracted["explain_governing"]:
            return AssistantReply(self._explain_governing(), self.state.last_result, used_llm)

        missing = [
            label
            for key, label in (
                ("force_ed_kn", "Bemessungslast"),
                ("timber_grade", "Holzfestigkeitsklasse"),
            )
            if key not in self.state.parameters
        ]
        if missing:
            return AssistantReply(
                "Für die Berechnung fehlt noch: " + ", ".join(missing) + ".",
                None,
                used_llm,
            )

        base_input = self._build_input()
        optimization = optimize_stabduebel(
            base_input,
            fixed_parameters=self.state.fixed_parameters,
            max_utilization=self.state.max_utilization,
            minimize_fasteners=self.state.minimize_fasteners,
        )
        self.state.last_optimization = optimization
        if optimization.selected is None:
            self.state.last_result = None
            return AssistantReply(optimization.message, None, used_llm)

        selected = optimization.selected
        self.state.last_result = selected.result
        # Die gefundene Konfiguration wird zum aktuellen Entwurf, bleibt aber
        # veränderbar, sofern der Benutzer sie nicht ausdrücklich festgelegt hat.
        self.state.parameters["rows_parallel_n"] = selected.input.rows_parallel_n
        self.state.parameters["rows_perpendicular_m"] = selected.input.rows_perpendicular_m
        self.state.parameters["dowel_diameter_d_mm"] = selected.input.dowel_diameter_d_mm
        return AssistantReply(
            self._format_result(selected.result, selected.fastener_count, optimization),
            selected.result,
            used_llm,
        )

    def _extract(self, text: str) -> tuple[dict[str, Any], bool]:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                state_context = {
                    "parameters": self.state.parameters,
                    "fixed_parameters": sorted(self.state.fixed_parameters),
                    "max_utilization": self.state.max_utilization,
                }
                response = client.responses.create(
                    model=MODEL,
                    instructions=self.system_prompt,
                    input=(
                        "Aktueller Entwurfszustand:\n"
                        f"{json.dumps(state_context, ensure_ascii=False)}\n\n"
                        f"Neue Benutzereingabe:\n{text}"
                    ),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "stabduebel_parameter_update",
                            "strict": True,
                            "schema": EXTRACTION_SCHEMA,
                        }
                    },
                )
                return self._validate_extraction(json.loads(response.output_text)), True
            except ImportError as exc:
                raise RuntimeError(
                    "OPENAI_API_KEY ist gesetzt, aber das Paket 'openai' fehlt."
                ) from exc
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise RuntimeError(f"Ungültige strukturierte KI-Antwort: {exc}") from exc

        return self._fallback_extract(text), False

    @staticmethod
    def _validate_extraction(data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict) or set(data) != set(EXTRACTION_SCHEMA["properties"]):
            raise ValueError("Die KI-Antwort entspricht nicht dem erwarteten Schema.")
        return data

    def _fallback_extract(self, text: str) -> dict[str, Any]:
        """Eng begrenzte Demo-Erkennung, falls kein API-Schlüssel gesetzt ist."""
        normalized = text.lower().replace(",", ".")
        data: dict[str, Any] = {
            "force_ed_kn": None,
            "timber_grade": None,
            "dowel_diameter_d_mm": None,
            "rows_parallel_n": None,
            "rows_perpendicular_m": None,
            "max_utilization": None,
            "minimize_fasteners": bool(re.search(r"weniger|möglichst wenig", normalized)),
            "explain_governing": bool(
                re.search(r"warum|weshalb", normalized)
                and re.search(r"maßgeb|nachweis", normalized)
            ),
        }

        force = re.search(r"(\d+(?:\.\d+)?)\s*kn\b", normalized)
        if force:
            data["force_ed_kn"] = float(force.group(1))

        grade_names = sorted(self.materials.grades(), key=len, reverse=True)
        grade_match = re.search(
            r"\b(" + "|".join(map(re.escape, grade_names)) + r")\b",
            text,
            flags=re.IGNORECASE,
        )
        if grade_match:
            canonical = next(
                grade for grade in grade_names
                if grade.lower() == grade_match.group(1).lower()
            )
            data["timber_grade"] = canonical

        diameter = re.search(r"(?:ø|⌀|durchmesser|dübel)\s*(\d+(?:\.\d+)?)", normalized)
        if diameter:
            data["dowel_diameter_d_mm"] = float(diameter.group(1))

        utilization = re.search(
            r"(?:max(?:imal)?\s*)?(\d+(?:\.\d+)?)\s*%\s*(?:ausnutzung)?",
            normalized,
        )
        if utilization:
            data["max_utilization"] = float(utilization.group(1)) / 100.0

        return data

    def _apply(self, extracted: dict[str, Any]) -> None:
        for key in (
            "force_ed_kn",
            "timber_grade",
            "dowel_diameter_d_mm",
            "rows_parallel_n",
            "rows_perpendicular_m",
        ):
            value = extracted.get(key)
            if value is not None:
                self.state.parameters[key] = value
                self.state.fixed_parameters.add(key)

        if extracted.get("max_utilization") is not None:
            maximum = float(extracted["max_utilization"])
            if not 0.0 < maximum <= 1.0:
                raise ValueError("Die maximale Ausnutzung muss zwischen 0 und 100 % liegen.")
            self.state.max_utilization = maximum
        if extracted.get("minimize_fasteners"):
            self.state.minimize_fasteners = True

    def _build_input(self) -> StabduebelInput:
        defaults = asdict(StabduebelInput())
        defaults.update(self.state.parameters)

        grade = str(defaults["timber_grade"])
        try:
            material = self.materials.get(grade)
        except KeyError as exc:
            raise ValueError(f"Holzfestigkeitsklasse '{grade}' ist nicht vorhanden.") from exc
        defaults.update(
            rho_k_kg_m3=material.value("rho_k"),
            ft_0_k_n_mm2=material.value("ft_0_k"),
            fv_k_n_mm2=material.value("fv_k"),
        )
        return StabduebelInput(**defaults)

    def _explain_governing(self) -> str:
        result = self.state.last_result
        if result is None:
            return "Es liegt noch kein berechnetes Ergebnis vor, das ich erklären kann."
        governing = result.governing_check
        next_check = sorted(result.checks, key=lambda check: check.utilization, reverse=True)[1]
        return (
            f"„{governing.name}“ ist maßgebend, weil der Rechenkern dafür mit "
            f"η = {governing.utilization:.2f} die höchste Ausnutzung aller Nachweise "
            f"berechnet hat. Der nächsthöhere Wert ist η = {next_check.utilization:.2f} "
            f"bei „{next_check.name}“. Es wurde keine Tragfähigkeit durch die KI berechnet."
        )

    def _format_result(
        self,
        result: StabduebelResult,
        fastener_count: int,
        optimization: OptimizationResult,
    ) -> str:
        data = result.input
        status = "erfüllt" if result.passed else "nicht erfüllt"
        return (
            f"Berechnete Variante: {data.timber_grade}, Ø{data.dowel_diameter_d_mm:g} mm, "
            f"{data.rows_parallel_n} × {data.rows_perpendicular_m} = "
            f"{fastener_count} Stabdübel.\n"
            f"Maßgebend: {result.governing_check.name}, "
            f"η = {result.governing_check.utilization:.2f}.\n"
            f"Gesamtnachweis: {status}. {optimization.message}\n"
            "Materialwerte und sämtliche Nachweise stammen aus Materialverwaltung "
            "und Python-Rechenkern."
        )
