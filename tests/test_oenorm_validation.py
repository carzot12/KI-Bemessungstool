from dataclasses import replace

import pytest

from ai.optimizer import optimize_stabduebel
from calculations.oenorm_validation import ValidationStatus, validate_oenorm
from calculations.stabduebel import StabduebelInput, calculate_stabduebel


def _status(data: StabduebelInput, name: str) -> ValidationStatus:
    validation = validate_oenorm(data)
    return next(check.status for check in validation.checks if check.name == name)


def test_reference_geometry_is_admissible_with_documented_open_checks() -> None:
    data = StabduebelInput()
    result = calculate_stabduebel(data)
    validation = validate_oenorm(data, result)

    assert validation.admissible
    assert _status(data, "Achsabstand a1") is ValidationStatus.PASSED
    assert _status(data, "Achsabstand a2") is ValidationStatus.PASSED
    assert _status(data, "Beanspruchter Endabstand a3,t") is ValidationStatus.PASSED
    assert _status(data, "Unbeanspruchter Randabstand a4,c") is ValidationStatus.PASSED
    assert any(
        check.status is ValidationStatus.UNVERIFIED
        for check in validation.checks
    )


@pytest.mark.parametrize(
    ("changes", "check_name"),
    [
        ({"a1_mm": 59.9}, "Achsabstand a1"),
        ({"a2_mm": 35.9}, "Achsabstand a2"),
        ({"a3_t_mm": 83.9}, "Beanspruchter Endabstand a3,t"),
        ({"a4_c_mm": 35.9}, "Unbeanspruchter Randabstand a4,c"),
        ({"dowel_diameter_d_mm": 6.0}, "Stabdübeldurchmesser"),
        ({"dowel_diameter_d_mm": 30.0}, "Stabdübeldurchmesser"),
        (
            {"rows_parallel_n": 1, "rows_perpendicular_m": 1},
            "Mindestanzahl Stabdübel",
        ),
        ({"shear_planes_s": 2}, "Mindestanzahl Scherflächen"),
        (
            {"number_of_plates_ns": 1, "shear_planes_s": 4},
            "Scherflächen und innenliegende Stahlbleche",
        ),
        (
            {"number_of_plates_ns": 3, "shear_planes_s": 6},
            "Anwendungsgrenze des V1-Rechenmodells",
        ),
        (
            {"dowel_steel_grade": "S355", "dowel_fu_k_n_mm2": 360.0},
            "Stabdübel-Stahlsorte und Zugfestigkeit",
        ),
        (
            {"height_h_mm": 239.0},
            "Anordnung im Querschnitt (Höhe)",
        ),
        (
            {"width_b_mm": 199.0},
            "Schichtaufbau im Querschnitt (Breite)",
        ),
    ],
)
def test_invalid_designs_are_rejected(changes: dict, check_name: str) -> None:
    data = replace(StabduebelInput(), **changes)
    validation = validate_oenorm(data)

    assert not validation.admissible
    failed = {check.name for check in validation.failures}
    assert check_name in failed


def test_large_but_permitted_diameter_creates_warning() -> None:
    data = replace(
        StabduebelInput(),
        dowel_diameter_d_mm=25.0,
        a1_mm=125.0,
        a2_mm=75.0,
        a3_t_mm=175.0,
        a4_c_mm=75.0,
        height_h_mm=375.0,
    )
    validation = validate_oenorm(data)

    assert validation.admissible
    assert any(
        check.name == "Großer Stabdübeldurchmesser"
        and check.status is ValidationStatus.WARNING
        for check in validation.checks
    )


def test_failed_capacity_is_part_of_technical_validation() -> None:
    data = replace(StabduebelInput(), force_ed_kn=1000.0)
    result = calculate_stabduebel(data)
    validation = validate_oenorm(data, result)

    assert not result.passed
    assert not validation.admissible
    assert "Tragfähigkeitsnachweise" in {
        check.name for check in validation.failures
    }


def test_too_small_net_section_is_rejected_by_calculation_input_validation() -> None:
    data = replace(StabduebelInput(), height_h_mm=48.0)
    with pytest.raises(ValueError, match="h - m·d"):
        calculate_stabduebel(data)


def test_optimizer_never_selects_normatively_invalid_fixed_geometry() -> None:
    data = replace(StabduebelInput(), a1_mm=40.0)
    optimization = optimize_stabduebel(data, minimize_fasteners=True)

    assert optimization.selected is None
    assert optimization.evaluated
    assert all(not item.validation.admissible for item in optimization.evaluated)


def test_one_plate_is_not_silently_replaced_and_is_not_selected() -> None:
    data = replace(StabduebelInput(), number_of_plates_ns=1)
    optimization = optimize_stabduebel(
        data,
        fixed_parameters={"number_of_plates_ns"},
        minimize_fasteners=True,
    )

    assert optimization.selected is None
    assert optimization.evaluated
    assert all(item.input.number_of_plates_ns == 1 for item in optimization.evaluated)
