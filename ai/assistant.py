from __future__ import annotations

"""Einfacher V1-Assistent: Sprache, Zustand, Material und Rechenaufruf."""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from calculations.stabduebel import StabduebelInput, StabduebelResult
from calculations.oenorm_validation import validate_oenorm
from infopol.materials import TimberMaterialRepository

from .optimizer import OptimizationResult, optimize_stabduebel


PROMPT_PATH = Path(__file__).parent / "prompts" / "stabduebel_system.txt"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "PARAMETER_CHANGE", "NEW_DESIGN", "OPTIMIZE",
                "EXPLAIN_RESULT", "ASK_CURRENT_STATE", "COMPARE",
                "CLARIFICATION", "GENERAL_ENGINEERING_QUESTION",
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

    def reset(self) -> None:
        self.state = ConversationState()

    def respond(self, user_text: str) -> AssistantReply:
        if not user_text.strip():
            raise ValueError("Bitte eine Anforderung eingeben.")

        extracted, used_llm = self._extract(user_text)

        intent = str(extracted["intent"])
        if intent == "CLARIFICATION":
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
            text = self._compare_variants()
            return AssistantReply(
                text,
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                text,
            )

        self._apply(extracted)
        self.state.pending_clarification = None

        if intent == "EXPLAIN_RESULT" or extracted["explain_governing"]:
            if re.search(
                r"was\s+würdest.*ändern|was.*verbessern|empfehl",
                user_text,
                re.IGNORECASE,
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
        optimization = optimize_stabduebel(
            base_input,
            fixed_parameters=self.state.fixed_parameters,
            max_utilization=self.state.max_utilization,
            minimize_fasteners=self.state.minimize_fasteners,
            required_fastener_count=self.state.requested_fastener_count,
        )
        self.state.last_optimization = optimization
        if optimization.selected is None:
            displayed = min(
                optimization.evaluated,
                key=lambda item: item.result.governing_check.utilization,
                default=None,
            )
            self.state.last_result = displayed.result if displayed else None
            interpretation = self._interpret_result(
                displayed.result if displayed else None,
                optimization,
            )
            return AssistantReply(
                (
                    self._format_result(displayed.result, optimization, intent, extracted)
                    if displayed
                    else optimization.message
                ),
                self.state.last_result,
                used_llm,
                self._recognized_parameters(self.state.last_result),
                interpretation,
            )

        selected = optimization.selected
        self.state.last_result = selected.result
        # Die gefundene Konfiguration wird zum aktuellen Entwurf, bleibt aber
        # veränderbar, sofern der Benutzer sie nicht ausdrücklich festgelegt hat.
        self.state.parameters["rows_parallel_n"] = selected.input.rows_parallel_n
        self.state.parameters["rows_perpendicular_m"] = selected.input.rows_perpendicular_m
        self.state.parameters["dowel_diameter_d_mm"] = selected.input.dowel_diameter_d_mm
        return AssistantReply(
            self._format_result(selected.result, optimization, intent, extracted),
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

        if re.search(r"was\s+(?:hab|habe).*eingestellt|was.*momentan|aktueller?\s+entwurf|was\s+war.*(?:querschnitt|eingestellt)", normalized):
            data["intent"] = "ASK_CURRENT_STATE"
        elif re.search(r"vergleich", normalized):
            data["intent"] = "COMPARE"
        elif re.search(r"was\s+(?:ist|bedeutet).*n[_\s-]?eff", normalized):
            data["intent"] = "GENERAL_ENGINEERING_QUESTION"
        elif (
            data["explain_governing"]
            or re.search(r"warum.*(?:nicht|geht|ausreich)", normalized)
            or re.search(r"was\s+würdest.*ändern|was.*verbessern|empfehl", normalized)
        ):
            data["intent"] = "EXPLAIN_RESULT"
        elif re.search(r"(?:querschnitt).*(?:kleiner|größer)|(?:kleiner|größer).*(?:querschnitt)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION"
            data["clarification_parameter"] = "cross_section"
        elif re.search(r"(?:blech).*(?:dicker|dünner)|(?:dicker|dünner).*(?:blech)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION"
            data["clarification_parameter"] = "plate_thickness_ts_mm"
        elif re.search(r"(?:dübel).*(?:dicker|größer|kleiner)|(?:dicker|größer|kleiner).*(?:dübel)", normalized) and not re.search(r"\d", normalized):
            data["intent"] = "CLARIFICATION"
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

        plates = re.search(r"(\d+)\s*(?:stahl)?blech(?:e|en)?\b", normalized)
        if plates:
            data["number_of_plates_ns"] = int(plates.group(1))

        plate_thickness = re.search(
            r"(?:blechdicke|blechstärke)\s*(?:von\s*)?(\d+(?:\.\d+)?)",
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

        data = self._enforce_cross_section_input(text, data)
        data = self._enforce_explicit_fastener_input(text, data)
        return self._enforce_plate_and_optimization_input(text, data)

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
        if re.search(r"querschnitt", text, re.IGNORECASE) and re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:x|×|✕|/)\s*\d+(?:[.,]\d+)?\b",
            text,
            re.IGNORECASE,
        ):
            data["intent"] = "CLARIFICATION"
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
        )
        if one_plate:
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
        if extracted.get("optimize_diameter"):
            self.state.fixed_parameters.discard("dowel_diameter_d_mm")

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

    def _compare_variants(self) -> str:
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
            f"{result_label}: {data.timber_grade}, Ø{data.dowel_diameter_d_mm:g} mm, "
            f"{data.rows_parallel_n} × {data.rows_perpendicular_m} = "
            f"{fastener_count} Stabdübel.\n"
            f"Maßgebend: {result.governing_check.name}, "
            f"η = {result.governing_check.utilization:.2f}.\n"
            f"Technisches Gesamtergebnis: {status}. {optimization.message}"
            f"{reasons}{closing}"
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
            f"Gewählt wurden {count} Stabdübel Ø{data.dowel_diameter_d_mm:g} mm "
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
