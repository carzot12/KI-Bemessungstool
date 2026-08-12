from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant
from calculations.oenorm_validation import ValidationStatus, validate_oenorm
from calculations.stabduebel import StabduebelInput, calculate_stabduebel
from ui.connection_visualizer import ConnectionVisualizerData


def say(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


def test_reference_cross_section_build_up_is_exact() -> None:
    data = StabduebelInput()
    assert 2 * data.side_thickness_t1_mm + 2 * data.plate_thickness_ts_mm + data.middle_thickness_t2_mm == 200.0


def test_chat_recognizes_plate_count_and_thickness_together() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "200x240")
    say(assistant, "2 bleche je 6mm")
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.parameters["number_of_plates_ns"] == 2
    assert assistant.state.parameters["plate_thickness_ts_mm"] == 6.0


def test_t1_creates_confirmable_t2_proposal_without_silent_assignment() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "200x240, 2 Bleche je 6mm")
    proposal = say(assistant, "t1 60")

    assert assistant.state.parameters["side_thickness_t1_mm"] == 60.0
    assert "middle_thickness_t2_mm" not in assistant.state.parameters
    assert assistant.state.pending_geometry_proposal == {
        "middle_thickness_t2_mm": 68.0
    }
    assert "t2 = 200 - 2·60 - 2·6 = 68 mm" in proposal.text

    say(assistant, "ja")
    assert assistant.state.parameters["middle_thickness_t2_mm"] == 68.0
    assert "middle_thickness_t2_mm" in assistant.state.fixed_parameters


def test_middle_timber_and_slot_allowance_are_separate_parameters() -> None:
    assistant = StabduebelAssistant()
    extracted = assistant._fallback_extract("mittelholz 68 mm, ts,L 1.0 mm")
    assert extracted["middle_thickness_t2_mm"] == 68.0
    assert extracted["slot_air_per_cut_ts_l_mm"] == 1.0
    assert extracted["plate_thickness_ts_mm"] is None


def test_inconsistent_explicit_geometry_is_preserved_and_reported() -> None:
    assistant = StabduebelAssistant()
    reply = say(
        assistant,
        "140 kN GL24h 200x240 mm, 2 Bleche je 6 mm, "
        "t1 70, t2 68, ts,L 1, NK1 mittel, möglichst wenige Stabdübel",
    )

    assert reply.result is None
    assert assistant.state.parameters["side_thickness_t1_mm"] == 70.0
    assert assistant.state.parameters["middle_thickness_t2_mm"] == 68.0
    assert "220 mm" in reply.text
    assert "b = 200 mm" in reply.text

    data = StabduebelInput(side_thickness_t1_mm=70.0)
    check = next(
        item for item in validate_oenorm(data).checks
        if item.name == "Schichtaufbau im Querschnitt (Breite)"
    )
    assert check.status is ValidationStatus.FAILED
    assert check.required == 220.0


def test_visualizer_receives_complete_cross_section_geometry() -> None:
    visual = ConnectionVisualizerData.from_input(StabduebelInput())
    assert visual.side_thickness_mm == 60.0
    assert visual.middle_thickness_mm == 68.0
    assert visual.plate_thickness_mm == 6.0
    assert visual.slot_allowance_mm == 1.0


def test_reference_calculation_remains_numerically_unchanged() -> None:
    result = calculate_stabduebel(StabduebelInput())
    assert result.side_timber["a_net_cm2"] == pytest.approx(113.28)
    assert result.middle_timber["a_net_cm2"] == pytest.approx(126.72)
    assert result.governing_check.name == "Verbindungsmittel im Holz"
    assert result.governing_check.utilization == pytest.approx(0.925632, rel=1e-6)
