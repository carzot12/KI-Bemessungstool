from __future__ import annotations

"""Einfacher V1-Assistent: Sprache, Zustand, Material und Rechenaufruf."""

import json
import os
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from calculations.stabduebel import (
    StabduebelInput,
    StabduebelResult,
    calculate_stabduebel,
)
from calculations.oenorm_validation import validate_oenorm
from infopol.materials import TimberMaterialRepository

from .optimizer import (
    SUPPORTED_DOWEL_DIAMETERS_MM,
    OptimizationResult,
    optimize_stabduebel,
)


PROMPT_PATH = Path(__file__).parent / "prompts" / "stabduebel_system.txt"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
TWO_SHEAR_ONE_INTERNAL_PLATE = "TWO_SHEAR_ONE_INTERNAL_PLATE"
MULTI_SHEAR_TWO_INTERNAL_PLATES = "MULTI_SHEAR_TWO_INTERNAL_PLATES"


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "PARAMETER_CHANGE", "NEW_DESIGN", "OPTIMIZE",
                "WHAT_IF", "COMPARE", "MAXIMUM_LOAD", "TARGET_UTILIZATION",
                "EXPLAIN_RESULT", "EXPLAIN_CHECK", "RECOMMEND_IMPROVEMENT",
                "ASK_CURRENT_STATE", "UNDO_LAST_CHANGE",
                "GENERAL_ENGINEERING_QUESTION", "CLARIFICATION_REQUIRED",
            ],
        },
        "clarification_parameter": {
            "type": ["string", "null"],
            "enum": [
                "force_ed_kn", "timber_grade", "cross_section",
                "dowel_diameter_d_mm", "number_of_plates_ns",
                "plate_thickness_ts_mm", "arrangement", None,
            ],
        },
        "force_ed_kn": {"type": ["number", "null"]},
        "timber_grade": {"type": ["string", "null"]},
        "dowel_diameter_d_mm": {"type": ["number", "null"]},
        "number_of_plates_ns": {"type": ["integer", "null"]},
        "plate_thickness_ts_mm": {"type": ["number", "null"]},
        "width_b_mm": {"type": ["number", "null"]},
        "height_h_mm": {"type": ["number", "null"]},
        "rows_parallel_n": {"type": ["integer", "null"]},
        "rows_perpendicular_m": {"type": ["integer", "null"]},
        "total_fastener_count": {"type": ["integer", "null"]},
        "a1_mm": {"type": ["number", "null"]},
        "a2_mm": {"type": ["number", "null"]},
        "a3_t_mm": {"type": ["number", "null"]},
        "a4_c_mm": {"type": ["number", "null"]},
        "e1_mm": {"type": ["number", "null"]},
        "e2_mm": {"type": ["number", "null"]},
        "max_utilization": {"type": ["number", "null"]},
        "minimize_fasteners": {"type": "boolean"},
        "optimize_diameter": {"type": "boolean"},
        "explain_governing": {"type": "boolean"},
    },
    "required": [
        "intent",
        "clarification_parameter",
        "force_ed_kn",
        "timber_grade",
        "dowel_diameter_d_mm",
        "number_of_plates_ns",
        "plate_thickness_ts_mm",
        "width_b_mm",
        "height_h_mm",
        "rows_parallel_n",
        "rows_perpendicular_m",
        "total_fastener_count",
        "a1_mm", "a2_mm", "a3_t_mm", "a4_c_mm", "e1_mm", "e2_mm",
        "max_utilization",
        "minimize_fasteners",
        "optimize_diameter",
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
    requested_fastener_count: int | None = None
    last_result: StabduebelResult | None = None
    last_optimization: OptimizationResult | None = None
    pending_clarification: str | None = None
    connection_type: str = MULTI_SHEAR_TWO_INTERNAL_PLATES
    shear_planes_s: int = 4


@dataclass(frozen=True, slots=True)
class AssistantReply:
    text: str
    result: StabduebelResult | None
    used_llm: bool
    recognized_parameters: str = ""
    interpretation: str = ""


class StabduebelAssistant:
    def __init__(self) -> None:
        self.state = ConversationState()
        self.materials = TimberMaterialRepository()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self._undo_state: ConversationState | None = None
        self._comparison_results: list[StabduebelResult] = []

    def reset(self) -> None:
        self.state = ConversationState()
        self._undo_state = None
        self._comparison_results = []

    def respond(self, user_text: str) -> AssistantReply:
        if not user_text.strip():
            raise ValueError("Bitte eine Anforderung eingeben.")
        if re.search(r"\beinschnittig(?:e|en|er|es)?\b", user_text, re.IGNORECASE):
            text = (
                "Mit ‚einschnittig‘ ist der Anschlussfall noch nicht eindeutig. "
                "Meinst du eine echte einschnittige Stahl-Holz-Verbindung oder den "
                "unterstützten Aufbau Holz | Stahl | Holz mit einem innenliegenden "
                "Stahlblech und zwei Scherfugen? Der aktuelle Entwurf bleibt unverändert."
            )
            return AssistantReply(
                text, self.state.last_result, False,
                self._recognized_parameters(self.state.last_result), text,
            )

        extracted, used_llm = self._extract(user_text)

        intent = str(extracted["intent"])
        if intent == "UNDO_LAST_CHANGE":
            return self._undo_reply(used_llm)

        if intent in {"CLARIFICATION", "CLARIFICATION_REQUIRED"}:
            parameter = extracted.get("clarification_parameter")
            self.state.pending_clarification = str(parameter) if parameter else None
            question = self._clarification_question(self.state.pending_clarification)
            return AssistantReply(
                question,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                question,
            )

        if intent == "ASK_CURRENT_STATE":
            text = self._current_state_text()
            return AssistantReply(
                text,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                text,
            )

        if intent == "GENERAL_ENGINEERING_QUESTION":
            text = self._answer_general_question(user_text)
            return AssistantReply(
                text,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                text,
            )

        if intent == "COMPARE":
            text = self._compare_requested_variants(user_text)
            return AssistantReply(
                text,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                text,
            )

        state_before_change = deepcopy(self.state)
        self._apply(extracted)
        self.state.pending_clarification = None

        if intent in {"EXPLAIN_RESULT", "EXPLAIN_CHECK", "RECOMMEND_IMPROVEMENT"} or extracted["explain_governing"]:
            if re.search(r"warum.*(?:diese\s+)?variante.*gewählt|warum.*diese\s+variante", user_text, re.IGNORECASE):
                explanation = self._explain_selection()
            elif intent == "RECOMMEND_IMPROVEMENT" or re.search(
                r"was\s+würdest.*ändern|was.*verbessern|empfehl|warum.*(?:nicht|geht)",
                user_text, re.IGNORECASE,
            ):
                explanation = (
                    self._interpret_result(
                        self.state.last_result,
                        self.state.last_optimization,
                    )
                    if self.state.last_optimization is not None
                    else "Es liegt noch kein berechneter Variantenraum für eine belastbare Empfehlung vor."
                )
            else:
                explanation = self._explain_governing()
            return AssistantReply(
                explanation,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(),
                explanation,
            )

        if intent == "MAXIMUM_LOAD":
            self._undo_state = state_before_change
            text = self._maximum_load_text()
            return AssistantReply(
                text, self.state.last_result, used_llm,
                self._recognized_parameters(self.state.last_result), text,
            )

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
                self._missing_parameter_question(missing),
                None,
                used_llm,
                self._recognized_parameters(),
            )

        base_input = self._build_input()
        run_fixed = set(self.state.fixed_parameters)
        # Bei einer normalen Änderung/What-if bleibt der aktuelle Entwurf
        # geometrisch derselbe. Nur ein ausdrücklicher Optimierungs-Intent darf
        # die vom letzten Lauf gewählten n, m oder d erneut variieren.
        if intent not in {"OPTIMIZE", "TARGET_UTILIZATION", "NEW_DESIGN"}:
            for key in (
                "rows_parallel_n", "rows_perpendicular_m", "dowel_diameter_d_mm",
            ):
                if key in self.state.parameters:
                    run_fixed.add(key)
        optimization = optimize_stabduebel(
            base_input,
            fixed_parameters=run_fixed,
            max_utilization=self.state.max_utilization,
            minimize_fasteners=self.state.minimize_fasteners,
            required_fastener_count=self.state.requested_fastener_count,
        )
        self.state.last_optimization = optimization
        if optimization.selected is None:
            displayed = min(
                optimization.evaluated,
                key=lambda item: (
                    len(item.validation.failures),
                    item.result.governing_check.utilization,
                ),
                default=None,
            )
            self.state.last_result = displayed.result if displayed else None
            if intent == "WHAT_IF" and state_before_change.last_result is not None and displayed:
                self._comparison_results = [
                    state_before_change.last_result,
                    displayed.result,
                ]
            interpretation = self._interpret_result(
                displayed.result if displayed else None,
                optimization,
            )
            self._undo_state = state_before_change
            return AssistantReply(
                (
                    self._format_result(displayed.result, optimization, intent, extracted)
                    if displayed
                    else optimization.message
                ) + (
                    self._what_if_delta(state_before_change.last_result, displayed.result)
                    if intent == "WHAT_IF" and displayed else ""
                ),
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                interpretation,
            )

        selected = optimization.selected
        previous_result = state_before_change.last_result
        self.state.last_result = selected.result
        # Die gefundene Konfiguration wird zum aktuellen Entwurf, bleibt aber
        # veränderbar, sofern der Benutzer sie nicht ausdrücklich festgelegt hat.
        self.state.parameters["rows_parallel_n"] = selected.input.rows_parallel_n
        self.state.parameters["rows_perpendicular_m"] = selected.input.rows_perpendicular_m
        self.state.parameters["dowel_diameter_d_mm"] = selected.input.dowel_diameter_d_mm
        self._undo_state = state_before_change
        if intent == "WHAT_IF" and previous_result is not None:
            self._comparison_results = [previous_result, selected.result]
        return AssistantReply(
            self._format_result(selected.result, optimization, intent, extracted)
            + (self._what_if_delta(previous_result, selected.result) if intent == "WHAT_IF" else ""),
            selected.result,
            used_llm,
            self._recognized_parameters(selected.result),
            self._interpret_result(selected.result, optimization),
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
                    "pending_clarification": self.state.pending_clarification,
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
                extracted = self._validate_extraction(json.loads(response.output_text))
                extracted = self._enforce_explicit_diameter_input(text, extracted)
                extracted = self._enforce_cross_section_input(text, extracted)
                extracted = self._enforce_explicit_fastener_input(text, extracted)
                return self._enforce_plate_and_optimization_input(text, extracted), True
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
            "intent": "PARAMETER_CHANGE",
            "clarification_parameter": None,
            "force_ed_kn": None,
            "timber_grade": None,
            "dowel_diameter_d_mm": None,
            "number_of_plates_ns": None,
            "plate_thickness_ts_mm": None,
            "width_b_mm": None,
            "height_h_mm": None,
            "rows_parallel_n": None,
            "rows_perpendicular_m": None,
            "total_fastener_count": None,
            "a1_mm": None,
            "a2_mm": None,
            "a3_t_mm": None,
            "a4_c_mm": None,
            "e1_mm": None,
            "e2_mm": None,
            "max_utilization": None,
            "minimize_fasteners": bool(
                re.search(r"weniger|möglichst\s+wenig|so\s+wenig", normalized)
            ),
            "optimize_diameter": bool(
                re.search(
                    r"welcher\s+(?:stab)?dübel(?:durchmesser)?|"
                    r"welcher\s+durchmesser.*(?:sinnvoll|geeignet)",
                    normalized,
                )
            ),
            "explain_governing": bool(
                re.search(r"warum|weshalb", normalized)
                and re.search(r"maßgeb|nachweis", normalized)
            ),
        }

        if re.search(r"rückgängig|vorige\s+variante|letzte\s+änderung.*zurück", normalized):
            data["intent"] = "UNDO_LAST_CHANGE"
        elif re.search(r"wie\s*viel.*trägt.*(?:maximal|höchstens)|wie\s*viel.*(?:maximal|höchstens).*trägt|max(?:imal)?\s*last|wie\s*viel\s+(?:kn\s+)?geht|wieviel\s+(?:kn\s+)?geht|welche\s+maximallast", normalized):
            data["intent"] = "MAXIMUM_LOAD"
        elif re.search(r"was\s+wäre|was\s+wenn|was\s+passiert|und\s+wenn", normalized):
            data["intent"] = "WHAT_IF"
        elif re.search(r"was\s+(?:hab|habe).*eingestellt|was.*momentan|aktueller?\s+entwurf|was\s+war.*(?:querschnitt|eingestellt)|was\s+rechnen\s+wir", normalized):
            data["intent"] = "ASK_CURRENT_STATE"
        elif re.search(r"vergleich", normalized):
            data["intent"] = "COMPARE"
        elif re.search(r"was\s+(?:ist|bedeutet).*n[_\s-]?eff", normalized):
            data["intent"] = "GENERAL_ENGINEERING_QUESTION"
        elif (
            data["explain_governing"]
            or re.search(r"warum.*(?:variante|so\s+hoch|gewählt)", normalized)
            or re.search(r"welcher\s+nachweis.*(?:kritisch|maßgeb)", normalized)
            or re.search(r"warum.*(?:nicht|geht|ausreich)", normalized)
            or re.search(r"was\s+würdest.*ändern|was.*verbessern|empfehl", normalized)
        ):
            data["intent"] = "EXPLAIN_RESULT"
        elif re.search(r"(?:querschnitt).*(?:kleiner|größer)|(?:kleiner|größer).*(?:querschnitt)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION_REQUIRED"
            data["clarification_parameter"] = "cross_section"
        elif re.search(r"(?:blech).*(?:dicker|dünner)|(?:dicker|dünner).*(?:blech)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION_REQUIRED"
            data["clarification_parameter"] = "plate_thickness_ts_mm"
        elif re.search(r"(?:dübel).*(?:welcher\s+durchmesser)|(?:durchmesser).*(?:ändern)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION_REQUIRED"
            data["clarification_parameter"] = "dowel_diameter_d_mm"
        elif re.search(r"so\s+wenig|möglichst\s+wenig|wie\s+viele.*mindestens", normalized):
            data["intent"] = "OPTIMIZE"
        elif data["optimize_diameter"]:
            data["intent"] = "OPTIMIZE"
        elif re.search(r"anschluss|bemess", normalized):
            data["intent"] = "NEW_DESIGN"

        pending = self.state.pending_clarification
        bare_number = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:mm)?\s*", normalized)
        if pending and bare_number:
            data["intent"] = "PARAMETER_CHANGE"
            if pending == "plate_thickness_ts_mm":
                data[pending] = float(bare_number.group(1))
            elif pending == "dowel_diameter_d_mm":
                data[pending] = float(bare_number.group(1))

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
        else:
            short_grade = re.search(r"\b(gl|c)\s*(\d+)\s*([hc])?\b", text, re.IGNORECASE)
            if short_grade:
                prefix, number, suffix = short_grade.groups()
                requested = f"{prefix.upper()}{number}{suffix or ''}"
                candidates = [
                    grade for grade in grade_names
                    if grade.lower() == requested.lower()
                    or (not suffix and grade.lower().startswith(requested.lower()))
                ]
                if len(candidates) == 1:
                    data["timber_grade"] = candidates[0]
                elif not suffix and f"{prefix.upper()}{number}h" in grade_names:
                    data["timber_grade"] = f"{prefix.upper()}{number}h"

        diameter = re.search(r"(?:ø|⌀|durchmesser|dübel)\s*(\d+(?:\.\d+)?)", normalized)
        if not diameter:
            diameter = re.search(r"\b(\d+(?:\.\d+)?)er(?:\s+(?:stab)?dübel)?\b", normalized)
        if not diameter and "dowel_diameter_d_mm" in self.state.fixed_parameters:
            diameter = re.search(
                r"(?:jetzt|nun|doch\s+wieder)\s+(?:mit|auf)\s*"
                r"(\d+(?:\.\d+)?)\s*mm\b",
                normalized,
            )
        if diameter:
            data["dowel_diameter_d_mm"] = float(diameter.group(1))
        elif re.search(r"(?:dübel|dübl).*\bkleiner|kleinere.*(?:dübel|dübl)", normalized):
            current = float(self._current_value("dowel_diameter_d_mm") or 12.0)
            smaller = [d for d in SUPPORTED_DOWEL_DIAMETERS_MM if d < current]
            if smaller:
                data["dowel_diameter_d_mm"] = max(smaller)
                data["intent"] = "WHAT_IF"
        elif re.search(r"(?:dübel|dübl).*\bgrößer|größere.*(?:dübel|dübl)", normalized):
            current = float(self._current_value("dowel_diameter_d_mm") or 12.0)
            larger = [d for d in SUPPORTED_DOWEL_DIAMETERS_MM if d > current]
            if larger:
                data["dowel_diameter_d_mm"] = min(larger)
                data["intent"] = "WHAT_IF"

        plates = re.search(r"(\d+)\s*(?:stahl)?blech(?:e|en)?\b", normalized)
        if plates:
            data["number_of_plates_ns"] = int(plates.group(1))

        plate_thickness = re.search(
            r"(?:blechdicke|blechstärke|blech)\s*(?:von\s*)?(\d+(?:\.\d+)?)\s*mm",
            normalized,
        )
        if plate_thickness:
            data["plate_thickness_ts_mm"] = float(plate_thickness.group(1))

        utilization = re.search(
            r"(?:max(?:imal)?\s*)?(\d+(?:\.\d+)?)\s*%\s*(?:ausnutzung)?",
            normalized,
        )
        if utilization:
            data["max_utilization"] = float(utilization.group(1)) / 100.0
            data["intent"] = "TARGET_UTILIZATION"

        distance_names = {
            "a1_mm": r"a1", "a2_mm": r"a2", "a3_t_mm": r"a3\s*,?\s*t",
            "a4_c_mm": r"a4\s*,?\s*c", "e1_mm": r"e1", "e2_mm": r"e2",
        }
        for key, label in distance_names.items():
            match = re.search(rf"\b{label}\s*(?:=|auf)?\s*(\d+(?:\.\d+)?)\s*mm\b", normalized)
            if match:
                data[key] = float(match.group(1))

        data = self._enforce_explicit_diameter_input(text, data)
        data = self._enforce_cross_section_input(text, data)
        data = self._enforce_explicit_fastener_input(text, data)
        return self._enforce_plate_and_optimization_input(text, data)

    @staticmethod
    def _enforce_explicit_diameter_input(
        text: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Gibt einer expliziten Durchmesserangabe immer Vorrang.

        Diese deterministische Schutzschicht läuft sowohl nach dem LLM
        Structured Output als auch im lokalen Fallback. Damit kann weder eine
        fehlerhafte KI-Extraktion noch ein alter State den Benutzerwert
        überschreiben.
        """
        number = r"(\d+(?:[.,]\d+)?)"
        patterns = (
            rf"(?:ø|⌀)\s*{number}\s*(?:mm)?\b",
            rf"\b{number}\s*er(?:\s+(?:stab)?dübel\w*)?\b",
            rf"\b{number}\s*mm\s+(?:stab)?dübel\w*\b",
        )
        match = next(
            (
                candidate
                for pattern in patterns
                if (candidate := re.search(pattern, text, re.IGNORECASE))
            ),
            None,
        )

        # In einem reinen Durchmesser-Folgeprompt ist auch "12 mm" eindeutig.
        # Aktionsformulierungen sind ebenfalls zulässig, solange ausdrücklich
        # kein Blech oder Querschnitt bezeichnet wird.
        if match is None and not re.search(r"blech|querschnit", text, re.IGNORECASE):
            match = re.search(
                rf"(?:nimm|verwende|mit|auf|ändere\s+auf|jetzt\s+mit|wieder)\s*"
                rf"{number}\s*mm\b",
                text,
                re.IGNORECASE,
            )
        if match is None:
            match = re.fullmatch(rf"\s*{number}\s*mm\s*[.!]?\s*", text, re.IGNORECASE)

        if match is not None:
            data["dowel_diameter_d_mm"] = float(match.group(1).replace(",", "."))
            # Ein ausdrücklicher Wert ist eine Parameteränderung, auch wenn das
            # LLM fälschlich eine Durchmesseroptimierung erkannt haben sollte.
            data["optimize_diameter"] = False
            if data.get("intent") not in {"WHAT_IF", "MAXIMUM_LOAD"}:
                data["intent"] = "PARAMETER_CHANGE"
        return data

    @staticmethod
    def _enforce_cross_section_input(
        text: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Liest b × h beziehungsweise b/h und normalisiert cm auf mm."""
        number = r"(\d+(?:[.,]\d+)?)"
        paired = re.search(
            rf"{number}\s*(?:x|×|✕|/)\s*{number}\s*(mm|cm)\b",
            text,
            re.IGNORECASE,
        )
        if paired:
            factor = 10.0 if paired.group(3).lower() == "cm" else 1.0
            data["width_b_mm"] = float(paired.group(1).replace(",", ".")) * factor
            data["height_h_mm"] = float(paired.group(2).replace(",", ".")) * factor
            return data

        unitless = re.search(
            rf"{number}\s*(?:x|×|✕|/)\s*{number}", text, re.IGNORECASE
        )
        if unitless and re.search(r"querschnit|jetzt\s+mit", text, re.IGNORECASE):
            width_value = float(unitless.group(1).replace(",", "."))
            height_value = float(unitless.group(2).replace(",", "."))
            if width_value >= 50.0 and height_value >= 50.0:
                data["width_b_mm"] = width_value
                data["height_h_mm"] = height_value
                return data

        width = re.search(
            rf"\bb\s*=\s*{number}\s*(mm|cm)\b",
            text,
            re.IGNORECASE,
        )
        height = re.search(
            rf"\bh\s*=\s*{number}\s*(mm|cm)\b",
            text,
            re.IGNORECASE,
        )
        if width and height:
            width_factor = 10.0 if width.group(2).lower() == "cm" else 1.0
            height_factor = 10.0 if height.group(2).lower() == "cm" else 1.0
            data["width_b_mm"] = (
                float(width.group(1).replace(",", ".")) * width_factor
            )
            data["height_h_mm"] = (
                float(height.group(1).replace(",", ".")) * height_factor
            )
        return data

    @staticmethod
    def _enforce_explicit_fastener_input(
        text: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Übernimmt explizites n × m wortgetreu, unabhängig vom LLM."""
        # Zahlenpaare mit mm/cm sind Querschnitte und keine Dübelanordnung.
        if re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:x|×|✕|/)\s*"
            r"\d+(?:[.,]\d+)?\s*(?:mm|cm)\b",
            text,
            re.IGNORECASE,
        ):
            return data

        # Ein als Querschnitt bezeichnetes Zahlenpaar ohne Einheit ist keine
        # Dübelanordnung. Die Einheit muss zunächst geklärt werden.
        if re.search(r"querschnit", text, re.IGNORECASE) and re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:x|×|✕|/)\s*\d+(?:[.,]\d+)?\b",
            text,
            re.IGNORECASE,
        ):
            data["intent"] = "CLARIFICATION_REQUIRED"
            data["clarification_parameter"] = "cross_section"
            data["width_b_mm"] = None
            data["height_h_mm"] = None
            return data

        arrangement = re.search(r"\b(\d+)\s*[x×✕]\s*(\d+)\b", text, re.IGNORECASE)
        if arrangement:
            rows_parallel = int(arrangement.group(1))
            rows_perpendicular = int(arrangement.group(2))
            data["rows_parallel_n"] = rows_parallel
            data["rows_perpendicular_m"] = rows_perpendicular
            data["total_fastener_count"] = rows_parallel * rows_perpendicular
            return data

        total = re.search(r"\b(\d+)\s*(?:stab)?dübel(?:n)?\b", text, re.IGNORECASE)
        if not total:
            total = re.search(r"\b(\d+)\s*stück\b", text, re.IGNORECASE)
        if total:
            data["total_fastener_count"] = int(total.group(1))
            data["rows_parallel_n"] = None
            data["rows_perpendicular_m"] = None
        return data

    @staticmethod
    def _enforce_plate_and_optimization_input(
        text: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Übernimmt explizite Ein-Blech-Vorgaben und Minimalziel wortgetreu."""
        one_plate = re.search(
            r"\b(?:1|ein(?:e|em|en|er|es)?)\s+stahlblech(?:e|en)?\b",
            text,
            re.IGNORECASE,
        ) or re.search(
            r"\b(?:anzahl\s+)?stahlblech(?:e|en)?\s*[:=]?\s*"
            r"(?:1|ein(?:e|em|en|er|es)?)\b",
            text,
            re.IGNORECASE,
        ) or re.search(
            r"\b(?:1|ein(?:e|em|en|er|es)?)\s+innenliegende[snr]?\s+blech\b|"
            r"\bnur\s+(?:1|ein(?:e|em|en|er|es)?)\s+blech\b",
            text,
            re.IGNORECASE,
        )
        if one_plate:
            data["number_of_plates_ns"] = 1
        if re.search(
            r"holz\s*[-|]\s*stahl(?:blech)?\s*[-|]\s*holz|"
            r"holz\s+stahl(?:blech)?\s+holz|"
            r"zweischnittig(?:e|en|er|es)?(?:\s+verbindung)?|"
            r"zweischnittig.*(?:ein(?:em|en)?|1)\s+stahlblech",
            text,
            re.IGNORECASE,
        ):
            data["number_of_plates_ns"] = 1

        normalized = text.lower()
        minimize = re.search(
            r"weniger|möglichst\s+wenig|so\s+wenig", normalized
        ) or re.search(
            r"wie\s+viele\s+(?:stab)?dübel.*(?:brauch|benötig|mindestens|minimal)",
            normalized,
        ) or re.search(
            r"(?:mindestens|minimal).*?(?:stab)?dübel",
            normalized,
        )
        if minimize:
            data["minimize_fasteners"] = True
            data["intent"] = "OPTIMIZE"
        return data

    def _apply(self, extracted: dict[str, Any]) -> None:
        rows_parallel = extracted.get("rows_parallel_n")
        rows_perpendicular = extracted.get("rows_perpendicular_m")
        total_fasteners = extracted.get("total_fastener_count")

        if rows_parallel is not None and rows_perpendicular is not None:
            self.state.parameters["rows_parallel_n"] = int(rows_parallel)
            self.state.parameters["rows_perpendicular_m"] = int(rows_perpendicular)
            self.state.fixed_parameters.update(
                {"rows_parallel_n", "rows_perpendicular_m"}
            )
            self.state.requested_fastener_count = int(rows_parallel) * int(
                rows_perpendicular
            )
        elif total_fasteners is not None:
            self.state.requested_fastener_count = int(total_fasteners)
            for key in ("rows_parallel_n", "rows_perpendicular_m"):
                self.state.parameters.pop(key, None)
                self.state.fixed_parameters.discard(key)

        for key in (
            "force_ed_kn",
            "timber_grade",
            "dowel_diameter_d_mm",
            "number_of_plates_ns",
            "plate_thickness_ts_mm",
            "width_b_mm",
            "height_h_mm",
            "a1_mm", "a2_mm", "a3_t_mm", "a4_c_mm", "e1_mm", "e2_mm",
        ):
            value = extracted.get(key)
            if value is not None:
                self.state.parameters[key] = value
                self.state.fixed_parameters.add(key)
                if key == "number_of_plates_ns":
                    self._set_connection_state(int(value))

        if extracted.get("max_utilization") is not None:
            maximum = float(extracted["max_utilization"])
            if not 0.0 < maximum <= 1.0:
                raise ValueError("Die maximale Ausnutzung muss zwischen 0 und 100 % liegen.")
            self.state.max_utilization = maximum
        if extracted.get("minimize_fasteners"):
            self.state.minimize_fasteners = True
        if extracted.get("optimize_diameter"):
            self.state.fixed_parameters.discard("dowel_diameter_d_mm")

    def _set_connection_state(self, plate_count: int) -> None:
        self.state.connection_type = (
            TWO_SHEAR_ONE_INTERNAL_PLATE
            if plate_count == 1 else MULTI_SHEAR_TWO_INTERNAL_PLATES
        )
        self.state.shear_planes_s = 2 * plate_count
        self.state.parameters["number_of_plates_ns"] = plate_count

    def _build_input(self) -> StabduebelInput:
        defaults = asdict(StabduebelInput())
        defaults.update(self.state.parameters)
        defaults["shear_planes_s"] = self.state.shear_planes_s

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

    def _explain_selection(self) -> str:
        optimization = self.state.last_optimization
        result = self.state.last_result
        if optimization is None or result is None:
            return "Es liegt noch keine berechnete Variantenauswahl vor, die ich erklären kann."
        if optimization.selected is None:
            validation = validate_oenorm(result.input, result)
            reasons = "; ".join(check.message for check in validation.failures)
            return (
                "Ich habe keine Variante als Lösung gewählt: Keine tatsächlich "
                f"berechnete Variante erfüllte alle Randbedingungen. Angezeigt wird "
                f"nur die am nächsten liegende untersuchte Variante mit "
                f"{result.governing_check.utilization:.0%} rechnerischer Ausnutzung. "
                + (f"Die Validierung meldet: {reasons}" if reasons else "")
            )
        objective = (
            "die kleinste erfüllte Stabdübelanzahl"
            if self.state.minimize_fasteners
            else "die geringste maximale Ausnutzung"
        )
        return (
            f"Ich habe diese Variante gewählt, weil das aktive Ziel {objective} war. "
            f"Der Optimierer hat {optimization.evaluated_count} Varianten tatsächlich "
            f"mit dem Python-Rechenkern geprüft; {optimization.feasible_count} davon "
            f"erfüllten Zulässigkeit, Nachweise und Ausnutzungsziel. Die aktuelle "
            f"Variante hat {result.governing_check.utilization:.0%} Ausnutzung."
        )

    def _current_value(self, key: str) -> float | int | str | None:
        if key in self.state.parameters:
            return self.state.parameters[key]
        if self.state.last_result is not None:
            return getattr(self.state.last_result.input, key)
        defaults = StabduebelInput()
        return getattr(defaults, key, None)

    def _clarification_question(self, parameter: str | None) -> str:
        if parameter == "cross_section":
            width = self._current_value("width_b_mm")
            height = self._current_value("height_h_mm")
            return (
                "Gerne. Welche Abmessungen möchtest du verwenden? "
                f"Aktuell sind {float(width):g} × {float(height):g} mm eingestellt."
            )
        if parameter == "plate_thickness_ts_mm":
            thickness = self._current_value("plate_thickness_ts_mm")
            return (
                f"Aktuell ist das Blech {float(thickness):g} mm dick. "
                "Welche Blechdicke möchtest du verwenden?"
            )
        if parameter == "dowel_diameter_d_mm":
            diameter = self._current_value("dowel_diameter_d_mm")
            return (
                f"Aktuell ist Ø{float(diameter):g} mm eingestellt. "
                "Welchen Stabdübeldurchmesser möchtest du verwenden?"
            )
        if parameter == "number_of_plates_ns":
            plates = self._current_value("number_of_plates_ns")
            return (
                f"Aktuell sind {int(plates)} Stahlbleche eingestellt. "
                "Wie viele möchtest du verwenden?"
            )
        if parameter == "timber_grade":
            return "Welche Holzfestigkeitsklasse möchtest du verwenden?"
        if parameter == "force_ed_kn":
            return "Welche Bemessungszugkraft in kN soll angesetzt werden?"
        if parameter == "arrangement":
            return "Welche feste Anordnung n × m möchtest du vorgeben?"
        return "Welche konkrete technische Vorgabe möchtest du ändern?"

    def _missing_parameter_question(self, missing: list[str]) -> str:
        known: list[str] = []
        if "force_ed_kn" in self.state.parameters:
            known.append(f"{float(self.state.parameters['force_ed_kn']):g} kN")
        if "timber_grade" in self.state.parameters:
            known.append(str(self.state.parameters["timber_grade"]))
        prefix = "Alles klar"
        if known:
            prefix += " – " + " und ".join(known) + " habe ich übernommen"
        if missing == ["Holzfestigkeitsklasse"]:
            return prefix + ". Welche Holzfestigkeitsklasse möchtest du verwenden?"
        if missing == ["Bemessungslast"]:
            return prefix + ". Welche Bemessungszugkraft in kN soll ich ansetzen?"
        return (
            prefix + ". Für den Start brauche ich noch Bemessungszugkraft und "
            "Holzfestigkeitsklasse."
        )

    def _current_state_text(self) -> str:
        result_input = self.state.last_result.input if self.state.last_result else None

        def value(key: str, default: str = "noch offen") -> str:
            current = self.state.parameters.get(key)
            if current is None and result_input is not None:
                current = getattr(result_input, key)
            return default if current is None else f"{current:g}" if isinstance(current, float) else str(current)

        lines = [
            "Aktueller Entwurf:",
            f"- Verbindungstyp: {result_input.connection_case if result_input else 'noch offen'}",
            f"- Last: {value('force_ed_kn')} kN",
            f"- Holz: {value('timber_grade')}",
        ]
        width = value("width_b_mm")
        height = value("height_h_mm")
        lines.append(f"- Querschnitt: {width} × {height} mm")
        lines.extend([
            f"- Stahlbleche: {value('number_of_plates_ns')}",
            f"- Blechdicke: {value('plate_thickness_ts_mm')} mm",
            f"- Stabdübel: Ø{value('dowel_diameter_d_mm')} mm",
        ])
        if result_input is not None:
            count = result_input.rows_parallel_n * result_input.rows_perpendicular_m
            lines.append(
                f"- Anordnung: {result_input.rows_parallel_n} × "
                f"{result_input.rows_perpendicular_m} = {count} Stabdübel"
            )
        objective = "minimale Stabdübelanzahl" if self.state.minimize_fasteners else "geringe Ausnutzung"
        if self.state.max_utilization < 1.0:
            objective += f", maximal {self.state.max_utilization:.0%}"
        lines.append(f"- Optimierungsziel: {objective}")
        if self.state.fixed_parameters:
            lines.append(
                "- Gesperrte Benutzervorgaben: "
                + ", ".join(sorted(self.state.fixed_parameters))
            )
        return "\n".join(lines)

    def _answer_general_question(self, user_text: str) -> str:
        if re.search(r"n[_\s-]?eff", user_text, re.IGNORECASE):
            result = self.state.last_result
            suffix = ""
            if result is not None:
                suffix = (
                    f" Im aktuellen Rechenergebnis verwendet der Python-Rechenkern "
                    f"n_eff = {result.timber_fastener['n_eff']:.2f}."
                )
            return (
                "n_eff ist die wirksame Anzahl der hintereinander in Faserrichtung "
                "angeordneten Verbindungsmittel. Der Rechenkern berücksichtigt damit, "
                "dass mehrere Stabdübel einer Reihe nicht immer gleichmäßig tragen."
                + suffix
            )
        return (
            "Diese allgemeine Fachfrage kann ich im V1 noch nicht belastbar aus der "
            "hinterlegten Wissensbasis beantworten. Ich kann dir aber den aktuellen "
            "Entwurf oder ein tatsächlich berechnetes Ergebnis erläutern."
        )

    def _undo_reply(self, used_llm: bool) -> AssistantReply:
        if self._undo_state is None:
            text = "Es gibt noch keine vorherige Änderung, die ich zurücknehmen kann."
            return AssistantReply(text, self.state.last_result, used_llm, interpretation=text)
        current = deepcopy(self.state)
        self.state = deepcopy(self._undo_state)
        self._undo_state = current
        text = "Erledigt – ich habe die letzte Änderung zurückgenommen.\n\n" + self._current_state_text()
        return AssistantReply(
            text, self.state.last_result, used_llm,
            self._recognized_parameters(self.state.last_result), text,
        )

    def _maximum_load_text(self) -> str:
        """Bestimmt die Grenzlast ausschließlich über wiederholte Kernaufrufe."""
        base = self._build_input()
        low_load_values = asdict(base)
        low_load_values["force_ed_kn"] = 0.001
        low_load_input = StabduebelInput(**low_load_values)
        fixed = set(self.state.fixed_parameters)
        for key in ("rows_parallel_n", "rows_perpendicular_m", "dowel_diameter_d_mm"):
            if key in self.state.parameters:
                fixed.add(key)
        resolved = optimize_stabduebel(
            low_load_input,
            fixed_parameters=fixed,
            max_utilization=1.0,
            minimize_fasteners=self.state.minimize_fasteners,
            required_fastener_count=self.state.requested_fastener_count,
        )
        if resolved.selected is None:
            return (
                "Für die aktuellen Randbedingungen kann keine normative Maximallast "
                "angegeben werden, weil keine geometrisch und normativ zulässige "
                "Konfiguration im unterstützten Suchraum gefunden wurde."
            )
        data = resolved.selected.input

        def evaluate(force_kn: float) -> StabduebelResult | None:
            values = asdict(data)
            values["force_ed_kn"] = force_kn
            try:
                result = calculate_stabduebel(StabduebelInput(**values))
            except (ValueError, ZeroDivisionError):
                return None
            validation = validate_oenorm(result.input, result)
            return result if validation.admissible and result.passed else None

        if evaluate(0.001) is None:
            return (
                "Für die aktuelle Konfiguration kann keine normative Maximallast angegeben "
                "werden, weil bereits die Norm-/Geometrievalidierung nicht erfüllt ist."
            )
        low, high = 0.001, max(1.0, data.force_ed_kn)
        while evaluate(high) is not None and high < 1_000_000.0:
            low, high = high, high * 2.0
        for _ in range(60):
            middle = (low + high) / 2.0
            if evaluate(middle) is not None:
                low = middle
            else:
                high = middle
        result = evaluate(low)
        if result is None:
            return "Die deterministische Maximallastsuche konnte kein Ergebnis bestimmen."
        item = result.input
        count = item.rows_parallel_n * item.rows_perpendicular_m
        return (
            f"Die deterministisch per Bisektion ermittelte maximale Bemessungslast beträgt "
            f"rund {low:.2f} kN. Maßgebend ist „{result.governing_check.name}“ "
            f"(η = {result.governing_check.utilization:.2f}). Verwendet wurden "
            f"{item.rows_parallel_n} × {item.rows_perpendicular_m} = {count} Stabdübel "
            f"Ø{item.dowel_diameter_d_mm:g} mm, {item.timber_grade}, "
            f"{item.width_b_mm:g} × {item.height_h_mm:g} mm und "
            f"{item.number_of_plates_ns} Stahlbleche. Die Norm- und Geometrievalidierung "
            "ist an dieser Grenzlast erfüllt."
        )

    @staticmethod
    def _what_if_delta(
        previous: StabduebelResult | None,
        current: StabduebelResult,
    ) -> str:
        if previous is None:
            return ""
        before = previous.governing_check.utilization
        after = current.governing_check.utilization
        direction = "gesunken" if after < before else "gestiegen" if after > before else "unverändert"
        return (
            f"\n\nWhat-if-Vergleich: Gegenüber dem vorherigen Entwurf ist die maximale "
            f"Ausnutzung von {before:.0%} auf {after:.0%} {direction}."
        )

    def _compare_requested_variants(self, user_text: str) -> str:
        diameters = [
            float(value.replace(",", "."))
            for value in re.findall(r"(?:ø|⌀)\s*(\d+(?:[.,]\d+)?)|\b(\d+(?:[.,]\d+)?)er\b", user_text, re.IGNORECASE)
            for value in value if value
        ]
        if len(diameters) >= 2 and self.state.last_result is not None:
            compared: list[StabduebelResult] = []
            base = self.state.last_result.input
            for diameter in diameters[:2]:
                values = asdict(base)
                values["dowel_diameter_d_mm"] = diameter
                candidate = StabduebelInput(**values)
                run = optimize_stabduebel(
                    candidate,
                    fixed_parameters=set(self.state.fixed_parameters)
                    | {"dowel_diameter_d_mm", "rows_parallel_n", "rows_perpendicular_m"},
                    max_utilization=1.0,
                    minimize_fasteners=False,
                )
                if run.selected is not None:
                    compared.append(run.selected.result)
            if len(compared) == 2:
                self._comparison_results = compared
        return self._compare_variants()

    def _compare_variants(self) -> str:
        if len(self._comparison_results) >= 2:
            lines = []
            for result in self._comparison_results[-2:]:
                data = result.input
                count = data.rows_parallel_n * data.rows_perpendicular_m
                validation = validate_oenorm(data, result)
                lines.append(
                    f"- Ø{data.dowel_diameter_d_mm:g} mm: {data.rows_parallel_n} × "
                    f"{data.rows_perpendicular_m} = {count} Stabdübel, "
                    f"Ausnutzung {result.governing_check.utilization:.0%}, maßgebend "
                    f"„{result.governing_check.name}“, "
                    f"{'zulässig' if validation.admissible else 'nicht zulässig'}"
                )
            return "Vergleich der tatsächlich berechneten Varianten:\n" + "\n".join(lines)
        optimization = self.state.last_optimization
        if optimization is None or not optimization.evaluated:
            return "Es wurden noch keine Varianten berechnet, die ich vergleichen kann."
        admissible = [
            item for item in optimization.evaluated
            if item.validation.admissible and item.result.passed
        ]
        if len(admissible) < 2:
            return (
                "Im letzten Suchlauf wurde weniger als zwei zulässige und erfüllte "
                "Varianten berechnet. Ein belastbarer Vergleich ist daher noch nicht möglich."
            )
        fewest = min(
            admissible,
            key=lambda item: (item.fastener_count, item.result.governing_check.utilization),
        )
        reserve = min(admissible, key=lambda item: item.result.governing_check.utilization)

        def describe(label: str, item: Any) -> str:
            data = item.input
            return (
                f"- {label}: {data.rows_parallel_n} × {data.rows_perpendicular_m} = "
                f"{item.fastener_count} Stabdübel, maximale Ausnutzung "
                f"{item.result.governing_check.utilization:.0%}, maßgebend "
                f"„{item.result.governing_check.name}“"
            )

        return "Vergleich der tatsächlich berechneten Varianten:\n" + "\n".join([
            describe("wenigste Stabdübel", fewest),
            describe("größte Reserve", reserve),
        ])

    def _format_result(
        self,
        result: StabduebelResult,
        optimization: OptimizationResult,
        intent: str = "NEW_DESIGN",
        extracted: dict[str, Any] | None = None,
    ) -> str:
        data = result.input
        fastener_count = data.rows_parallel_n * data.rows_perpendicular_m
        validation = validate_oenorm(data, result)
        status = (
            "zulässig und erfüllt"
            if validation.admissible
            else "nicht zulässig"
        )
        reasons = ""
        if validation.failures:
            reasons = "\nGründe: " + "; ".join(
                check.message for check in validation.failures
            )
        changes = extracted or {}
        changed_labels = [
            label for key, label in (
                ("timber_grade", f"Holzklasse {data.timber_grade}"),
                (
                    "number_of_plates_ns",
                    f"{data.number_of_plates_ns} "
                    + ("Stahlblech" if data.number_of_plates_ns == 1 else "Stahlbleche"),
                ),
                ("plate_thickness_ts_mm", f"Blechdicke {data.plate_thickness_ts_mm:g} mm"),
                ("dowel_diameter_d_mm", f"Ø{data.dowel_diameter_d_mm:g} mm"),
                ("width_b_mm", f"Querschnitt {data.width_b_mm:g} × {data.height_h_mm:g} mm"),
            ) if changes.get(key) is not None
        ]
        if intent == "OPTIMIZE":
            opening = "Alles klar – ich habe den aktuellen Entwurf neu optimiert."
        elif intent == "PARAMETER_CHANGE" and changed_labels:
            opening = "Alles klar – geändert auf " + ", ".join(changed_labels) + "."
        else:
            opening = "Ich habe den Entwurf mit dem Python-Rechenkern geprüft."
        result_label = (
            "Ergebnis"
            if validation.admissible
            else "Beste berechnete Variante im Suchraum (nicht zulässig)"
        )
        closing = (
            ""
            if validation.admissible
            else "\nIch habe deine festen Vorgaben nicht automatisch verändert."
        )
        return (
            f"{opening}\n\n"
            f"Anschlussfall: {data.connection_case}\n"
            f"Scherfugen: {data.shear_planes_s}\n"
            f"{result_label}: {data.timber_grade}, Ø{data.dowel_diameter_d_mm:g} mm, "
            f"{data.rows_parallel_n} × {data.rows_perpendicular_m} = "
            f"{fastener_count} Stabdübel.\n"
            f"Maßgebend: {result.governing_check.name}, "
            f"η = {result.governing_check.utilization:.2f}.\n"
            f"Technisches Gesamtergebnis: {status}. {optimization.message}"
            f"{reasons}{closing}"
            + (
                "\nRechnerisch nach ÖNORM EN 1995-1-1, Gleichung (8.11), "
                "untersucht, aber nach der österreichischen nationalen Ergänzung "
                "für diesen tragenden Stabdübelanschluss nicht zulässig, da nur "
                "2 Scherflächen vorhanden sind."
                if data.number_of_plates_ns == 1 else ""
            )
        )

    def _recognized_parameters(self, result: StabduebelResult | None = None) -> str:
        parameters = self.state.parameters
        lines: list[str] = []

        def add(label: str, key: str, suffix: str = "") -> None:
            if key in parameters:
                source = "Benutzervorgabe" if key in self.state.fixed_parameters else "Optimierer"
                lines.append(f"{label}: {parameters[key]}{suffix}  ·  {source}")

        add("Ft,d", "force_ed_kn", " kN")
        add("Holzklasse", "timber_grade")

        if "width_b_mm" in parameters and "height_h_mm" in parameters:
            lines.append(
                f"Querschnitt: {float(parameters['width_b_mm']):g} × "
                f"{float(parameters['height_h_mm']):g} mm  ·  Benutzervorgabe"
            )

        input_data = result.input if result else None
        for label, key, suffix in (
            ("Anzahl Stahlbleche", "number_of_plates_ns", ""),
            ("Blechdicke", "plate_thickness_ts_mm", " mm"),
        ):
            if key in parameters:
                add(label, key, suffix)
            elif input_data is not None:
                lines.append(f"{label}: {getattr(input_data, key):g}{suffix}  ·  Standardwert")

        if "dowel_diameter_d_mm" in self.state.fixed_parameters:
            add("Stabdübeldurchmesser", "dowel_diameter_d_mm", " mm")
        elif input_data is not None:
            lines.append(
                f"Stabdübeldurchmesser: {input_data.dowel_diameter_d_mm:g} mm  ·  Optimierer"
            )

        objective = (
            "möglichst wenige Stabdübel"
            if self.state.minimize_fasteners
            else "geringe Ausnutzung"
        )
        if self.state.max_utilization < 1.0:
            objective += f", maximal {self.state.max_utilization:.0%}"
        lines.append(f"Optimierungsziel: {objective}")

        if input_data is not None:
            arrangement_source = (
                "Benutzervorgabe"
                if {
                    "rows_parallel_n",
                    "rows_perpendicular_m",
                }.issubset(self.state.fixed_parameters)
                else "Optimierer"
            )
            lines.append(
                f"Gewählte Anordnung: {input_data.rows_parallel_n} × "
                f"{input_data.rows_perpendicular_m} = "
                f"{input_data.rows_parallel_n * input_data.rows_perpendicular_m} "
                f"Stabdübel  ·  {arrangement_source}"
            )
        return "\n".join(lines)

    def _interpret_result(
        self,
        result: StabduebelResult | None,
        optimization: OptimizationResult,
    ) -> str:
        if result is None:
            return (
                "Es konnte keine berechenbare Variante erzeugt werden. Es liegt daher "
                "keine belastbare Empfehlung vor; als Nächstes sollte der fachlich "
                "festgelegte Suchraum überprüft oder erweitert werden."
            )

        data = result.input
        validation = validate_oenorm(data, result)
        utilization = result.governing_check.utilization
        reserve = max(0.0, 1.0 - utilization)
        count = data.rows_parallel_n * data.rows_perpendicular_m
        status = (
            "zulässig und erfüllt"
            if validation.admissible
            else "nicht zulässig"
        )
        text = (
            f"Untersucht wurde der Anschlussfall „{data.connection_case}“ mit "
            f"{data.shear_planes_s} Scherfugen. Gewählt wurden {count} Stabdübel "
            f"Ø{data.dowel_diameter_d_mm:g} mm "
            f"in einer Anordnung {data.rows_parallel_n} × {data.rows_perpendicular_m}, "
            f"{data.number_of_plates_ns} Stahlbleche mit {data.plate_thickness_ts_mm:g} mm "
            f"Dicke, Holzklasse {data.timber_grade} und einem Holzquerschnitt von "
            f"{data.width_b_mm:g} × {data.height_h_mm:g} mm. Der Rechenkern bewertet den "
            f"Gesamtnachweis als {status}. Die maximale Ausnutzung beträgt "
            f"{utilization:.0%}; maßgebend ist „{result.governing_check.name}“. "
        )
        if not validation.admissible:
            text += "Die technische Validierung meldet: " + "; ".join(
                check.message for check in validation.failures
            ) + " "
            if data.number_of_plates_ns == 1:
                text += (
                    "Der Verbindungsmittelnachweis wurde rechnerisch nach Gleichung "
                    "(8.11) geführt; eine österreichische Gesamtzulässigkeit wird "
                    "ausdrücklich nicht behauptet. "
                )
        elif result.passed:
            text += f"Bis 100 % verbleiben rechnerisch rund {reserve:.0%} Reserve. "
            if utilization > self.state.max_utilization:
                text += (
                    f"Das zusätzliche Optimierungsziel von maximal "
                    f"{self.state.max_utilization:.0%} wird damit jedoch nicht erreicht. "
                )
        else:
            failed = [check.name for check in result.checks if not check.passed]
            text += "Nicht erfüllt: " + ", ".join(failed) + ". "

        alternatives = [
            variant
            for variant in optimization.evaluated
            if variant.validation.admissible
            and variant.result.passed
            and variant.result.governing_check.utilization < utilization
            and (
                variant.input.rows_parallel_n,
                variant.input.rows_perpendicular_m,
            ) != (data.rows_parallel_n, data.rows_perpendicular_m)
        ]
        if alternatives:
            alternative = min(
                alternatives,
                key=lambda item: (
                    item.fastener_count,
                    item.result.governing_check.utilization,
                ),
            )
            alt = alternative.input
            text += (
                f"Als tatsächlich berechnete Alternative bietet sich "
                f"{alt.rows_parallel_n} × {alt.rows_perpendicular_m} = "
                f"{alternative.fastener_count} Stabdübel an; dafür berechnete der "
                f"Rechenkern eine maximale Ausnutzung von "
                f"{alternative.result.governing_check.utilization:.0%}."
            )
        else:
            text += (
                "Im untersuchten V1-Suchraum wurde keine Variante mit größerer "
                "Reserve berechnet. Als nächster Schritt können weitere fachlich "
                "freigegebene Anordnungen untersucht werden."
            )
        return text
