from __future__ import annotations

import json

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
    assert data.side_thickness_t1_mm == 40.0
    assert data.middle_thickness_t2_mm == 110.0
    assert data.dowel_diameter_d_mm == 16.0
    assert (data.rows_parallel_n, data.rows_perpendicular_m) == (2, 3)
    assert data.rows_parallel_n * data.rows_perpendicular_m == 6
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
    assert payload["currentResult"]["input"]["dowel_diameter_d_mm"] == 16.0


def test_visualization_model_contains_only_python_snapshot_values() -> None:
    data = build_demo_snapshot().input
    model = visualization_model(data)

    assert model == {
        "sectionWidthMm": 200.0,
        "sectionHeightMm": 240.0,
        "plateCount": 2,
        "plateThicknessMm": 5.0,
        "sideThicknessMm": 40.0,
        "middleThicknessMm": 110.0,
        "dowelDiameterMm": 16.0,
        "rowsParallel": 2,
        "rowsPerpendicular": 3,
        "forceEdKn": 140.0,
        "a1Mm": 80.0,
        "a2Mm": 48.0,
        "a3tMm": 112.0,
        "a4cMm": 48.0,
    }


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
        "model": "gpt-5-mini",
        "detail": "Connectivity-Test fehlgeschlagen",
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
