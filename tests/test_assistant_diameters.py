from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import patch

from ai.assistant import StabduebelAssistant
from ai.optimizer import SUPPORTED_DOWEL_DIAMETERS_MM, optimize_stabduebel
from calculations.stabduebel import StabduebelInput


def respond(assistant: StabduebelAssistant, prompt: str):
    assistant.state.parameters.setdefault("service_class", 1)
    assistant.state.parameters.setdefault("load_duration_class", "mittel")
    assistant.state.fixed_parameters.update({"service_class", "load_duration_class"})
    assistant.state.parameters.setdefault("width_b_mm", 200.0)
    assistant.state.parameters.setdefault("height_h_mm", 240.0)
    assistant.state.parameters.setdefault("number_of_plates_ns", 2)
    assistant.state.parameters.setdefault("plate_thickness_ts_mm", 6.0)
    assistant.state.parameters.setdefault("side_thickness_t1_mm", 60.0)
    assistant.state.parameters.setdefault("middle_thickness_t2_mm", 68.0)
    assistant.state.parameters.setdefault("slot_air_per_cut_ts_l_mm", 1.0)
    assistant._set_connection_state(int(assistant.state.parameters["number_of_plates_ns"]))
    assistant.state.minimize_fasteners = True
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(prompt)


def test_explicit_diameter_12_is_fixed_and_calculated() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, "140 kN, GL24h, verwende Ø12 mm")

    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 12.0
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 12.0
    assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters


def test_explicit_diameter_16_is_fixed_calculated_and_validated() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, "140 kN, GL24h, nimm 16er Dübel")

    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 16.0
    selected = assistant.state.last_optimization.selected
    assert selected is not None
    assert selected.validation.admissible
    assert selected.result.passed
    assert selected.input.a1_mm >= 5.0 * 16.0
    assert selected.input.a2_mm >= 3.0 * 16.0
    assert selected.input.a3_t_mm >= 7.0 * 16.0


def test_followup_switches_12_to_16_without_changing_other_user_values() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h, Ø12 mm")
    reply = respond(assistant, "nimm 16er Dübel")

    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 16.0
    assert reply.result.input.force_ed_kn == 140.0
    assert reply.result.input.timber_grade == "GL24h"


def test_followup_switches_16_to_12_with_contextual_mm_phrase() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h, Ø16 mm")
    reply = respond(assistant, "doch wieder mit 12 mm")

    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 12.0
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 12.0


def test_normatively_invalid_diameter_is_not_calculated_as_solution() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, "140 kN, GL24h, Ø30 mm")

    assert reply.result is None
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 30.0
    assert "6 mm < d < 30 mm" in reply.text


def test_optimizer_evaluates_multiple_supported_diameters() -> None:
    optimization = optimize_stabduebel(
        StabduebelInput(),
        minimize_fasteners=True,
    )

    evaluated_diameters = {
        item.input.dowel_diameter_d_mm for item in optimization.evaluated
    }
    assert len(SUPPORTED_DOWEL_DIAMETERS_MM) > 1
    assert {12.0, 16.0}.issubset(evaluated_diameters)
    assert optimization.selected is not None
    assert optimization.selected.validation.admissible
    assert optimization.selected.result.passed


def test_explicit_warning_range_is_checked_but_not_auto_recommended() -> None:
    optimization = optimize_stabduebel(
        replace(StabduebelInput(), dowel_diameter_d_mm=25.0),
        fixed_parameters={"dowel_diameter_d_mm"},
    )

    assert 25.0 not in SUPPORTED_DOWEL_DIAMETERS_MM
    assert all(item.input.dowel_diameter_d_mm == 25.0 for item in optimization.evaluated)


