from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from desktop.bridge import DesktopBridge
from desktop.serializers import build_demo_snapshot, visualization_model


def test_demo_snapshot_uses_real_core_and_reference_geometry() -> None:
    demo = build_demo_snapshot()
    data = demo.input

    assert data.force_ed_kn == 140.0
    assert data.timber_grade == "GL24h"
    assert data.width_b_mm == 200.0
    assert data.height_h_mm == 240.0
    assert data.number_of_plates_ns == 2
    assert data.plate_thickness_ts_mm == 5.0
    assert data.side_thickness_t1_mm == 60.0
    assert data.middle_thickness_t2_mm == 70.0
    assert data.dowel_diameter_d_mm == 12.0
    assert (data.rows_parallel_n, data.rows_perpendicular_m) == (2, 4)
    assert data.rows_parallel_n * data.rows_perpendicular_m == 8
    assert 2 * data.side_thickness_t1_mm + 2 * data.plate_thickness_ts_mm + data.middle_thickness_t2_mm == 200.0
    assert demo.result.input == data


def test_bridge_snapshot_is_json_serializable_and_complete() -> None:
    envelope = DesktopBridge(demo_enabled=True).bootstrap()
    payload = envelope["data"]

    json.dumps(envelope)
    assert envelope["ok"] is True
    assert {
        "technicalState", "currentResult", "lastOptimization", "variants",
        "agentStatus", "conversation", "visualizationModel",
    } <= payload.keys()
    assert payload["demoMode"] is True
    assert len(payload["variants"]) == 3
    assert payload["currentResult"]["input"]["dowel_diameter_d_mm"] == 12.0


def test_visualization_model_contains_only_python_snapshot_values() -> None:
    data = build_demo_snapshot().input
    model = visualization_model(data)

    assert {
        "sectionWidthMm": 200.0,
        "sectionHeightMm": 240.0,
        "plateCount": 2,
        "plateThicknessMm": 5.0,
        "sideThicknessMm": 60.0,
        "middleThicknessMm": 70.0,
        "dowelDiameterMm": 12.0,
        "rowsParallel": 2,
        "rowsPerpendicular": 4,
        "forceEdKn": 140.0,
        "a1Mm": 60.0,
        "a2Mm": 40.0,
        "a3tMm": 85.0,
        "a4cMm": 60.0,
    }.items() <= model.items()


def test_reference_drawing_geometry_values_are_consistent() -> None:
    from calculations.stabduebel import StabduebelInput

    data = StabduebelInput(
        width_b_mm=200.0, height_h_mm=240.0, side_thickness_t1_mm=60.0,
        middle_thickness_t2_mm=70.0, plate_thickness_ts_mm=5.0,
        number_of_plates_ns=2, dowel_diameter_d_mm=12.0,
        rows_parallel_n=2, rows_perpendicular_m=4, a1_mm=60.0,
        a2_mm=40.0, a3_t_mm=85.0, a4_c_mm=60.0, e1_mm=20.0, e2_mm=20.0,
    )
    model = visualization_model(data)
    assert model["sectionWidthMm"] == 200.0
    assert model["sectionHeightMm"] == 240.0
    assert model["crossSectionLayersMm"] == [60.0, 5.0, 70.0, 5.0, 60.0]
    assert sum(model["crossSectionLayersMm"]) == model["sectionWidthMm"]
    assert model["rowPositionsMm"] == [60.0, 100.0, 140.0, 180.0]
    assert model["columnPositionsMm"] == [85.0, 145.0]
    assert model["plateLengthMm"] == 330.0
    assert model["plateHeightMm"] == 160.0
    assert model["plateTopMm"] == 40.0
    assert model["plateBottomMm"] == 200.0
    assert model["platePositionsMm"] == [62.5, 137.5]
    assert len(model["dowelPositionsLeftMm"]) == 8
    assert len(model["dowelPositionsRightMm"]) == 8
    assert model["topTimberEdgeDistanceMm"] == 60.0
    assert model["bottomTimberEdgeDistanceMm"] == 60.0


def test_reference_section_geometry_uses_shared_plate_and_dowel_coordinates() -> None:
    from calculations.stabduebel import StabduebelInput

    data = StabduebelInput(
        width_b_mm=200.0, height_h_mm=240.0,
        side_thickness_t1_mm=60.0, middle_thickness_t2_mm=68.0,
        plate_thickness_ts_mm=6.0, number_of_plates_ns=2,
        dowel_diameter_d_mm=12.0, rows_parallel_n=2,
        rows_perpendicular_m=4, a1_mm=60.0, a2_mm=40.0,
        a3_t_mm=85.0, a4_c_mm=60.0, e1_mm=20.0, e2_mm=20.0,
    )
    model = visualization_model(data)
    render_scale = 1.45

    assert model["plateTopMm"] == 40.0
    assert model["plateBottomMm"] == 200.0
    assert model["plateHeightMm"] == 160.0
    assert model["rowPositionsMm"] == [60.0, 100.0, 140.0, 180.0]
    assert model["sectionWidthMm"] == 200.0
    assert model["sectionHeightMm"] == 240.0
    assert model["crossSectionLayersMm"] == [60.0, 6.0, 68.0, 6.0, 60.0]
    assert abs(
        (model["sectionWidthMm"] * render_scale)
        / (model["sectionHeightMm"] * render_scale)
        - 200.0 / 240.0
    ) < 1e-12
    assert (
        model["dowelDiameterMm"] * render_scale
        / (model["plateThicknessMm"] * render_scale)
    ) == 2.0


