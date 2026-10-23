from __future__ import annotations

"""Data-only engineering assessment layer built on calculated results."""

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Any

from ai.assistant import MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL


SECTION_TITLES = (
    "Aufgabenstellung",
    "Erkannte Randbedingungen",
    "Gewählte Verbindung",
    "Bemessungsergebnis",
    "Maßgebender Nachweis",
    "Ingenieurmäßige Interpretation",
    "Variantenbewertung",
    "Optimierungspotenzial",
    "Empfehlung",
    "Annahmen und Grenzen",
    "Verwendete Quellen",
)

FORBIDDEN_CLAIMS = re.compile(
    r"\b(?:ist|sei|wirkt|erscheint|wäre)\s+(?:am\s+)?(?:billig|günstig|wirtschaftlich|"
    r"nachhaltig)\w*\b|\b(?:billiger|günstiger|wirtschaftlicher|nachhaltiger)\s+als\b|"
    r"\b(?:geringere|niedrigere|höhere)\s+(?:kosten|co2)\b|"
    r"\b(?:leichter\s+(?:zu\s+)?montieren|geringerer\s+fertigungsaufwand)\b",
    re.IGNORECASE,
)
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")


@dataclass(frozen=True, slots=True)
class EngineeringAssessmentContext:
    project_inputs: dict[str, Any]
    design_load: dict[str, Any]
    material: dict[str, Any]
    geometry: dict[str, Any]
    service_class: Any
    load_duration: Any
    selected_variant: dict[str, Any]
    calculated_checks: tuple[dict[str, Any], ...]
    governing_check: dict[str, Any]
    alternative_variants: tuple[dict[str, Any], ...]
    validation_results: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    applied_source_references: tuple[str, ...]
    user_optimization_objective: str | None
    conversation_constraints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectInputs": self.project_inputs,
            "designLoad": self.design_load,
            "material": self.material,
            "geometry": self.geometry,
            "serviceClass": self.service_class,
            "loadDuration": self.load_duration,
            "selectedVariant": self.selected_variant,
            "calculatedChecks": list(self.calculated_checks),
            "governingCheck": self.governing_check,
            "alternativeVariants": list(self.alternative_variants),
            "validationResults": list(self.validation_results),
            "warnings": list(self.warnings),
            "appliedSourceReferences": list(self.applied_source_references),
            "userOptimizationObjective": self.user_optimization_objective,
            "conversationConstraints": list(self.conversation_constraints),
            "dataAvailability": {
                "costs": False,
                "co2": False,
                "fabricationEffort": False,
                "assemblyEffort": False,
            },
        }


def _percent(value: Any) -> float:
    return round(float(value) * 100.0, 1)


