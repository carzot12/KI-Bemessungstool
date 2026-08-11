from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import patch

from ai.assistant import StabduebelAssistant
from ai.optimizer import SUPPORTED_DOWEL_DIAMETERS_MM, optimize_stabduebel
from calculations.stabduebel import StabduebelInput


def respond(assistant: StabduebelAssistant, prompt: str):
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
