from unittest.mock import patch

from ai.agent import EngineeringTools
from ai.assistant import StabduebelAssistant


def offline_assistant() -> StabduebelAssistant:
    with patch.object(
        StabduebelAssistant, "_resolve_api_key", return_value=(None, "test")
    ):
        return StabduebelAssistant()


def required_state(assistant: StabduebelAssistant) -> None:
    assistant.state.parameters.update({
        "force_ed_kn": 140.0,
        "timber_grade": "GL24h",
        "width_b_mm": 200.0,
        "height_h_mm": 240.0,
        "service_class": 1,
        "load_duration_class": "mittel",
    })
    assistant.state.fixed_parameters.update(assistant.state.parameters)
    assistant.state.parameter_provenance.update(
        {key: "USER_FIXED" for key in assistant.state.parameters}
    )


def test_a_explicit_nkl_is_stored_without_repeated_question() -> None:
    assistant = offline_assistant()
    reply = assistant.respond(
        "140 kN GL24h 200 × 240 mm, NKL 1, Lasteinwirkungsdauer mittel. "
        "Finde eine wirtschaftliche Lösung."
    )

    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert "service_class" in assistant.state.fixed_parameters
    assert reply.result is not None
    assert "Welche Nutzungsklasse" not in reply.text


def test_b_genau_confirms_pending_service_class() -> None:
    assistant = offline_assistant()
    assistant.respond("Die Verbindung liegt in einem beheizten Innenraum.")

    assistant.respond("genau")

    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameter_provenance["service_class"] == "USER_FIXED"
    assert assistant.state.pending_clarification is None
    assert assistant.state.pending_state_proposal is None


def test_c_autonomy_followup_does_not_forget_confirmed_service_class() -> None:
    assistant = offline_assistant()
    assistant.respond("Die Verbindung liegt in einem beheizten Innenraum.")
    assistant.respond("genau")

    reply = assistant.respond("du entscheidest")

    assert assistant.state.parameters["service_class"] == 1
    assert "Nutzungsklasse" not in reply.text


def test_d_complete_required_input_starts_optimization_immediately() -> None:
    assistant = offline_assistant()

    reply = assistant.respond(
        "Bemesse 140 kN mit GL24h und 200 x 240 mm, NKL 1, mittel. "
        "Finde eine wirtschaftliche Lösung."
    )

    assert reply.result is not None
    assert assistant.state.last_optimization is not None
    assert assistant.state.last_optimization.evaluated_count > 0
    assert assistant.state.autonomy_mode is True


def test_e_only_one_plate_is_user_fixed() -> None:
    assistant = offline_assistant()

    assistant.respond("nur ein Blech")

    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert "number_of_plates_ns" in assistant.state.fixed_parameters
    assert assistant.state.parameter_provenance["number_of_plates_ns"] == "USER_FIXED"


def test_f_later_two_plate_instruction_replaces_fixed_value() -> None:
    assistant = offline_assistant()
    assistant.respond("nur ein Blech")

    assistant.respond("nimm doch zwei Bleche")

    assert assistant.state.parameters["number_of_plates_ns"] == 2
    assert "number_of_plates_ns" in assistant.state.fixed_parameters
    assert assistant.state.shear_planes_s == 4


def test_g_du_entscheidest_releases_pending_plate_count() -> None:
    assistant = offline_assistant()
    required_state(assistant)
    assistant.state.parameters["number_of_plates_ns"] = 1
    assistant.state.fixed_parameters.add("number_of_plates_ns")
    assistant.state.parameter_provenance["number_of_plates_ns"] = "USER_FIXED"
    assistant.state.pending_clarification = "number_of_plates_ns"

    reply = assistant.respond("du entscheidest")

    assert reply.result is not None
    assert "number_of_plates_ns" not in assistant.state.fixed_parameters
    assert assistant.state.last_optimization is not None
    assert {item.input.number_of_plates_ns for item in assistant.state.last_optimization.evaluated} == {1, 2}


def test_h_incremental_followups_preserve_all_required_parameters() -> None:
    assistant = offline_assistant()
    assistant.respond("140 kN")
    assistant.respond("GL24h")
    assistant.respond("200 × 240 mm")
    assistant.respond("NKL 1")
    assistant.respond("mittel")

    reply = assistant.respond("finde eine wirtschaftliche Lösung")

    assert reply.result is not None
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 240.0
    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"


def test_online_tool_filter_accepts_explicit_nkl_spelling() -> None:
    assistant = offline_assistant()
    assistant.message_history.append({
        "role": "user",
        "content": "140 kN GL24h 200 × 240 mm, NKL 1 und mittel",
    })

    EngineeringTools(assistant).update_design(
        {
            "force_ed_kn": 140,
            "timber_grade": "GL24h",
            "width_b_mm": 200,
            "height_h_mm": 240,
            "service_class": 1,
            "load_duration_class": "mittel",
        },
        "USER_FIXED",
        None,
        True,
    )

    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert {"service_class", "load_duration_class"} <= assistant.state.fixed_parameters
