from dataclasses import asdict

import pytest

from ai.optimizer import (
    PREFERRED_DESIGN_DIAMETERS_MM,
    RESERVE_TARGET_UTILIZATION,
    curated_feasible_variants,
    optimize_stabduebel,
)
from calculations.stabduebel import StabduebelInput


BASE_FIXED = {
    "force_ed_kn", "timber_grade", "width_b_mm", "height_h_mm",
    "service_class", "load_duration_class",
}


@pytest.fixture(scope="module")
def base() -> StabduebelInput:
    return StabduebelInput(
        force_ed_kn=140, timber_grade="GL24h", width_b_mm=200,
        height_h_mm=240, service_class=1, load_duration_class="mittel",
    )


@pytest.mark.parametrize(
    ("goal", "expected"),
    [
        ("BALANCED_DESIGN", (16.0, 2, 3)),
        ("MIN_FASTENER_COUNT", (16.0, 2, 3)),
        ("COMPACT_GEOMETRY", (12.0, 2, 4)),
    ],
)
def test_engineering_goals_prefer_sensible_diameters(base, goal, expected):
    result = optimize_stabduebel(
        base, fixed_parameters=BASE_FIXED,
        minimize_fasteners=goal == "MIN_FASTENER_COUNT",
        optimization_goal=goal,
    )
    selected = result.selected
    assert selected is not None
    assert (
        selected.input.dowel_diameter_d_mm,
        selected.input.rows_parallel_n,
        selected.input.rows_perpendicular_m,
    ) == expected
    assert selected.input.dowel_diameter_d_mm in PREFERRED_DESIGN_DIAMETERS_MM
    assert selected.validation.admissible and selected.result.passed


def test_more_reserve_uses_central_target_not_absolute_minimum(base):
    result = optimize_stabduebel(
        base, fixed_parameters=BASE_FIXED, minimize_fasteners=False,
        optimization_goal="LOWER_UTILIZATION",
    )
    assert result.selected is not None
    assert result.selected.result.governing_check.utilization == pytest.approx(
        RESERVE_TARGET_UTILIZATION, abs=0.01,
    )


def test_maximize_utilization_never_selects_failed_variant(base):
    result = optimize_stabduebel(
        base, fixed_parameters=BASE_FIXED, maximize_utilization=True,
        optimization_goal="MAXIMIZE_UTILIZATION",
    )
    assert result.selected is not None
    assert result.selected.validation.admissible
    assert result.selected.result.passed
    assert result.selected.result.governing_check.utilization <= 1.0


def test_one_plate_is_calculated_but_not_austrian_admissible(base):
    result = optimize_stabduebel(base, fixed_parameters=BASE_FIXED)
    one_plate = [v for v in result.evaluated if v.input.number_of_plates_ns == 1]
    assert one_plate
    assert not any(v.validation.admissible for v in one_plate)
    assert all(v.input.shear_planes_s == 2 for v in one_plate)


def test_explicit_nonpreferred_diameter_remains_fixed(base):
    explicit = StabduebelInput(**{
        **asdict(base), "dowel_diameter_d_mm": 8.0,
    })
    result = optimize_stabduebel(
        explicit, fixed_parameters=BASE_FIXED | {"dowel_diameter_d_mm"},
        optimization_goal="COMPACT_GEOMETRY",
    )
    assert result.selected is not None
    assert all(v.input.dowel_diameter_d_mm == 8.0 for v in result.evaluated)


def test_curated_variants_include_distinct_12_and_16_candidates(base):
    result = optimize_stabduebel(
        base, fixed_parameters=BASE_FIXED,
        optimization_goal="BALANCED_DESIGN",
    )
    curated = curated_feasible_variants(
        result, "BALANCED_DESIGN", BASE_FIXED, 6,
    )
    assert {v.input.dowel_diameter_d_mm for v in curated} >= {12.0, 16.0}
    signatures = {
        (v.input.number_of_plates_ns, v.input.dowel_diameter_d_mm,
         v.input.rows_parallel_n, v.input.rows_perpendicular_m)
        for v in curated
    }
    assert len(signatures) == len(curated)
