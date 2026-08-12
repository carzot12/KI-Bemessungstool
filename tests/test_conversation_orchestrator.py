from __future__ import annotations

import os
from unittest.mock import patch

from ai.assistant import StabduebelAssistant


def respond(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


COMPLETE = (
    "140 kN GL24h, Querschnitt 200x240 mm, zwei innenliegende Bleche, "
    "Blech 6 mm, NK1, mittel, möglichst wenige Stabdübel"
)


def test_typo_dialog_collects_all_parameters_without_losing_state() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "brauch stabdsübel für 140 kn gl24")
    respond(assistant, "querschnit 20x24")
    respond(assistant, "ein blech 6mm")
    reply = respond(assistant, "nuzungsklasse 1 und mittel")

    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.parameters["plate_thickness_ts_mm"] == 6.0
    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert assistant.state.shear_planes_s == 2
    assert reply.result is None
    assert "Optimierungsziel" in reply.text


def test_short_followups_use_previous_result_and_topic() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE)
    change = respond(assistant, "mach ma 16er dübl draus")
    comparison = respond(assistant, "is des besser?")
    explanation = respond(assistant, "warum?")
    maximum = respond(assistant, "und maximal?")

    assert change.result is not None
    assert change.result.input.dowel_diameter_d_mm == 16.0
    assert "berechneten Varianten" in comparison.text
    assert "berechneten Ergebnissen" in explanation.text
    assert "maximale Bemessungslast" in maximum.text
    assert assistant.conversation.last_action == "MAXIMUM_LOAD"


def test_discussion_and_acknowledgement_do_not_recalculate() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE)
    previous_optimization = assistant.state.last_optimization

    discussion = respond(assistant, "das sind mir zu viele dübel")
    assert "geringere Stabdübelanzahl" in discussion.text
    assert assistant.state.last_optimization is previous_optimization

    acknowledgement = respond(assistant, "okay verstehe")
    assert "aktuellen Entwurf" in acknowledgement.text
    assert assistant.state.last_optimization is previous_optimization
    assert assistant.conversation.last_action == "CHAT"


def test_free_engineering_questions_do_not_calculate() -> None:
    assistant = StabduebelAssistant()
    question = respond(assistant, "Warum brauchst du eigentlich die Nutzungsklasse?")

    assert "Feuchtebedingungen" in question.text
    assert assistant.state.last_optimization is None
    assert assistant.state.last_result is None


def test_ranked_variant_can_be_selected_and_used_for_maximum_load() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE)
    ranking = respond(assistant, "zeig mir die 5 besten Varianten unter 90 Prozent")
    second = assistant.conversation.presented_variants[1]
    selected = respond(assistant, "nimm die zweite")
    maximum = respond(assistant, "und was schafft die maximal?")

    assert "Beste tatsächlich berechnete Varianten" in ranking.text
    assert selected.result is second.result
    assert assistant.state.parameters["rows_parallel_n"] == second.input.rows_parallel_n
    assert assistant.state.parameters["rows_perpendicular_m"] == second.input.rows_perpendicular_m
    assert assistant.state.parameters["dowel_diameter_d_mm"] == second.input.dowel_diameter_d_mm
    assert "maximale Bemessungslast" in maximum.text


def test_debug_mode_exposes_action_without_changing_user_text() -> None:
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "", "STABDUEBEL_DEBUG": "1"},
    ):
        assistant = StabduebelAssistant()
        reply = assistant.respond("140 kN GL24h")

    assert "Intent:" in reply.debug
    assert "Action:" in reply.debug
    assert "Technical State:" in reply.debug


def test_complete_colloquial_message_is_extracted_atomically() -> None:
    assistant = StabduebelAssistant()
    extracted = assistant._fallback_extract(
        "140 kN GL24h, Querschnit 20x24 cm, ein innenliegendes Blech, "
        "1 Blech mit 6 mm Dicke, Nutzungsklase 2, mittlere "
        "Lasteinwirkungsdaur"
    )

    assert extracted["force_ed_kn"] == 140.0
    assert extracted["timber_grade"] == "GL24h"
    assert extracted["width_b_mm"] == 200.0
    assert extracted["height_h_mm"] == 240.0
    assert extracted["number_of_plates_ns"] == 1
    assert extracted["plate_thickness_ts_mm"] == 6.0
    assert extracted["service_class"] == 2
    assert extracted["load_duration_class"] == "mittel"


def test_llm_action_cannot_trigger_calculation_for_a_general_question() -> None:
    assert (
        StabduebelAssistant._validated_action(
            {"action": "CALCULATE"}, "GENERAL_ENGINEERING_QUESTION"
        )
        == "GENERAL_TECHNICAL_QUESTION"
    )


def test_twenty_turn_dialog_keeps_technical_and_conversation_state_consistent() -> None:
    assistant = StabduebelAssistant()
    messages = [
        "brauch stabdübl für 140 kn gl24",
        "querschnit 20x24",
        "ein blech 6mm",
        "nuzungsklasse 1 und mittel",
        "möglichst wenige dübel",
        "warum is des nicht zulässig",
        "okay verstehe",
        "und wenn ich zwei bleche nehme?",
        "mach ma 16er dübl draus",
        "is des besser?",
        "warum?",
        "wieviel kn geht damit",
        "was habe ich eingestellt?",
        "zeig mir die 5 besten varianten unter 90 prozent",
        "nimm die zweite",
        "und was schafft die maximal?",
        "was bedeutet 80 prozent ausnutzung?",
        "probier größere",
        "welche würdest du nehmen?",
        "mach das rückgängig",
    ]
    replies = [respond(assistant, message) for message in messages]

    assert len(replies) == 20
    assert all(reply.text for reply in replies)
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.parameters["plate_thickness_ts_mm"] == 6.0
    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert assistant.state.parameters["number_of_plates_ns"] == 2
    assert assistant.state.shear_planes_s == 4
    assert assistant.conversation.last_intent == "UNDO_LAST_CHANGE"
    assert assistant.conversation.last_assistant_answer
