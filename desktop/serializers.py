from __future__ import annotations

"""JSON-only view models for the web presentation layer; no engineering maths."""

from dataclasses import asdict, dataclass
from typing import Any

from ai.assistant import MODEL, StabduebelAssistant
from ai.optimizer import curated_feasible_variants
from calculations.oenorm_validation import validate_oenorm
from calculations.stabduebel import StabduebelInput, StabduebelResult, calculate_stabduebel


@dataclass(frozen=True, slots=True)
class DemoSnapshot:
    input: StabduebelInput
    result: StabduebelResult
    variants: tuple[StabduebelResult, ...]


def build_demo_snapshot() -> DemoSnapshot:
    """Central, removable development state calculated by the real core."""
    base = StabduebelInput(
        force_ed_kn=140.0,
        timber_grade="GL24h",
        width_b_mm=200.0,
        height_h_mm=240.0,
        number_of_plates_ns=2,
        plate_thickness_ts_mm=5.0,
        side_thickness_t1_mm=40.0,
        middle_thickness_t2_mm=110.0,
        dowel_diameter_d_mm=16.0,
        hole_diameter_d0_mm=16.0,
        rows_parallel_n=2,
        rows_perpendicular_m=3,
        a1_mm=80.0,
        a2_mm=48.0,
        a3_t_mm=112.0,
        a4_c_mm=48.0,
    )
    variants = tuple(
        calculate_stabduebel(StabduebelInput(**{**asdict(base), **change}))
        for change in (
            {},
            {"plate_thickness_ts_mm": 6.0, "rows_perpendicular_m": 4},
            {"dowel_diameter_d_mm": 12.0, "hole_diameter_d0_mm": 13.0,
             "rows_parallel_n": 3, "rows_perpendicular_m": 3,
             "a1_mm": 60.0, "a2_mm": 40.0, "a3_t_mm": 85.0, "a4_c_mm": 60.0},
        )
    )
    return DemoSnapshot(base, variants[0], variants)


def _result(result: StabduebelResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    validation = validate_oenorm(result.input, result)
    return {
        "passed": result.passed,
        "normAdmissible": validation.admissible,
        "utilization": result.governing_check.utilization,
        "governingCheck": result.governing_check.name,
        "checks": [asdict(check) for check in result.checks],
        "input": asdict(result.input),
    }


def _variant(
    result: StabduebelResult, index: int, label: str | None = None,
) -> dict[str, Any]:
    data = result.input
    validation = validate_oenorm(data, result)
    return {
        "id": f"variant-{index}",
        "label": label or ("Beste Empfehlung" if index == 1 else "Berechnete Alternative"),
        "fastenerCount": data.rows_parallel_n * data.rows_perpendicular_m,
        "rowsParallel": data.rows_parallel_n,
        "rowsPerpendicular": data.rows_perpendicular_m,
        "diameterMm": data.dowel_diameter_d_mm,
        "plateCount": data.number_of_plates_ns,
        "plateThicknessMm": data.plate_thickness_ts_mm,
        "utilization": result.governing_check.utilization,
        "passed": result.passed,
        "normAdmissible": validation.admissible,
        "visualizationModel": visualization_model(data),
    }


def visualization_model(data: StabduebelInput) -> dict[str, Any]:
    return {
        "sectionWidthMm": data.width_b_mm,
        "sectionHeightMm": data.height_h_mm,
        "plateCount": data.number_of_plates_ns,
        "plateThicknessMm": data.plate_thickness_ts_mm,
        "sideThicknessMm": data.side_thickness_t1_mm,
        "middleThicknessMm": data.middle_thickness_t2_mm,
        "dowelDiameterMm": data.dowel_diameter_d_mm,
        "rowsParallel": data.rows_parallel_n,
        "rowsPerpendicular": data.rows_perpendicular_m,
        "forceEdKn": data.force_ed_kn,
        "a1Mm": data.a1_mm,
        "a2Mm": data.a2_mm,
        "a3tMm": data.a3_t_mm,
        "a4cMm": data.a4_c_mm,
    }


def serialize_snapshot(
    assistant: StabduebelAssistant,
    conversation: list[dict[str, str]],
    *,
    demo: DemoSnapshot | None,
) -> dict[str, Any]:
    current = assistant.state.last_result or (demo.result if demo else None)
    if assistant.state.last_optimization:
        curated = curated_feasible_variants(
                assistant.state.last_optimization,
                assistant.state.optimization_goal,
                assistant.state.fixed_parameters,
                12,
            )
        lowest_eta = min(
            (item.result.governing_check.utilization for item in curated),
            default=None,
        )
        labels_used: set[str] = set()
        variants = []
        for index, item in enumerate(curated, start=1):
            if index == 1:
                label = "Beste Empfehlung"
            elif item.input.dowel_diameter_d_mm == 12 and "Alternative Ø12" not in labels_used:
                label = "Alternative Ø12"
            elif item.input.dowel_diameter_d_mm == 16 and "Alternative Ø16" not in labels_used:
                label = "Alternative Ø16"
            elif item.result.governing_check.utilization == lowest_eta and "Mehr Reserve" not in labels_used:
                label = "Mehr Reserve"
            else:
                label = "Berechnete Alternative"
            labels_used.add(label)
            variants.append(_variant(item.result, index, label))
    else:
        variants = (
            [_variant(item, index) for index, item in enumerate(demo.variants, start=1)]
            if demo else []
        )
    if assistant.llm_status == "ONLINE":
        agent_status = {
            "mode": "online", "label": "KI ONLINE", "model": MODEL,
            "detail": "LLM-first Agent verbunden",
        }
    elif assistant.llm_status == "ERROR":
        agent_status = {
            "mode": "error", "label": "KI FEHLER", "model": MODEL,
            "detail": assistant.llm_error or "LLM-Verbindung fehlgeschlagen",
        }
    else:
        agent_status = {
            "mode": "local", "label": "LOKALER MODUS", "model": None,
            "detail": "Freie KI-Unterhaltung eingeschränkt",
        }
    return {
        "technicalState": dict(assistant.state.parameters),
        "currentResult": _result(current),
        "lastOptimization": (
            {
                "evaluatedCount": assistant.state.last_optimization.evaluated_count,
                "feasibleCount": assistant.state.last_optimization.feasible_count,
                "message": assistant.state.last_optimization.message,
            }
            if assistant.state.last_optimization else None
        ),
        "variants": variants,
        "agentStatus": agent_status,
        "conversation": conversation,
        "visualizationModel": visualization_model(current.input) if current else None,
        "demoMode": assistant.state.last_result is None and demo is not None,
    }
