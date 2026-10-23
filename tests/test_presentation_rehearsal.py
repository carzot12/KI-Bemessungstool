from __future__ import annotations

from dataclasses import asdict

import pytest

from calculations.stabduebel import StabduebelInput
from desktop.bridge import DesktopBridge


def valid_bridge() -> DesktopBridge:
    bridge = DesktopBridge(demo_enabled=False)
    data = StabduebelInput(
        force_ed_kn=140, timber_grade="GL24h", width_b_mm=200,
        height_h_mm=240, service_class=1, load_duration_class="mittel",
        number_of_plates_ns=2, plate_thickness_ts_mm=6,
        side_thickness_t1_mm=45, middle_thickness_t2_mm=98,
        dowel_diameter_d_mm=16, hole_diameter_d0_mm=16,
        rows_parallel_n=2, rows_perpendicular_m=3,
        a1_mm=80, a2_mm=48, a3_t_mm=112, a4_c_mm=72,
        e1_mm=20, e2_mm=20,
    )
    assert bridge.manual_calculate(asdict(data))["ok"] is True
    return bridge


def test_one_plate_request_runs_kernel_and_selects_one_plate() -> None:
    bridge = valid_bridge()
    reply = bridge.assistant.execute_local_command(
        "Geht die Verbindung auch nur mit einem innenliegenden Stahlblech?"
    )
    assert "nicht normkonform" not in reply.text
    assert reply.result is not None
    assert reply.result.input.number_of_plates_ns == 1
    assert reply.result.input.shear_planes_s == 2
    assert bridge.assistant.state.parameters["number_of_plates_ns"] == 1


def test_reverse_capacity_and_ninety_percent_are_kernel_verified() -> None:
    bridge = valid_bridge()
    maximum = bridge.assistant.execute_local_command(
        "Wie viel Zugkraft hält diese Verbindung maximal aus?"
    )
    assert "164.18 kN" in maximum.text
    assert bridge.assistant.state.last_maximum_load["utilization"] == pytest.approx(1.0)

    target = bridge.assistant.execute_local_command(
        "Und wie viel darf ich ansetzen, wenn ich maximal 90 % Ausnutzung haben möchte?"
    )
    assert "147.76 kN" in target.text
    assert bridge.assistant.state.last_maximum_load["utilization"] == pytest.approx(0.9)


def test_selected_connection_summary_contains_result_without_recalculation() -> None:
    bridge = valid_bridge()
    before = bridge.assistant.state.last_result
    reply = bridge.assistant.execute_local_command(
        "Welche Verbindung haben wir jetzt eigentlich gewählt?"
    )
    assert "140 kN" in reply.text
    assert "2 × 3 = 6" in reply.text
    assert "85.3 %" in reply.text
    assert "Verbindungsmittel im Holz" in reply.text
    assert bridge.assistant.state.last_result is before


def test_bridge_keeps_capacity_action_text(monkeypatch) -> None:
    bridge = valid_bridge()
    local = bridge.assistant.execute_local_command
    monkeypatch.setattr(bridge.assistant, "respond", local)

    maximum = bridge.send_message({
        "text": "Wie viel Zugkraft hält diese Verbindung maximal aus?",
    })
    assert "164.18 kN" in maximum["data"]["conversation"][-1]["content"]
