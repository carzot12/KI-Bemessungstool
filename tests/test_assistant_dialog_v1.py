from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant


def respond(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


def test_parameter_changes_preserve_the_rest_of_the_design() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h, Querschnitt 200 × 240 mm, 2 Stahlbleche")
    respond(assistant, "mach 160 kN")
    respond(assistant, "jetzt GL28h")
    respond(assistant, "Blech 8 mm")

    assert assistant.state.parameters["force_ed_kn"] == 160.0
    assert assistant.state.parameters["timber_grade"] == "GL28h"
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.parameters["number_of_plates_ns"] == 2
    assert assistant.state.parameters["plate_thickness_ts_mm"] == 8.0


def test_arrangement_count_and_distances_are_fixed_user_parameters() -> None:
    assistant = StabduebelAssistant()
    reply = respond(
        assistant,
        "140 kN GL24h, mach 2x4 Stabdübel, a1 = 60 mm, e1 = 22 mm",
    )

    assert reply.result is not None
    assert reply.result.input.rows_parallel_n == 2
    assert reply.result.input.rows_perpendicular_m == 4
    assert reply.result.input.a1_mm == 60.0
    assert reply.result.input.e1_mm == 22.0
    assert {"rows_parallel_n", "rows_perpendicular_m", "a1_mm", "e1_mm"} <= assistant.state.fixed_parameters


def test_what_if_recalculates_and_compare_uses_both_real_results() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h 4x4 Stabdübel, nimm 12er")
    what_if = respond(assistant, "was wäre mit 16er?")
    comparison = respond(assistant, "vergleich die beiden")

    assert what_if.result is not None
    assert what_if.result.input.dowel_diameter_d_mm == 16.0
    assert "What-if-Vergleich" in what_if.text
    assert "Ø12 mm" in comparison.text
    assert "Ø16 mm" in comparison.text
    assert "tatsächlich berechneten" in comparison.text


def test_maximum_load_is_found_deterministically_for_valid_configuration() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h 4x4 Stabdübel, nimm 12er")
    reply = respond(assistant, "wie viel trägt das maximal?")

    assert "per Bisektion" in reply.text
    assert "maximale Bemessungslast" in reply.text
    assert "maßgebend" in reply.text.lower()
    assert "Norm- und Geometrievalidierung" in reply.text


def test_target_utilization_runs_optimizer_and_locks_cross_section() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h Querschnitt 200x240 mm")
    reply = respond(
        assistant,
        "bring die Ausnutzung unter 80 %, aber lass den Querschnitt gleich",
    )

    assert assistant.state.max_utilization == pytest.approx(0.8)
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.last_optimization is not None
    if assistant.state.last_optimization.selected is not None:
        assert reply.result.governing_check.utilization <= 0.8


def test_clarification_does_not_mutate_state() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h Querschnitt 200x240 mm")
    before = dict(assistant.state.parameters)
    previous_result = assistant.state.last_result
    reply = respond(assistant, "mach den Querschnitt bissl kleiner")

    assert "Welche Abmessungen" in reply.text
    assert assistant.state.parameters == before
    assert assistant.state.last_result is previous_result


def test_current_state_and_one_step_undo() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h 4x4 Stabdübel, nimm 12er")
    respond(assistant, "was wäre mit 16er?")
    state_reply = respond(assistant, "was habe ich gerade alles eingestellt?")
    undo_reply = respond(assistant, "mach die letzte Änderung rückgängig")

    assert "Ø16" in state_reply.text
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 12.0
    assert "zurückgenommen" in undo_reply.text


def test_typo_and_colloquial_language_are_recognized() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, gl24, querschnit 20x24 cm")
    reply = respond(assistant, "nimm 12er dübl")

    assert reply.result is not None
    assert reply.result.input.timber_grade == "GL24h"
    assert reply.result.input.width_b_mm == 200.0
    assert reply.result.input.height_h_mm == 240.0
    assert reply.result.input.dowel_diameter_d_mm == 12.0


def test_explanation_and_recommendation_do_not_recalculate() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN GL24h, möglichst wenige Dübel")
    previous_optimization = assistant.state.last_optimization
    explanation = respond(assistant, "welcher Nachweis ist kritisch?")
    recommendation = respond(assistant, "was würdest du ändern?")

    assert "maßgebend" in explanation.text
    assert assistant.state.last_optimization is previous_optimization
    assert recommendation.text
    assert assistant.state.last_optimization is previous_optimization


def test_complete_requested_dialog_remains_consistent() -> None:
    assistant = StabduebelAssistant()
    prompts = [
        "Ich brauche 140 kN mit GL24.",
        "Querschnitt 20x24 cm.",
        "such mir eine Lösung mit möglichst wenigen Dübeln.",
        "nimm jetzt 12er.",
        "und 10 Stück.",
        "wie viel trägt das maximal?",
        "was wäre mit 16er?",
        "vergleich die beiden.",
        "bring die Ausnutzung unter 80 %, aber lass den Querschnitt gleich.",
        "warum hast du diese Variante gewählt?",
        "was habe ich gerade alles eingestellt?",
        "mach die letzte Änderung rückgängig.",
    ]
    replies = [respond(assistant, prompt) for prompt in prompts]

    assert all(reply.text for reply in replies)
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.requested_fastener_count == 10
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 16.0
