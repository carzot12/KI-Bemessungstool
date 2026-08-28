from __future__ import annotations

"""Kleine deterministische Variantenuntersuchung für den V1-Prototyp."""

from dataclasses import dataclass, replace

from calculations.stabduebel import (
    StabduebelInput,
    StabduebelResult,
    calculate_stabduebel,
)
from calculations.oenorm_validation import (
    TechnicalValidationResult,
    validate_oenorm,
)


# Fachlich festgelegter V1-Suchraum. Die ÖNORM erlaubt 6 mm < d < 30 mm
# und warnt oberhalb 24 mm. Die automatische Suche untersucht deshalb alle
# ausgewählte gerade Nenndurchmesser im nicht gewarnten Bereich. Das ist ein
# Suchraster, keine normative Durchmesserreihe. Explizite Benutzervorgaben
# innerhalb des gesamten Normbereichs werden unabhängig davon geprüft.
ROWS_PARALLEL = (1, 2, 3, 4)
ROWS_PERPENDICULAR = (2, 3, 4, 5, 6)
SUPPORTED_DOWEL_DIAMETERS_MM = (8.0, 10.0, 12.0, 16.0, 20.0, 24.0)
PREFERRED_DESIGN_DIAMETERS_MM = (12.0, 16.0)
SUPPORTED_PLATE_COUNTS = (1, 2)
# Im aktuellen Scope tatsächlich belegte Dicken: 5 mm im IHBV-Tabellenwerk
# (Zuglaschenstoß mit innenliegendem Stahlblech) und 6 mm im verifizierten
# Projekt-Referenzfall. Weitere in Unterlagen vorkommende Dicken betreffen
# andere Bauteile/Verbindungsmittel und werden daher nicht freigeschaltet.
SUPPORTED_PLATE_THICKNESSES_MM = (5.0, 6.0)
GEOMETRY_STEP_MM = 5.0
RESERVE_TARGET_UTILIZATION = 0.65


def _connection_area(item: "EvaluatedVariant") -> float:
    data = item.input
    return (
        2.0 * data.a3_t_mm + (data.rows_parallel_n - 1) * data.a1_mm
    ) * (
        2.0 * data.a4_c_mm + (data.rows_perpendicular_m - 1) * data.a2_mm
    )


def _preferred_candidates(
    feasible: list["EvaluatedVariant"], fixed: set[str],
) -> list["EvaluatedVariant"]:
    """Engineering candidate set; never changes explicit user diameters."""
    if "dowel_diameter_d_mm" in fixed:
        return feasible
    preferred = [
        item for item in feasible
        if item.input.dowel_diameter_d_mm in PREFERRED_DESIGN_DIAMETERS_MM
    ]
    return preferred or feasible


def engineering_rank_key(item: "EvaluatedVariant", goal: str | None) -> tuple:
    """Ranks already calculated/admissible variants without new engineering maths."""
    eta = item.result.governing_check.utilization
    diameter_preference = (
        PREFERRED_DESIGN_DIAMETERS_MM.index(item.input.dowel_diameter_d_mm)
        if item.input.dowel_diameter_d_mm in PREFERRED_DESIGN_DIAMETERS_MM
        else len(PREFERRED_DESIGN_DIAMETERS_MM)
    )
    if goal == "MIN_FASTENER_COUNT":
        return (item.fastener_count, item.input.number_of_plates_ns,
                abs(eta - 0.85), diameter_preference, _connection_area(item))
    if goal == "COMPACT_GEOMETRY":
        return (_connection_area(item), item.fastener_count,
                item.input.number_of_plates_ns, abs(eta - 0.85), diameter_preference)
    if goal == "LOWER_UTILIZATION":
        return (abs(eta - RESERVE_TARGET_UTILIZATION), item.fastener_count,
                item.input.number_of_plates_ns, diameter_preference, _connection_area(item))
    if goal == "MAXIMIZE_UTILIZATION":
        return (-eta, item.fastener_count, item.input.number_of_plates_ns,
                diameter_preference, _connection_area(item))
    # Default: wirtschaftliche, robuste Empfehlung statt Extremwert.
    return (item.input.number_of_plates_ns, item.fastener_count,
            diameter_preference, abs(eta - 0.85), _connection_area(item))