def build_assessment_context(
    snapshot: dict[str, Any], conversation: list[dict[str, str]],
) -> EngineeringAssessmentContext | None:
    result = snapshot.get("currentResult")
    if not result:
        return None
    inputs = dict(result.get("input") or {})
    checks = tuple({
        "name": item.get("name"),
        "resistanceKn": item.get("resistance_kn"),
        "utilizationPercent": _percent(item.get("utilization", 0)),
        "passed": item.get("passed"),
        "source": item.get("source"),
    } for item in result.get("checks", []))
    governing_name = result.get("governingCheck")
    governing = next(
        (item for item in checks if item["name"] == governing_name),
        {
            "name": governing_name,
            "utilizationPercent": _percent(result.get("utilization", 0)),
            "passed": result.get("passed"),
        },
    )
    alternatives = tuple({
        "id": item.get("id"),
        "label": item.get("label"),
        "fastenerCount": item.get("fastenerCount"),
        "diameterMm": item.get("diameterMm"),
        "plateCount": item.get("plateCount"),
        "plateThicknessMm": item.get("plateThicknessMm"),
        "rowsParallel": item.get("rowsParallel"),
        "rowsPerpendicular": item.get("rowsPerpendicular"),
        "utilizationPercent": _percent(item.get("utilization", 0)),
        "governingCheck": item.get("governingCheck"),
        "passed": item.get("passed"),
        "normAdmissible": item.get("normAdmissible"),
    } for item in snapshot.get("variants", []))
    validation = tuple(dict(item) for item in result.get("geometryRequirements", []))
    warnings = tuple(
        str(item.get("message") or item.get("name"))
        for item in validation
        if str(item.get("status", "")).lower() not in {"passed", "ok", "erfüllt"}
    )
    fixed = snapshot.get("technicalState", {})
    conversation_constraints = tuple(
        item["content"] for item in conversation
        if item.get("role") == "user"
    )[-8:]
    selected_source = snapshot.get("currentVariant") or snapshot.get("recommendedVariant") or {}
    selected = {
        "id": selected_source.get("id"),
        "fastenerCount": selected_source.get("fastenerCount"),
        "diameterMm": selected_source.get("diameterMm"),
        "plateCount": selected_source.get("plateCount"),
        "plateThicknessMm": selected_source.get("plateThicknessMm"),
        "rowsParallel": selected_source.get("rowsParallel"),
        "rowsPerpendicular": selected_source.get("rowsPerpendicular"),
        "utilizationPercent": _percent(result.get("utilization", 0)),
        "reservePercent": _percent(selected_source.get("reserve", 0)),
        "governingCheck": result.get("governingCheck"),
        "passed": result.get("passed"),
        "normAdmissible": result.get("normAdmissible"),
    }
    return EngineeringAssessmentContext(
        project_inputs=fixed,
        design_load={"forceEdKn": inputs.get("force_ed_kn")},
        material={
            "timberGrade": inputs.get("timber_grade"),
            "rhoKkgM3": inputs.get("rho_k_kg_m3"),
            "kMod": inputs.get("k_mod"),
            "gammaMTimber": inputs.get("gamma_m_timber"),
        },
        geometry={
            "widthMm": inputs.get("width_b_mm"),
            "heightMm": inputs.get("height_h_mm"),
            "plateCount": inputs.get("number_of_plates_ns"),
            "plateThicknessMm": inputs.get("plate_thickness_ts_mm"),
            "sideThicknessMm": inputs.get("side_thickness_t1_mm"),
            "middleThicknessMm": inputs.get("middle_thickness_t2_mm"),
            "dowelDiameterMm": inputs.get("dowel_diameter_d_mm"),
            "rowsParallel": inputs.get("rows_parallel_n"),
            "rowsPerpendicular": inputs.get("rows_perpendicular_m"),
            "a1Mm": inputs.get("a1_mm"), "a2Mm": inputs.get("a2_mm"),
            "a3tMm": inputs.get("a3_t_mm"), "a4cMm": inputs.get("a4_c_mm"),
        },
        service_class=inputs.get("service_class"),
        load_duration=inputs.get("load_duration_class"),
        selected_variant=selected,
        calculated_checks=checks,
        governing_check=governing,
        alternative_variants=alternatives,
        validation_results=validation,
        warnings=warnings,
        applied_source_references=tuple(snapshot.get("sources", [])),
        user_optimization_objective=snapshot.get("optimizationGoal"),
        conversation_constraints=conversation_constraints,
    )


