from __future__ import annotations

"""JSON-only view models for the web presentation layer; no engineering maths."""

from dataclasses import asdict, dataclass
from typing import Any

from ai.assistant import MODEL, OLLAMA_MODEL, StabduebelAssistant
from ai.optimizer import curated_feasible_variants, ranked_feasible_variants
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
        side_thickness_t1_mm=60.0,
        middle_thickness_t2_mm=70.0,
        dowel_diameter_d_mm=12.0,
        hole_diameter_d0_mm=16.0,
        rows_parallel_n=2,
        rows_perpendicular_m=4,
        a1_mm=60.0,
        a2_mm=40.0,
        a3_t_mm=85.0,
        a4_c_mm=60.0,
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
        "geometryRequirements": [
            {**asdict(check), "status": check.status.value}
            for check in validation.checks
            if check.name in {
                "Achsabstand a1", "Achsabstand a2",
                "Beanspruchter Endabstand a3,t",
                "Unbeanspruchter Randabstand a4,c",
            }
        ],
        "input": asdict(result.input),
    }


def _variant(
    result: StabduebelResult, index: int, label: str | None = None,
    interest_reason: str | None = None,
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
        "governingCheck": result.governing_check.name,
        "interestReason": interest_reason or "Tatsächlich berechnete Vergleichsvariante.",
        "reserve": max(0.0, 1.0 - result.governing_check.utilization),
        "connectionAreaMm2": (
            2.0 * data.a3_t_mm + (data.rows_parallel_n - 1) * data.a1_mm
        ) * (
            2.0 * data.a4_c_mm + (data.rows_perpendicular_m - 1) * data.a2_mm
        ),
        "input": asdict(data),
        "visualizationModel": visualization_model(data),
        "connectionGeometry": connection_geometry(data),
    }


def _recommendation(variants: list[dict[str, Any]], goal: str | None) -> str:
    if not variants:
        return "Noch keine berechneten Varianten vorhanden."
    best = variants[0]
    reason = {
        "MIN_FASTENER_COUNT": "sie mit der geringsten priorisierten Verbindungsmittelanzahl gewählt wurde",
        "LOWER_UTILIZATION": "sie das gewählte Reserveziel am besten abbildet",
        "COMPACT_GEOMETRY": "sie im berechneten Variantenraum die kompakte Empfehlung ist",
        "MAXIMIZE_UTILIZATION": "sie die gewünschte hohe, noch zulässige Ausnutzung erreicht",
    }.get(goal, "sie die wirtschaftlich ausgewogene Empfehlung des berechneten Variantenraums ist")
    return (
        f"KI-Einschätzung: {best['label']} mit Ø{best['diameterMm']:g} mm und "
        f"{best['fastenerCount']} Stabdübeln wird empfohlen, weil {reason}. "
        "Die Einschätzung basiert ausschließlich auf den berechneten Varianten."
    )


def connection_geometry(data: StabduebelInput) -> dict[str, Any]:
    plate_half_length = (
        data.a3_t_mm
        + max(0, data.rows_parallel_n - 1) * data.a1_mm
        + data.e1_mm
    )
    plate_length = 2.0 * plate_half_length
    # No independent longitudinal timber end distance exists in the input model.
    # Use the exact modelled plate half-length as the drawing envelope instead of
    # borrowing the transverse timber edge distance a4,c.
    connection_length = plate_half_length
    plate_height = (
        2.0 * data.e2_mm
        + max(0, data.rows_perpendicular_m - 1) * data.a2_mm
    )
    row_positions = [
        data.a4_c_mm + index * data.a2_mm
        for index in range(data.rows_perpendicular_m)
    ]
    column_positions = [
        data.a3_t_mm + index * data.a1_mm
        for index in range(data.rows_parallel_n)
    ]
    plate_positions: list[float]
    if data.number_of_plates_ns == 2:
        plate_positions = [
            data.side_thickness_t1_mm + data.plate_thickness_ts_mm / 2.0,
            data.side_thickness_t1_mm + data.plate_thickness_ts_mm
            + data.middle_thickness_t2_mm + data.plate_thickness_ts_mm / 2.0,
        ]
    else:
        plate_positions = [
            data.side_thickness_t1_mm + data.plate_thickness_ts_mm / 2.0,
        ]
    plate_top = row_positions[0] - data.e2_mm
    plate_bottom = row_positions[-1] + data.e2_mm
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
        "e1Mm": data.e1_mm,
        "e2Mm": data.e2_mm,
        "connectionLengthMm": connection_length,
        "plateLengthMm": plate_length,
        "plateHeightMm": plate_height,
        "plateTopMm": plate_top,
        "plateBottomMm": plate_bottom,
        "platePositionsMm": plate_positions,
        "crossSectionLayersMm": (
            [data.side_thickness_t1_mm, data.plate_thickness_ts_mm,
             data.middle_thickness_t2_mm, data.plate_thickness_ts_mm,
             data.side_thickness_t1_mm]
            if data.number_of_plates_ns == 2
            else [data.side_thickness_t1_mm, data.plate_thickness_ts_mm,
                  data.side_thickness_t1_mm]
        ),
        "columnPositionsMm": column_positions,
        "rowPositionsMm": row_positions,
        "dowelPositionsLeftMm": [
            {"x": -x, "y": y} for x in column_positions for y in row_positions
        ],
        "dowelPositionsRightMm": [
            {"x": x, "y": y} for x in column_positions for y in row_positions
        ],
        "topTimberEdgeDistanceMm": row_positions[0],
        "bottomTimberEdgeDistanceMm": data.height_h_mm - row_positions[-1],
    }


