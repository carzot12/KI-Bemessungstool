from unittest.mock import patch

from ai.assistant import ParameterCategory, StabduebelAssistant
from ai.optimizer import (
    SUPPORTED_PLATE_THICKNESSES_MM,
    optimize_stabduebel,
)
from calculations.stabduebel import StabduebelInput


def test_autonomous_design_asks_only_for_real_clarifications() -> None:
    assistant = StabduebelAssistant()
    reply = assistant.respond(
        "Bemesse mir einen Stabdübelanschluss für 140 kN mit GL24h, "
        "200x240 und möglichst wenigen Stabdübeln."
    )

    assert assistant.state.autonomy_mode is True
    assert "t1" not in reply.text
    assert "t2" not in reply.text
    assert "Schlitz-/Luftwert" not in reply.text
    assert "Stabdübeldurchmesser" not in reply.text
    assert "Stabdübelanzahl" not in reply.text
    assert "Stahlblechdicke" not in reply.text
    assert "Anschlussaufbau" not in reply.text
    assert assistant.parameter_categories()["dowel_diameter_d_mm"] is ParameterCategory.OPTIMIZATION_VARIABLE


def test_fast_input_nk1_mittel_is_stored_as_user_fixed() -> None:
    assistant = StabduebelAssistant()
    assistant.respond("NK1 mittel")

    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert {"service_class", "load_duration_class"} <= assistant.state.fixed_parameters


def test_heated_interior_is_proposed_from_knowledge_and_confirmed() -> None:
    assistant = StabduebelAssistant()
    proposal = assistant.respond("Die Verbindung ist in einem beheizten Innenraum.")

    assert "Nutzungsklasse 1" in proposal.text
    assert "Soll ich" in proposal.text
    assert "service_class" not in assistant.state.parameters

    assistant.respond("ja")
    assert assistant.state.parameters["service_class"] == 1
    assert "service_class" in assistant.state.fixed_parameters


def test_autonomous_t1_t2_are_really_optimized() -> None:
    assistant = StabduebelAssistant()
    assistant.respond(
        "140 kN GL24h 200x240, 2 Bleche je 6mm, NK1 mittel, "
        "möglichst wenige Stabdübel"
    )
    reply = assistant.respond("t1 und t2 kannst du selber wählen")

    assert assistant.state.autonomy_mode is True
    assert reply.result is not None
    assert "Seitenholzdicke" not in reply.text
    assert "Mittelholzdicke" not in reply.text
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"


def test_user_fixed_t1_derives_t2_and_calculates() -> None:
    assistant = StabduebelAssistant()
    assistant.respond(
        "140 kN GL24h 200x240, 2 Bleche je 6mm, NK1 mittel, "
        "möglichst wenige Stabdübel"
    )
    result = assistant.respond("t1 60")
    assert result.result is not None
    assert result.result.input.side_thickness_t1_mm == 60.0
    assert result.result.input.middle_thickness_t2_mm == 68.0


def test_target_dialog_with_typos_optimizes_all_design_variables() -> None:
    assistant = StabduebelAssistant()
    first = assistant.respond(
        "140kn gl24 200x240, möglichst wenig stabdübl, rest mach selber"
    )
    assert "Nutzungsklasse" in first.text
    assert "Stahlblechdicke" not in first.text
    assert assistant.state.autonomy_mode is True

    final = assistant.respond("beheizter innenraun, mittel")
    assert "Nutzungsklasse 1" in final.text
    assert "Soll ich" not in final.text
    assert final.result is not None
    assert assistant.state.parameters["service_class"] == 1
    assert "service_class" not in assistant.state.fixed_parameters
    assert assistant.state.parameter_provenance["service_class"] == "KNOWLEDGE_DERIVED"
    assert assistant.state.last_optimization is not None
    varied = assistant.state.last_optimization.evaluated
    assert {item.input.number_of_plates_ns for item in varied} == {1, 2}
    assert {item.input.plate_thickness_ts_mm for item in varied} == set(
        SUPPORTED_PLATE_THICKNESSES_MM
    )
    assert len({(item.input.side_thickness_t1_mm,
                 item.input.middle_thickness_t2_mm) for item in varied}) > 2

    state_before = dict(assistant.state.parameters)
    why = assistant.respond("warum hast du zwei bleche genommen?")
    assert "beide" in why.text
    assert "zwei Scherflächen" in why.text
    assert assistant.state.parameters == state_before

    one_plate = assistant.respond("gehts auch mit einem?")
    assert one_plate.result is not None
    assert one_plate.result.input.number_of_plates_ns == 1
    assert "nicht zulässig" in one_plate.text.lower()


def test_technical_question_has_priority_and_preserves_full_state() -> None:
    assistant = StabduebelAssistant()
    assistant.respond(
        "140kn gl24 200x240, möglichst wenig stabdübl, rest mach selber"
    )
    calculated = assistant.respond("beheizter innenraun, mittel")
    assert calculated.result is not None
    state_before = dict(assistant.state.parameters)
    result_before = assistant.state.last_result

    answer = assistant.respond("Was bedeutet eigentlich Lasteinwirkungsdauer mittel?")
    assert "wie lange" in answer.text
    assert "kmod" in answer.text
    assert "Für die Bemessung brauche ich noch" not in answer.text
    assert assistant.state.parameters == state_before
    assert assistant.state.last_result is result_before


def test_optimizer_computes_minimum_spacings_and_validator_checks_geometry() -> None:
    optimization = optimize_stabduebel(
        StabduebelInput(),
        fixed_parameters={
            "force_ed_kn", "timber_grade", "width_b_mm", "height_h_mm",
            "number_of_plates_ns", "plate_thickness_ts_mm",
            "side_thickness_t1_mm", "middle_thickness_t2_mm",
        },
    )
    assert optimization.evaluated
    for variant in optimization.evaluated:
        d = variant.input.dowel_diameter_d_mm
        if d != 12.0:
            assert variant.input.a1_mm == 5.0 * d
            assert variant.input.a2_mm == 3.0 * d
            assert variant.input.a3_t_mm == max(7.0 * d, 80.0)
            assert variant.input.a4_c_mm == 3.0 * d


def test_user_fixed_geometry_and_plate_are_never_changed() -> None:
    base = StabduebelInput(
        number_of_plates_ns=2,
        plate_thickness_ts_mm=6.0,
        side_thickness_t1_mm=60.0,
        middle_thickness_t2_mm=68.0,
    )
    result = optimize_stabduebel(
        base,
        fixed_parameters={
            "number_of_plates_ns", "plate_thickness_ts_mm",
            "side_thickness_t1_mm", "middle_thickness_t2_mm",
        },
    )
    assert result.evaluated
    assert all(item.input.number_of_plates_ns == 2 for item in result.evaluated)
    assert all(item.input.plate_thickness_ts_mm == 6.0 for item in result.evaluated)
    assert all(item.input.side_thickness_t1_mm == 60.0 for item in result.evaluated)
    assert all(item.input.middle_thickness_t2_mm == 68.0 for item in result.evaluated)


def test_macos_keychain_enables_llm_without_environment_key() -> None:
    completed = type("Completed", (), {"stdout": "sk-test-only\n"})()
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), patch(
        "ai.assistant.os.sys.platform", "darwin"
    ), patch("ai.assistant.subprocess.run", return_value=completed):
        assistant = StabduebelAssistant()
    assert assistant.llm_available is True
    assert assistant.llm_key_source == "macos_keychain"