def compact_assessment(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    result = snapshot.get("currentResult")
    if not result:
        return None
    suitable = bool(result.get("passed") and result.get("normAdmissible"))
    utilization = _percent(result.get("utilization", 0))
    reserve = round(max(0.0, 100.0 - utilization), 1)
    variants = snapshot.get("variants", [])
    current = snapshot.get("currentVariant") or snapshot.get("recommendedVariant")
    alternatives = [item for item in variants if not current or item.get("id") != current.get("id")]
    lower = min(alternatives, key=lambda item: item.get("utilization", 99), default=None)
    if lower and float(lower.get("utilization", 99)) < float(result.get("utilization", 0)):
        recommendation = (
            f"Für eine größere rechnerische Reserve kann die berechnete Variante "
            f"„{lower['label']}“ mit {_percent(lower['utilization']):.1f} % "
            "maximaler Ausnutzung untersucht werden."
        )
    else:
        recommendation = (
            "Für eine größere rechnerische Reserve kann der vorhandene Variantenraum "
            "mit einem niedrigeren Zielwert der maximalen Ausnutzung erneut ausgewertet werden."
        )
    return {
        "status": "Technisch geeignet" if suitable else "Technisch nicht geeignet",
        "suitable": suitable,
        "utilizationPercent": utilization,
        "reservePercent": reserve,
        "governingCheck": result.get("governingCheck"),
        "summary": (
            f"Die untersuchte Variante {'erfüllt' if suitable else 'erfüllt nicht'} die aktuell "
            f"implementierten Nachweise. Mit {utilization:.1f} % maximaler Ausnutzung "
            f"verbleiben {reserve:.1f} % rechnerische Reserve bis zum Bemessungswiderstand."
        ),
        "recommendation": recommendation,
    }


def _assessment_prompt(context: EngineeringAssessmentContext) -> str:
    return """Du erstellst eine sachliche technische Bewertung ausschließlich aus dem JSON-Kontext.
Du darfst keine Werte berechnen, ergänzen oder schätzen. Verwende quantitative Angaben nur exakt so,
wie sie im Kontext stehen. Behaupte keine Kosten-, Wirtschafts-, CO2-, Nachhaltigkeits-, Montage-
oder Fertigungsvorteile. Normkonformität darf nur für die aufgeführten Prüfungen beschrieben werden.
Vorschläge sind als erneut durch den Rechenkern zu prüfende Untersuchungen zu formulieren.
Verwende die Fachbegriffe Stahlblechanzahl für plateCount und Stahlblechdicke für plateThicknessMm;
bezeichne Stahlbleche niemals als Bretter oder Brettlagen.
Antworte ausschließlich als JSON-Objekt mit dem Schlüssel sections. sections ist ein Array aus genau
11 Objekten mit title und content, in der vorgegebenen Reihenfolge. Keine Markdown-Tabellen.

EngineeringAssessmentContext:
""" + json.dumps(context.to_dict(), ensure_ascii=False, separators=(",", ":"))


def _parse_report(raw: str) -> list[dict[str, str]]:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Die KI-Antwort enthält kein JSON-Objekt.")
    parsed = json.loads(raw[start:end + 1])
    sections = parsed.get("sections")
    if not isinstance(sections, list) or len(sections) != len(SECTION_TITLES):
        raise ValueError("Die KI-Antwort enthält nicht alle Berichtskapitel.")
    normalized = []
    for expected, section in zip(SECTION_TITLES, sections):
        if not isinstance(section, dict):
            raise ValueError("Die Kapitelstruktur der KI-Antwort ist ungültig.")
        content = str(section.get("content", "")).strip()
        if not content:
            raise ValueError("Ein Berichtskapitel ist leer.")
        normalized.append({"title": expected, "content": content})
    return normalized


def _validate_report(sections: list[dict[str, str]], context: EngineeringAssessmentContext) -> None:
    text = "\n".join(item["content"] for item in sections)
    if FORBIDDEN_CLAIMS.search(text):
        raise ValueError("Die KI-Antwort enthält eine nicht belegte Bewertungsdimension.")
    context_text = json.dumps(context.to_dict(), ensure_ascii=False)
    context_numbers = [float(token.replace(",", ".")) for token in NUMBER.findall(context_text)]
    for token in NUMBER.findall(text):
        normalized = token.replace(",", ".")
        value = float(normalized)
        decimals = len(normalized.partition(".")[2]) if "." in normalized else 0
        if not any(round(candidate, decimals) == value for candidate in context_numbers):
            raise ValueError(f"Nicht belegte Zahl in der KI-Antwort: {token}")


def generate_engineering_report(assistant: Any, context: EngineeringAssessmentContext) -> list[dict[str, str]]:
    prompt = _assessment_prompt(context)
    if assistant.llm_provider == "local":
        request = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/chat",
            data=json.dumps({
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = json.load(response)["message"]["content"]
    else:
        if not assistant._api_key:
            raise RuntimeError("OpenAI API-Key fehlt.")
        from openai import OpenAI
        response = OpenAI(api_key=assistant._api_key).responses.create(
            model=MODEL,
            input=prompt,
        )
        raw = response.output_text
    sections = _parse_report(raw)
    _validate_report(sections, context)
    return sections