def ranked_feasible_variants(
    optimization: "OptimizationResult", goal: str | None,
    fixed_parameters: set[str] | None = None,
) -> list["EvaluatedVariant"]:
    feasible = [
        item for item in optimization.evaluated
        if item.validation.admissible and item.result.passed
    ]
    candidates = _preferred_candidates(feasible, fixed_parameters or set())
    return sorted(candidates, key=lambda item: engineering_rank_key(item, goal))


def curated_feasible_variants(
    optimization: "OptimizationResult", goal: str | None,
    fixed_parameters: set[str] | None = None, limit: int = 12,
) -> list["EvaluatedVariant"]:
    """Returns diverse, real variants rather than repeated geometry splits."""
    ranked = ranked_feasible_variants(optimization, goal, fixed_parameters)
    chosen: list[EvaluatedVariant] = []
    signatures: set[tuple[int, float, int, int]] = set()

    def add(item: EvaluatedVariant | None) -> None:
        if item is None or len(chosen) >= limit:
            return
        signature = (
            item.input.number_of_plates_ns, item.input.dowel_diameter_d_mm,
            item.input.rows_parallel_n, item.input.rows_perpendicular_m,
        )
        if signature not in signatures:
            signatures.add(signature)
            chosen.append(item)

    add(optimization.selected)
    for diameter in PREFERRED_DESIGN_DIAMETERS_MM:
        add(next((item for item in ranked if item.input.dowel_diameter_d_mm == diameter), None))
    add(min(ranked, key=lambda item: item.result.governing_check.utilization, default=None))
    for item in ranked:
        add(item)
    return chosen


def _geometry_candidates(
    base_input: StabduebelInput,
    plate_count: int,
    fixed: set[str],
) -> tuple[tuple[float, float], ...]:
    """Liefert ausschließlich geometrisch konsistente Schichtaufbauten.

    Es wird keine Mindestholzdicke erfunden: freie Aufteilungen werden im
    1-mm-Raster erzeugt und anschließend ausnahmslos vom vorhandenen Rechenkern
    und ÖNORM-Validator geprüft. Explizite Benutzerwerte bleiben unverändert.
    """
    b = base_input.width_b_mm
    ts = base_input.plate_thickness_ts_mm
    t1_fixed = "side_thickness_t1_mm" in fixed
    t2_fixed = "middle_thickness_t2_mm" in fixed

    if plate_count == 1:
        derived_t1 = (b - ts) / 2.0
        return ((base_input.side_thickness_t1_mm if t1_fixed else derived_t1,
                 base_input.middle_thickness_t2_mm),)

    if t1_fixed and t2_fixed:
        return ((base_input.side_thickness_t1_mm, base_input.middle_thickness_t2_mm),)
    if t1_fixed:
        return ((base_input.side_thickness_t1_mm,
                 b - 2.0 * base_input.side_thickness_t1_mm - 2.0 * ts),)
    if t2_fixed:
        return (((b - 2.0 * ts - base_input.middle_thickness_t2_mm) / 2.0,
                 base_input.middle_thickness_t2_mm),)

    # Das Raster ist eine transparente Variantendiskretisierung, keine
    # normative Mindestholzdicke. Zulässig wird eine Aufteilung ausschließlich
    # nach realem Rechenlauf und bestehender ÖNORM-/Geometrievalidierung.
    upper = int((b - 2.0 * ts) / 2.0)
    candidates = set(range(int(GEOMETRY_STEP_MM), upper + 1, int(GEOMETRY_STEP_MM)))
    candidates.add(int(base_input.side_thickness_t1_mm))
    return tuple(
        (float(t1), b - 2.0 * float(t1) - 2.0 * ts)
        for t1 in sorted(candidates)
        if t1 > 0 and b - 2.0 * float(t1) - 2.0 * ts > 0.0
    )


