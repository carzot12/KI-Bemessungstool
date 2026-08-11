from __future__ import annotations

import os
from unittest.mock import patch

from ai.assistant import StabduebelAssistant


def respond(assistant: StabduebelAssistant, prompt: str):
    assistant.state.parameters.setdefault("service_class", 1)
    assistant.state.parameters.setdefault("load_duration_class", "mittel")
    assistant.state.fixed_parameters.update({"service_class", "load_duration_class"})
    assistant.state.parameters.update(width_b_mm=200.0, height_h_mm=240.0)
    assistant.state.parameters.setdefault("number_of_plates_ns", 2)
    assistant.state.parameters.setdefault("plate_thickness_ts_mm", 6.0)
    assistant._set_connection_state(int(assistant.state.parameters["number_of_plates_ns"]))
    assistant.state.minimize_fasteners = True
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(prompt)


def test_complete_natural_dialog_preserves_state_and_avoids_recalculation() -> None:
    assistant = StabduebelAssistant()

    first = respond(assistant, "ich brauch einen anschluss für 140 kn")
    assert first.result is None
    assert "Holzfestigkeitsklasse" in first.text
    assert assistant.state.parameters["force_ed_kn"] == 140.0

    second = respond(assistant, "gl24 und 20x24 cm")
    assert second.result is not None
    assert second.result.input.timber_grade == "GL24h"
    assert second.result.input.width_b_mm == 200.0
    assert second.result.input.height_h_mm == 240.0

    third = respond(assistant, "nur ein stahlblech")
    assert third.result is not None
    assert third.result.input.number_of_plates_ns == 1
    assert third.result.input.force_ed_kn == 140.0
    assert third.result.input.timber_grade == "GL24h"

    fourth = respond(assistant, "so wenig dübel wie möglich")
    assert assistant.state.minimize_fasteners
    assert fourth.result is not None
    optimization_after_calculation = assistant.state.last_optimization

    explanation = respond(assistant, "warum ist der nachweis maßgebend?")
    assert "höchste Ausnutzung" in explanation.text
    assert assistant.state.last_optimization is optimization_after_calculation

    state_reply = respond(assistant, "was hab ich gerade alles eingestellt?")
    assert "140" in state_reply.text
    assert "GL24h" in state_reply.text
    assert "200 × 240 mm" in state_reply.text
    assert "Stahlbleche: 1" in state_reply.text
    assert "minimale Stabdübelanzahl" in state_reply.text
    assert assistant.state.last_optimization is optimization_after_calculation

    clarification = respond(assistant, "mach das blech dicker")
    assert "Welche Blechdicke" in clarification.text
    assert "6 mm" in clarification.text
    assert assistant.state.pending_clarification == "plate_thickness_ts_mm"
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.last_optimization is optimization_after_calculation


def test_bare_answer_completes_pending_plate_thickness_clarification() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h")
    respond(assistant, "mach das Blech dicker")

    reply = respond(assistant, "8 mm")

    assert reply.result is not None
    assert assistant.state.parameters["plate_thickness_ts_mm"] == 8.0
    assert assistant.state.pending_clarification is None


def test_general_neff_question_does_not_recalculate() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h")
    previous_optimization = assistant.state.last_optimization

    reply = respond(assistant, "Was bedeutet n_eff?")

    assert "wirksame Anzahl" in reply.text
    assert assistant.state.last_optimization is previous_optimization


def test_colloquial_diameter_changes_are_understood() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h")

    reply = respond(assistant, "nimm lieber 16er")

    assert assistant.state.parameters["dowel_diameter_d_mm"] == 16.0
    assert reply.result is not None
    assert reply.result.input.dowel_diameter_d_mm == 16.0


def test_cross_section_without_unit_is_clarified_not_parsed_as_arrangement() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h")
    previous_result = assistant.state.last_result

    reply = respond(assistant, "mach den Querschnitt 20x24")

    assert "Welche Abmessungen" in reply.text
    assert assistant.state.last_result is previous_result
    assert "rows_parallel_n" not in assistant.state.fixed_parameters
    assert "rows_perpendicular_m" not in assistant.state.fixed_parameters


def test_recommendation_question_uses_existing_result_without_recalculation() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h")
    previous_optimization = assistant.state.last_optimization

    reply = respond(assistant, "was würdest du ändern?")

    assert reply.result is assistant.state.last_result
    assert assistant.state.last_optimization is previous_optimization
