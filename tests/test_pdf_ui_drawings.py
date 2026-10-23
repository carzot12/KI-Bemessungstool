from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from calculations.stabduebel import StabduebelInput
from desktop.bridge import DesktopBridge


def test_pdf_rejects_a_geometry_snapshot_different_from_the_ui(technical_drawings) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    geometry = dict(bridge.bootstrap()["data"]["connectionGeometry"])
    geometry["dowelDiameterMm"] = 99

    result = bridge.create_pdf_report({
        "type": "calculation",
        "geometrySnapshot": geometry,
        "technicalDrawings": technical_drawings,
    })

    assert result == {
        "status": "error",
        "message": "UI- und Berichtgeometrie stimmen nicht überein.",
    }


@pytest.mark.parametrize("design, expected", [
    (
        StabduebelInput(
            number_of_plates_ns=1,
            width_b_mm=126,
            side_thickness_t1_mm=60,
            dowel_diameter_d_mm=10,
            hole_diameter_d0_mm=11,
            rows_parallel_n=3,
            rows_perpendicular_m=3,
        ),
        {"plateCount": 1, "dowelDiameterMm": 10, "rowsParallel": 3,
         "rowsPerpendicular": 3, "sectionWidthMm": 126},
    ),
    (
        StabduebelInput(
            number_of_plates_ns=2,
            width_b_mm=220,
            side_thickness_t1_mm=65,
            middle_thickness_t2_mm=78,
            plate_thickness_ts_mm=6,
            dowel_diameter_d_mm=16,
            hole_diameter_d0_mm=17,
            rows_parallel_n=2,
            rows_perpendicular_m=4,
        ),
        {"plateCount": 2, "dowelDiameterMm": 16, "rowsParallel": 2,
         "rowsPerpendicular": 4, "sectionWidthMm": 220},
    ),
])
def test_pdf_receives_the_exact_current_ui_snapshot_for_one_and_two_plates(
    tmp_path, monkeypatch, technical_drawings, design, expected,
) -> None:
    bridge = DesktopBridge(demo_enabled=False)
    snapshot = bridge.manual_calculate(asdict(design))["data"]
    geometry = snapshot["connectionGeometry"]
    captured = {}

    class Window:
        def create_file_dialog(self, _dialog_type, **_kwargs):
            return str(tmp_path / "snapshot.pdf")

    def fake_create_report(report_snapshot, _report_type, output_dir, filename=None,
                           technical_drawings=None):
        captured["geometry"] = report_snapshot["connectionGeometry"]
        captured["drawings"] = technical_drawings
        target = Path(output_dir) / filename
        target.write_bytes(b"%PDF-test")
        return target

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(
        windows=[Window()], SAVE_DIALOG=20,
    ))
    monkeypatch.setattr("desktop.bridge.create_report", fake_create_report)

    result = bridge.create_pdf_report({
        "type": "calculation",
        "geometrySnapshot": geometry,
        "technicalDrawings": technical_drawings,
    })

    assert result["status"] == "success"
    assert captured["geometry"] == geometry
    assert captured["drawings"] is technical_drawings
    assert expected.items() <= geometry.items()
    assert len(geometry["platePositionsMm"]) == expected["plateCount"]
    assert len(geometry["dowelPositionsLeftMm"]) == (
        expected["rowsParallel"] * expected["rowsPerpendicular"]
    )