def visualization_model(data: StabduebelInput) -> dict[str, Any]:
    """Backward-compatible name for the shared Python geometry snapshot."""
    return connection_geometry(data)


def _report_variants(
    assistant: StabduebelAssistant,
    current: StabduebelResult | None,
) -> list[dict[str, Any]]:
    """Select factual, de-duplicated report categories from evaluated results."""
    optimization = assistant.state.last_optimization
    if current is None:
        return []
    candidates: list[tuple[str, str, StabduebelResult | None]] = [
        ("A - FAVORIT", "Gewählte Variante / Favorit", current),
    ]
    if optimization:
        fixed = assistant.state.fixed_parameters
        balanced = ranked_feasible_variants(optimization, "BALANCED_DESIGN", fixed)
        minimum = ranked_feasible_variants(optimization, "MIN_FASTENER_COUNT", fixed)
        reserve = ranked_feasible_variants(optimization, "LOWER_UTILIZATION", fixed)
        feasible = [
            item for item in optimization.evaluated
            if item.validation.admissible and item.result.passed
            and item.result.governing_check.utilization <= 1.0
        ]
        diameter_12 = [item for item in feasible if item.input.dowel_diameter_d_mm == 12.0]
        fewest_12 = min(
            diameter_12,
            key=lambda item: (
                item.fastener_count,
                abs(item.result.governing_check.utilization - 0.85),
                item.input.number_of_plates_ns,
            ),
            default=None,
        )
        high_eta = max(
            feasible,
            key=lambda item: item.result.governing_check.utilization,
            default=None,
        )
        candidates.extend([
            ("B - WIRTSCHAFTLICH AUSGEWOGEN", "Heuristisch ausgewogene Lösung", balanced[0].result if balanced else None),
            ("C - WENIGSTE STABDÜBEL", "Minimale Verbindungsmittelanzahl", minimum[0].result if minimum else None),
            ("D - WENIGSTE STABDÜBEL MIT Ø12", "Ø12-Alternative mit minimaler Anzahl", fewest_12.result if fewest_12 else None),
            ("E - HOHE AUSNUTZUNG", "Höchste zulässige Ausnutzung", high_eta.result if high_eta else None),
            ("F - MEHR RESERVE", "Ausgewählte größere Tragreserve", reserve[0].result if reserve else None),
        ])
    selected: list[dict[str, Any]] = []
    signatures: set[tuple[Any, ...]] = set()
    for category, characteristic, result in candidates:
        if result is None:
            continue
        data = result.input
        signature = (
            data.number_of_plates_ns, data.plate_thickness_ts_mm,
            data.side_thickness_t1_mm, data.middle_thickness_t2_mm,
            data.dowel_diameter_d_mm, data.rows_parallel_n,
            data.rows_perpendicular_m, data.a1_mm, data.a2_mm,
            data.a3_t_mm, data.a4_c_mm, data.e1_mm, data.e2_mm,
        )
        if signature in signatures:
            # Preserve the factual category meaning without printing the same
            # physical design as a second report row.
            existing = next(
                item for item in selected
                if item["input"]["number_of_plates_ns"] == data.number_of_plates_ns
                and item["input"]["plate_thickness_ts_mm"] == data.plate_thickness_ts_mm
                and item["input"]["side_thickness_t1_mm"] == data.side_thickness_t1_mm
                and item["input"]["middle_thickness_t2_mm"] == data.middle_thickness_t2_mm
                and item["input"]["dowel_diameter_d_mm"] == data.dowel_diameter_d_mm
                and item["input"]["rows_parallel_n"] == data.rows_parallel_n
                and item["input"]["rows_perpendicular_m"] == data.rows_perpendicular_m
                and item["input"]["a1_mm"] == data.a1_mm
                and item["input"]["a2_mm"] == data.a2_mm
                and item["input"]["a3_t_mm"] == data.a3_t_mm
                and item["input"]["a4_c_mm"] == data.a4_c_mm
            )
            existing["category"] += f" / {category}"
            existing["characteristic"] += f"; {characteristic}"
            continue
        signatures.add(signature)
        item = _variant(result, len(selected) + 1, category, characteristic)
        item["category"] = category
        item["characteristic"] = characteristic
        selected.append(item)
    return selected


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
        lowest_count = min(
            (item.input.rows_parallel_n * item.input.rows_perpendicular_m for item in curated),
            default=None,
        )
        smallest_area = min(
            ((2.0 * item.input.a3_t_mm + (item.input.rows_parallel_n - 1) * item.input.a1_mm) *
             (2.0 * item.input.a4_c_mm + (item.input.rows_perpendicular_m - 1) * item.input.a2_mm)
             for item in curated),
            default=None,
        )
        labels_used: set[str] = set()
        variants = []
        selected_rank = next(
            (index for index, item in enumerate(
                assistant.state.last_optimization.evaluated, start=1
            ) if item is assistant.state.last_optimization.selected),
            None,
        )
        for index, item in enumerate(curated, start=1):
            count = item.input.rows_parallel_n * item.input.rows_perpendicular_m
            area = ((2.0 * item.input.a3_t_mm + (item.input.rows_parallel_n - 1) * item.input.a1_mm) *
                    (2.0 * item.input.a4_c_mm + (item.input.rows_perpendicular_m - 1) * item.input.a2_mm))
            if index == 1:
                label = "KI-Empfehlung"
                reason = {
                    "MIN_FASTENER_COUNT": "Empfohlen für das Ziel möglichst weniger Verbindungsmittel.",
                    "LOWER_UTILIZATION": "Empfohlen für das Ziel einer höheren rechnerischen Reserve.",
                    "COMPACT_GEOMETRY": "Empfohlen für das Ziel einer kompakten Verbindungsgeometrie.",
                    "MAXIMIZE_UTILIZATION": "Empfohlen für das Ziel einer hohen zulässigen Ausnutzung.",
                }.get(assistant.state.optimization_goal, "Wirtschaftlich ausgewogene KI-Empfehlung.")
            elif item.input.dowel_diameter_d_mm == 12 and "Alternative Ø12" not in labels_used:
                label = "Alternative Ø12"
                reason = "Vergleich mit tatsächlich berechnetem Stabdübeldurchmesser Ø12 mm."
            elif item.input.dowel_diameter_d_mm == 16 and "Alternative Ø16" not in labels_used:
                label = "Alternative Ø16"
                reason = "Vergleich mit tatsächlich berechnetem Stabdübeldurchmesser Ø16 mm."
            elif count == lowest_count and "Weniger Verbindungsmittel" not in labels_used:
                label = "Weniger Verbindungsmittel"
                reason = f"Mit {count} Stabdübeln je Stoßseite eine Variante mit minimaler Anzahl im Vergleich."
            elif item.result.governing_check.utilization == lowest_eta and "Mehr Reserve" not in labels_used:
                label = "Mehr Reserve"
                reason = f"Mit η = {item.result.governing_check.utilization * 100:.1f} % die größte Reserve im Vergleich."
            elif area == smallest_area and "Kompakter" not in labels_used:
                label = "Kompakter"
                reason = "Kleinste berechnete Anschlussfläche der dargestellten Vergleichsvarianten."
            else:
                label = f"Variante Ø{item.input.dowel_diameter_d_mm:g} · {item.input.rows_parallel_n} × {item.input.rows_perpendicular_m}"
                reason = "Technisch zulässige, tatsächlich berechnete Vergleichsvariante."
            labels_used.add(label)
            item_variant = _variant(item.result, index, label, reason)
            item_variant["reportIncluded"] = index == 1
            variants.append(item_variant)
    else:
        variants = (
            [{**_variant(
                item, index,
                "KI-Empfehlung" if index == 1 else
                f"Variante Ø{item.input.dowel_diameter_d_mm:g} · {item.input.rows_parallel_n} × {item.input.rows_perpendicular_m}",
                "Wirtschaftlich ausgewogene KI-Empfehlung." if index == 1 else
                "Tatsächlich berechnete Vergleichsvariante.",
            ), "reportIncluded": index == 1}
             for index, item in enumerate(demo.variants, start=1)]
            if demo else []
        )
    recommended_variant = variants[0] if variants else None
    current_input = asdict(current.input) if current else None
    current_variant = next(
        (
            item for item in variants
            if current_input and all(
                value == current_input.get(key)
                for key, value in item["input"].items()
                if key != "project_name"
            )
        ),
        None,
    )
    if current and current_variant is None:
        current_variant = _variant(current, 0, "Aktuell übernommene Variante",
                                   "Aktuell über DesktopBridge übernommene Konstruktion.")
    sources: list[str] = []
    if current:
        for check in validate_oenorm(current.input, current).checks:
            if check.source not in sources:
                sources.append(check.source)
    provider = assistant.llm_provider
    available = assistant.provider_available(provider)
    if assistant.llm_status == "ONLINE":
        agent_status = {
            "mode": "online", "label": "KI ONLINE",
            "model": OLLAMA_MODEL if provider == "local" else MODEL,
            "detail": "Ollama verbunden" if provider == "local" else "OpenAI konfiguriert",
        }
    elif assistant.llm_status == "ERROR":
        agent_status = {
            "mode": "error", "label": "KI FEHLER",
            "model": OLLAMA_MODEL if provider == "local" else MODEL,
            "detail": assistant.llm_error or "LLM-Verbindung fehlgeschlagen",
        }
    else:
        agent_status = {
            "mode": "local", "label": "LOKAL" if provider == "local" else "OPENAI",
            "model": OLLAMA_MODEL if provider == "local" else MODEL,
            "detail": (
                "Ollama verbunden" if available and provider == "local"
                else "Ollama nicht erreichbar" if provider == "local"
                else "OpenAI konfiguriert" if available
                else "OpenAI API-Key fehlt"
            ),
        }
    agent_status.update({
        "provider": provider,
        "available": available,
        "privacyDetail": "Daten bleiben auf diesem Gerät" if provider == "local" else "Cloud-KI optional",
    })
    return {
        "technicalState": dict(assistant.state.parameters),
        "currentResult": _result(current),
        "lastOptimization": (
            {
                "evaluatedCount": assistant.state.last_optimization.evaluated_count,
                "feasibleCount": assistant.state.last_optimization.feasible_count,
                "rejectedCount": assistant.state.last_optimization.evaluated_count - assistant.state.last_optimization.feasible_count,
                "shortlistedCount": len(variants),
                "selectedVariantRank": selected_rank,
                "selectedVariant": "variant-1" if assistant.state.last_optimization.selected else None,
                "objective": assistant.state.optimization_goal,
                "message": assistant.state.last_optimization.message,
            }
            if assistant.state.last_optimization else None
        ),
        "lastMaximumLoad": assistant.state.last_maximum_load,
        "variants": variants,
        "reportVariants": _report_variants(assistant, current),
        "recommendedVariant": recommended_variant,
        "currentVariant": current_variant,
        "recommendation": _recommendation(variants, assistant.state.optimization_goal),
        "sources": sources,
        "optimizationGoal": assistant.state.optimization_goal,
        "projectName": (
            str(current.input.project_name) if current else
            str(assistant.state.parameters.get("project_name", ""))
        ),
        "reportVariantIds": sorted(assistant.state.report_variant_ids),
        "agentStatus": agent_status,
        "conversation": conversation,
        "visualizationModel": visualization_model(current.input) if current else None,
        "connectionGeometry": connection_geometry(current.input) if current else None,
        "demoMode": assistant.state.last_result is None and demo is not None,
    }