def test_demo_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KI_TOOL_DEMO_SNAPSHOT", "0")
    payload = DesktopBridge().bootstrap()["data"]
    assert payload["demoMode"] is False
    assert payload["visualizationModel"] is None


def test_agent_error_status_is_not_reported_as_online() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    bridge.assistant.llm_status = "ERROR"
    bridge.assistant.llm_error = "Connectivity-Test fehlgeschlagen"
    status = bridge.bootstrap()["data"]["agentStatus"]
    assert status == {
        "mode": "error",
        "label": "KI FEHLER",
        "model": "qwen3:8b",
        "detail": "Connectivity-Test fehlgeschlagen",
        "provider": "local",
        "available": True,
        "privacyDetail": "Daten bleiben auf diesem Gerät",
    }


def test_manual_calculation_updates_shared_assistant_state() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    payload = bridge.form_options()["manualDefaults"]
    payload.update(timber_grade="GL24h", force_ed_kn=140.0)
    result = bridge.manual_calculate(payload)["data"]
    assert bridge.assistant.state.last_result is not None
    assert result["currentResult"]["input"]["force_ed_kn"] == 140.0
    assert result["technicalState"]["timber_grade"] == "GL24h"


def test_compact_calculation_uses_same_state_and_conversation() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    payload = {
        "force_ed_kn": 140, "timber_grade": "GL24h",
        "width_b_mm": 200, "height_h_mm": 240,
        "service_class": 1, "load_duration_class": "mittel",
        "objective": "MIN_FASTENER_COUNT",
    }
    snapshot = bridge.compact_calculate(payload)["data"]
    assert bridge.assistant.state.parameters["force_ed_kn"] == 140.0
    assert snapshot["conversation"][-2]["role"] == "user"
    assert snapshot["currentResult"] is not None


def test_pdf_dialog_uses_pywebview_621_filter_and_pdf_suffix(tmp_path, monkeypatch) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    chosen = tmp_path / "test 1_Berechnungsbericht"
    calls = {}

    class Window:
        def create_file_dialog(self, dialog_type, **kwargs):
            calls.update(dialog_type=dialog_type, **kwargs)
            return [str(chosen)]

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(
        windows=[Window()], SAVE_DIALOG=20,
    ))
    result = bridge.create_pdf_report({"type": "calculation"})

    assert result["status"] == "success"
    assert result["path"].endswith(".pdf")
    assert result["size"] > 0
    assert Path(result["path"]).is_file()
    assert calls["save_filename"] == "Zugstoß – 4-schnittiger Stabdübelanschluss.pdf"
    assert calls["file_types"] == ("PDF (*.pdf)",)


def test_pdf_dialog_cancel_is_not_an_error(monkeypatch) -> None:
    bridge = DesktopBridge(demo_enabled=True)

    class Window:
        def create_file_dialog(self, dialog_type, **kwargs):
            return None

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(
        windows=[Window()], SAVE_DIALOG=20,
    ))

    assert bridge.create_pdf_report({"type": "calculation"}) == {
        "status": "cancelled",
    }


def test_pdf_dialog_accepts_string_result_and_writes_exact_target(tmp_path, monkeypatch) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    chosen = tmp_path / "Direkter Stringpfad"

    class Window:
        def create_file_dialog(self, dialog_type, **kwargs):
            return str(chosen)

    monkeypatch.setitem(sys.modules, "webview", SimpleNamespace(
        windows=[Window()], SAVE_DIALOG=20,
    ))

    result = bridge.create_pdf_report({"type": "calculation"})
    expected = chosen.with_suffix(".pdf")
    assert result == {
        "status": "success",
        "path": str(expected),
        "size": expected.stat().st_size,
    }
    assert expected.is_file()
    assert expected.read_bytes().startswith(b"%PDF-")


def test_adopting_variant_preserves_project_and_recommendation() -> None:
    bridge = DesktopBridge(demo_enabled=True)
    bridge.set_project_name({"project_name": "test 1"})
    before = bridge.bootstrap()["data"]
    adopted = bridge.adopt_variant({"variant_id": "variant-2"})["data"]

    assert adopted["projectName"] == "test 1"
    assert adopted["currentVariant"]["id"] == "variant-2"
    assert adopted["recommendedVariant"]["input"] == before["recommendedVariant"]["input"]