def test_16_mm_followup_is_fixed_through_complete_data_flow() -> None:
    assistant = StabduebelAssistant()
    respond(
        assistant,
        "Bemesse einen Stabdübelanschluss für 140 kN mit GL24h und "
        "möglichst wenigen Stabdübeln.",
    )
    extracted, _ = assistant._extract("16 mm Stabdübel")
    reply = respond(assistant, "16 mm Stabdübel")

    assert extracted["dowel_diameter_d_mm"] == 16.0
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 16.0
    assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters
    optimization = assistant.state.last_optimization
    assert optimization is not None
    assert optimization.evaluated
    assert {
        variant.input.dowel_diameter_d_mm
        for variant in optimization.evaluated
    } == {16.0}
    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 16.0
    assert "Ø16 mm" in reply.text
    assert "Ø12 mm" not in reply.text


def test_explicit_diameter_sequence_always_replaces_previous_value() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h, möglichst wenige Stabdübel")

    for wording, expected in (
        ("16 mm Stabdübel", 16.0),
        ("12 mm", 12.0),
        ("20er", 20.0),
        ("wieder 16er", 16.0),
    ):
        reply = respond(assistant, wording)
        assert assistant.state.parameters["dowel_diameter_d_mm"] == expected
        assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters
        assert assistant.state.last_optimization is not None
        assert all(
            variant.input.dowel_diameter_d_mm == expected
            for variant in assistant.state.last_optimization.evaluated
        )
        assert reply.result is not None
        assert reply.result.input.dowel_diameter_d_mm == expected
        assert f"Ø{expected:g} mm" in reply.text


def test_all_required_16_mm_wordings_have_deterministic_priority() -> None:
    wordings = (
        "16 mm Stabdübel",
        "Ø16",
        "16er",
        "16er Dübel",
        "nimm 16 mm",
        "jetzt mit 16er",
        "ändere auf 16 mm",
    )
    for wording in wordings:
        assistant = StabduebelAssistant()
        respond(assistant, "140 kN GL24h 2 × 4 Stabdübel")
        reply = respond(assistant, wording)

        assert assistant.state.parameters["dowel_diameter_d_mm"] == 16.0
        assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters
        assert assistant.state.last_optimization is not None
        assert all(
            variant.input.dowel_diameter_d_mm == 16.0
            for variant in assistant.state.last_optimization.evaluated
        )
        assert reply.result is not None
        assert reply.result.input.dowel_diameter_d_mm == 16.0
        assert "Ø16 mm" in reply.text
        assert "Ø12 mm" not in reply.text


def test_deterministic_user_text_overrides_wrong_llm_diameter() -> None:
    llm_output = {
        key: None
        for key in (
            "force_ed_kn", "timber_grade", "dowel_diameter_d_mm",
            "number_of_plates_ns", "plate_thickness_ts_mm", "width_b_mm",
            "height_h_mm", "rows_parallel_n", "rows_perpendicular_m",
            "total_fastener_count", "a1_mm", "a2_mm", "a3_t_mm",
            "a4_c_mm", "e1_mm", "e2_mm", "max_utilization",
        )
    }
    llm_output.update(
        intent="OPTIMIZE",
        action="OPTIMIZE",
        clarification_parameter=None,
        dowel_diameter_d_mm=12.0,
        minimize_fasteners=False,
        optimize_diameter=True,
        explain_governing=False,
    )

    enforced = StabduebelAssistant._enforce_explicit_diameter_input(
        "16 mm Stabdübel", llm_output
    )

    assert enforced["dowel_diameter_d_mm"] == 16.0
    assert enforced["optimize_diameter"] is False
    assert enforced["intent"] == "PARAMETER_CHANGE"


def test_every_automatic_diameter_and_explicit_special_diameter_are_exact() -> None:
    for diameter in (*SUPPORTED_DOWEL_DIAMETERS_MM, 25.0):
        assistant = StabduebelAssistant()
        respond(assistant, "140 kN GL24h, möglichst wenige Stabdübel")
        reply = respond(assistant, f"Ø{diameter:g}")

        assert assistant.state.parameters["dowel_diameter_d_mm"] == diameter
        assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters
        assert assistant.state.last_optimization is not None
        assert all(
            variant.input.dowel_diameter_d_mm == diameter
            for variant in assistant.state.last_optimization.evaluated
        )
        assert reply.result is not None
        assert reply.result.input.dowel_diameter_d_mm == diameter
        assert f"Ø{diameter:g} mm" in reply.text
