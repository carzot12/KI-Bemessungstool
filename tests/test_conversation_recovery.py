from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant


def say(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


def test_exact_incremental_regression_dialog_calculates_real_variants() -> None:
    assistant = StabduebelAssistant()
    messages = (
        "Bemesse einen Stabdübelanschluss für 140 kN mit GL24h und möglichst wenigen Stabdübeln",
        "200 x 240",
        "merhschnittig 2 blech",
        "6mm stahlblech",
        "ntuzungsklasse 1",
        "lasteinwirkungsdaur mittel",
        "t1 60",
        "ja",
        "ts,L 1",
    )
    replies = [say(assistant, message) for message in messages]

    parameters = assistant.state.parameters
    assert parameters["force_ed_kn"] == 140.0
    assert parameters["timber_grade"] == "GL24h"
    assert parameters["width_b_mm"] == 200.0
    assert parameters["height_h_mm"] == 240.0
    assert parameters["number_of_plates_ns"] == 2
    assert parameters["plate_thickness_ts_mm"] == 6.0
    assert parameters["service_class"] == 1
    assert parameters["load_duration_class"] == "mittel"
    assert replies[-1].result is not None
    assert assistant.state.last_optimization is not None
    assert assistant.state.last_optimization.evaluated_count > 0


@pytest.mark.parametrize(
    "message",
    ["200 x 240", "200x240", "200 × 240", "200/240", "b/h 200/240", "b x h = 200 x 240"],
)
def test_unitless_cross_section_spellings_are_not_fastener_arrangements(message: str) -> None:
    assistant = StabduebelAssistant()
    say(assistant, "140 kN GL24h möglichst wenige Stabdübel")
    say(assistant, message)

    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert "rows_parallel_n" not in assistant.state.fixed_parameters
    assert "rows_perpendicular_m" not in assistant.state.fixed_parameters


def test_missing_parameters_answer_lists_known_and_missing_values() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "140 kN GL24h 200 x 240 mm 2 Bleche je 6 mm möglichst wenige Stabdübel")
    reply = say(assistant, "was brauchst du?")

    assert "140 kN" in reply.text
    assert "GL24h" in reply.text
    assert "200 × 240 mm" in reply.text
    assert "Nutzungsklasse" in reply.text
    assert "Lasteinwirkungsdauer" in reply.text

    why = say(assistant, "warum?")
    assert "kmod" in why.text


def test_outdoor_service_class_requests_clarification_and_bare_answer_recovers() -> None:
    assistant = StabduebelAssistant()
    reply = say(assistant, "Nutzungsklasse draußen")
    assert "Nutzungsklasse 2 oder 3" in reply.text
    assert "service_class" not in assistant.state.parameters

    say(assistant, "2")
    assert assistant.state.parameters["service_class"] == 2


def test_failure_explanation_state_preservation_correction_and_undo() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "140 kN GL24h 200 x 240 mm 2 Bleche je 6 mm t1 60 t2 68 ts,L 1 NK1 mittel, möglichst wenige Stabdübel")
    successful = assistant.state.last_result
    assert successful is not None

    failed = say(assistant, "genau 999 Stabdübel")
    assert "keine Variante erzeugen" in failed.text
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.last_successful_result is successful
    why = say(assistant, "warum?")
    assert "999" in why.text

    corrected = say(assistant, "8 Stabdübel")
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.requested_fastener_count == 8
    assert corrected.text
    say(assistant, "zurück")
    assert assistant.state.requested_fastener_count == 999


def test_typo_and_contextual_diameter_correction() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "140 kN GL24h 200/240 mm 2 Bleche je 6 mm t1 60 t2 68 ts,L 1 nuzungsklasse eins mittel möglichst wenige stabdsübel")
    changed = say(assistant, "und mit 16er?")
    assert changed.result is not None
    assert changed.result.input.dowel_diameter_d_mm == 16.0
    say(assistant, "ich meinte 12")
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 12.0


def test_norm_question_simple_explanation_and_details_do_not_recalculate() -> None:
    assistant = StabduebelAssistant()
    say(assistant, "140 kN GL24h 200/240 mm 2 Bleche je 6 mm t1 60 t2 68 ts,L 1 NK1 mittel möglichst wenige Stabdübel")
    optimization = assistant.state.last_optimization

    norm = say(assistant, "geht das überhaupt nach ÖNORM?")
    simple = say(assistant, "erklär mir das einfacher")
    details = say(assistant, "zeig mir die details")

    assert "ÖNORM" in norm.text
    assert "Kurz gesagt" in simple.text
    assert "Technisches Ergebnis" in details.text
    assert assistant.state.last_optimization is optimization