@dataclass(frozen=True, slots=True)
class EvaluatedVariant:
    input: StabduebelInput
    result: StabduebelResult
    validation: TechnicalValidationResult

    @property
    def fastener_count(self) -> int:
        return self.input.rows_parallel_n * self.input.rows_perpendicular_m


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    selected: EvaluatedVariant | None
    evaluated: tuple[EvaluatedVariant, ...]
    evaluated_count: int
    feasible_count: int
    message: str


def optimize_stabduebel(
    base_input: StabduebelInput,
    *,
    fixed_parameters: set[str] | None = None,
    max_utilization: float = 1.0,
    min_utilization: float = 0.0,
    minimize_fasteners: bool = True,
    maximize_utilization: bool = False,
    required_fastener_count: int | None = None,
    optimization_goal: str | None = None,
) -> OptimizationResult:
    """Prüft den V1-Suchraum ausschließlich mit ``calculate_stabduebel``."""
    fixed = fixed_parameters or set()
    diameters = (
        (base_input.dowel_diameter_d_mm,)
        if "dowel_diameter_d_mm" in fixed
        else SUPPORTED_DOWEL_DIAMETERS_MM
    )
    if any(not 6.0 < diameter < 30.0 for diameter in diameters):
        return OptimizationResult(
            selected=None,
            evaluated=(),
            evaluated_count=0,
            feasible_count=0,
            message=(
                "Der Stabdübeldurchmesser ist nach dem aktuellen ÖNORM-Profil "
                "nur im Bereich 6 mm < d < 30 mm zulässig."
            ),
        )

    parallel_values = (
        (base_input.rows_parallel_n,)
        if "rows_parallel_n" in fixed
        else ROWS_PARALLEL
    )
    perpendicular_values = (
        (base_input.rows_perpendicular_m,)
        if "rows_perpendicular_m" in fixed
        else ROWS_PERPENDICULAR
    )
    plate_counts = (
        (base_input.number_of_plates_ns,)
        if "number_of_plates_ns" in fixed
        else SUPPORTED_PLATE_COUNTS
    )
    plate_thicknesses = (
        (base_input.plate_thickness_ts_mm,)
        if "plate_thickness_ts_mm" in fixed
        else SUPPORTED_PLATE_THICKNESSES_MM
    )

    evaluated: list[EvaluatedVariant] = []
    for plate_count in plate_counts:
        for plate_thickness in plate_thicknesses:
            geometry_base = replace(
                base_input, plate_thickness_ts_mm=plate_thickness
            )
            for side_t1, middle_t2 in _geometry_candidates(geometry_base, plate_count, fixed):
                for diameter in diameters:
                    for rows_parallel in parallel_values:
                        for rows_perpendicular in perpendicular_values:
                            if (
                                required_fastener_count is not None
                                and rows_parallel * rows_perpendicular != required_fastener_count
                            ):
                                continue
                            candidate_a2 = (
                                base_input.a2_mm
                                if "a2_mm" in fixed
                                else base_input.a2_mm
                                if diameter == 12.0
                                else 3.0 * diameter
                            )
                            # a4,c is an actual edge distance in the input
                            # model. Automatically generated grids are centred;
                            # the validator independently checks the normative
                            # minimum. Explicit user geometry is never moved.
                            candidate_a4 = (
                                base_input.a4_c_mm
                                if "a4_c_mm" in fixed
                                else (
                                    base_input.height_h_mm
                                    - (rows_perpendicular - 1) * candidate_a2
                                ) / 2.0
                            )
                            if (
                                "a4_c_mm" not in fixed
                                and candidate_a4 < 3.0 * diameter
                            ):
                                # A centred automatic grid is only a candidate
                                # when both residual timber edges satisfy the
                                # existing minimum-distance rule.
                                continue
                            candidate = replace(
                                geometry_base,
                                number_of_plates_ns=plate_count,
                                side_thickness_t1_mm=side_t1,
                                middle_thickness_t2_mm=middle_t2,
                                dowel_diameter_d_mm=diameter,
                                hole_diameter_d0_mm=(
                                    base_input.hole_diameter_d0_mm
                                    if "hole_diameter_d0_mm" in fixed
                                    else base_input.hole_diameter_d0_mm
                                    if diameter == 12.0
                                    else diameter
                                ),
                                a1_mm=(
                                    base_input.a1_mm
                                    if "a1_mm" in fixed
                                    else base_input.a1_mm
                                    if diameter == 12.0
                                    else 5.0 * diameter
                                ),
                                a2_mm=candidate_a2,
                                a3_t_mm=(
                                    base_input.a3_t_mm
                                    if "a3_t_mm" in fixed
                                    else base_input.a3_t_mm
                                    if diameter == 12.0
                                    else max(7.0 * diameter, 80.0)
                                ),
                                a4_c_mm=candidate_a4,
                                rows_parallel_n=rows_parallel,
                                rows_perpendicular_m=rows_perpendicular,
                            )
                            try:
                                result = calculate_stabduebel(candidate)
                            except (ValueError, ZeroDivisionError):
                                continue
                            validation = validate_oenorm(candidate, result)
                            evaluated.append(EvaluatedVariant(candidate, result, validation))

    feasible = [
        variant
        for variant in evaluated
        if variant.validation.admissible
        and variant.result.passed
        and variant.result.governing_check.utilization >= min_utilization
        and variant.result.governing_check.utilization <= max_utilization
    ]
    if not feasible:
        inadmissible_count = sum(
            not variant.validation.admissible for variant in evaluated
        )
        return OptimizationResult(
            selected=None,
            evaluated=tuple(evaluated),
            evaluated_count=len(evaluated),
            feasible_count=0,
            message=(
                f"Keine der {len(evaluated)} geprüften Varianten erfüllt "
                f"Norm-/Geometrieprüfung und maximale Ausnutzung von "
                f"{max_utilization:.0%}. {inadmissible_count} Varianten sind "
                "normativ oder geometrisch nicht zulässig."
            ),
        )

    candidates = _preferred_candidates(feasible, fixed)

    if optimization_goal == "MIN_PLATE_THICKNESS":
        selected = min(
            candidates,
            key=lambda item: (
                item.input.plate_thickness_ts_mm,
                item.fastener_count,
                item.result.governing_check.utilization,
            ),
        )
    elif optimization_goal == "COMPACT_GEOMETRY":
        selected = min(candidates, key=lambda item: engineering_rank_key(item, optimization_goal))
    elif optimization_goal == "LOWER_UTILIZATION":
        selected = min(candidates, key=lambda item: engineering_rank_key(item, optimization_goal))
    elif maximize_utilization or optimization_goal == "MAXIMIZE_UTILIZATION":
        selected = min(candidates, key=lambda item: engineering_rank_key(item, "MAXIMIZE_UTILIZATION"))
    elif minimize_fasteners or optimization_goal == "MIN_FASTENER_COUNT":
        selected = min(candidates, key=lambda item: engineering_rank_key(item, "MIN_FASTENER_COUNT"))
    else:
        selected = min(candidates, key=lambda item: engineering_rank_key(item, "BALANCED_DESIGN"))

    return OptimizationResult(
        selected=selected,
        evaluated=tuple(evaluated),
        evaluated_count=len(evaluated),
        feasible_count=len(feasible),
        message=(
            f"{len(evaluated)} Varianten berechnet, "
            f"davon {len(feasible)} geeignet."
        ),
    )
