from __future__ import annotations

from calculations.stabduebel import StabduebelInput
from ui.connection_visualizer import ConnectionVisualizerData


def visual_data(**overrides) -> ConnectionVisualizerData:
    return ConnectionVisualizerData.from_input(StabduebelInput(**overrides))


def test_visualizer_receives_one_internal_plate() -> None:
    data = visual_data(number_of_plates_ns=1, width_b_mm=126.0)
    assert data.plate_count == 1
    assert data.shear_planes == 2


def test_visualizer_receives_two_internal_plates() -> None:
    data = visual_data(number_of_plates_ns=2)
    assert data.plate_count == 2
    assert data.shear_planes == 4


def test_visualizer_fastener_count_is_exact_product() -> None:
    assert visual_data(rows_parallel_n=2, rows_perpendicular_m=3).fastener_count == 6
    assert visual_data(rows_parallel_n=3, rows_perpendicular_m=4).fastener_count == 12


def test_visualizer_uses_actual_diameter_section_and_force() -> None:
    first = visual_data(
        dowel_diameter_d_mm=12.0,
        width_b_mm=200.0,
        height_h_mm=240.0,
        force_ed_kn=140.0,
    )
    second = visual_data(dowel_diameter_d_mm=16.0)

    assert first.diameter_mm == 12.0
    assert second.diameter_mm == 16.0
    assert (first.width_mm, first.height_mm) == (200.0, 240.0)
    assert first.force_ed_kn == 140.0
    assert first.force_label == "FEd = 140 kN"
