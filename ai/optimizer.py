from __future__ import annotations

"""Kleine deterministische Variantenuntersuchung für den V1-Prototyp."""

from dataclasses import dataclass, replace

from calculations.stabduebel import (
    StabduebelInput,
    StabduebelResult,
    calculate_stabduebel,
)


# Fachlich festgelegter, bewusst kleiner V1-Suchraum. Andere Eingabewerte
# bleiben unverändert; jede Kombination wird vom bestehenden Rechenkern geprüft.
ROWS_PARALLEL = (1, 2, 3, 4)
ROWS_PERPENDICULAR = (2, 3, 4, 5, 6)
SUPPORTED_DOWEL_DIAMETERS_MM = (12.0,)


@dataclass(frozen=True, slots=True)
class EvaluatedVariant:
    input: StabduebelInput
    result: StabduebelResult

    @property
    def fastener_count(self) -> int:
        return self.input.rows_parallel_n * self.input.rows_perpendicular_m


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    selected: EvaluatedVariant | None
    evaluated_count: int
    feasible_count: int
    message: str


def optimize_stabduebel(
    base_input: StabduebelInput,
    *,
    fixed_parameters: set[str] | None = None,
    max_utilization: float = 1.0,
    minimize_fasteners: bool = True,
) -> OptimizationResult:
    """Prüft den V1-Suchraum ausschließlich mit ``calculate_stabduebel``."""
    fixed = fixed_parameters or set()
    diameters = (
        (base_input.dowel_diameter_d_mm,)
        if "dowel_diameter_d_mm" in fixed
        else SUPPORTED_DOWEL_DIAMETERS_MM
    )
    if any(diameter not in SUPPORTED_DOWEL_DIAMETERS_MM for diameter in diameters):
        return OptimizationResult(
            selected=None,
            evaluated_count=0,
            feasible_count=0,
            message="Der V1-Suchraum unterstützt ausschließlich Stabdübel Ø12 mm.",
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

    evaluated: list[EvaluatedVariant] = []
    for diameter in diameters:
        for rows_parallel in parallel_values:
            for rows_perpendicular in perpendicular_values:
                candidate = replace(
                    base_input,
                    dowel_diameter_d_mm=diameter,
                    rows_parallel_n=rows_parallel,
                    rows_perpendicular_m=rows_perpendicular,
                )
                try:
                    result = calculate_stabduebel(candidate)
                except (ValueError, ZeroDivisionError):
                    continue
                evaluated.append(EvaluatedVariant(candidate, result))

    feasible = [
        variant
        for variant in evaluated
        if variant.result.passed
        and variant.result.governing_check.utilization <= max_utilization
    ]
    if not feasible:
        return OptimizationResult(
            selected=None,
            evaluated_count=len(evaluated),
            feasible_count=0,
            message=(
                f"Keine der {len(evaluated)} geprüften Varianten erfüllt "
                f"die maximale Ausnutzung von {max_utilization:.0%}."
            ),
        )

    if minimize_fasteners:
        selected = min(
            feasible,
            key=lambda item: (
                item.fastener_count,
                item.result.governing_check.utilization,
            ),
        )
    else:
        selected = min(
            feasible,
            key=lambda item: item.result.governing_check.utilization,
        )

    return OptimizationResult(
        selected=selected,
        evaluated_count=len(evaluated),
        feasible_count=len(feasible),
        message=(
            f"{len(evaluated)} Varianten berechnet, "
            f"davon {len(feasible)} geeignet."
        ),
    )
