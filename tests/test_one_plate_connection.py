from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import patch

import pytest

from ai.assistant import (
    MULTI_SHEAR_TWO_INTERNAL_PLATES,
    TWO_SHEAR_ONE_INTERNAL_PLATE,
    StabduebelAssistant,
)
from ai.optimizer import optimize_stabduebel
from calculations.oenorm_validation import validate_oenorm
from calculations.stabduebel import StabduebelInput, calculate_stabduebel


def respond(assistant: StabduebelAssistant, prompt: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(prompt)


def test_one_plate_uses_separate_double_shear_equation_811_model() -> None:
    data = replace(
        StabduebelInput(),
        number_of_plates_ns=1,
        side_thickness_t1_mm=97.0,
    )
    result = calculate_stabduebel(data)

    assert data.shear_planes_s == 2
    assert data.connection_case == (
        "Zuglaschenstoß – zweischnittig, 1 innenliegendes Stahlblech"
    )
    assert result.timber_fastener["connection_model"] == (
        "EN 1995-1-1 (8.11), zweischnittig"
    )
    assert result.timber_fastener["fv_rk_one_dowel_n"] == pytest.approx(
        2.0 * result.timber_fastener["fv_rk_per_shear_plane_n"]
    )
    assert result.middle_timber["applicable"] is False
    assert result.timber_block["applicable"] is False
    assert {check.name for check in result.checks} == {
        "Seitenholz – Nettoquerschnitt",
        "Stahlblech – Zug",
        "Verbindungsmittel im Stahlblech",
        "Blockversagen Stahlblech",
        "Verbindungsmittel im Holz",
    }


def test_one_plate_is_always_nationally_inadmissible() -> None:
    data = replace(
        StabduebelInput(),
        force_ed_kn=20.0,
        number_of_plates_ns=1,
        side_thickness_t1_mm=97.0,
    )
    result = calculate_stabduebel(data)
    validation = validate_oenorm(data, result)

    assert result.passed
    assert not validation.admissible
    assert "Mindestanzahl Scherflächen" in {
        check.name for check in validation.failures
    }


@pytest.mark.parametrize(
    "wording",
    [
        "1 innenliegendes Blech",
        "ein Stahlblech",
        "ein innenliegendes Blech",
        "Holz Stahl Holz",
        "Holz-Stahl-Holz",
        "zweischnittig",
        "zweischnittige Verbindung",
        "zweischnittig mit einem Stahlblech",
        "zweischnittig ein innenliegendes Blech",
        "jetzt nur ein Blech",
    ],
)
def test_assistant_recognizes_one_plate_connection_wordings(wording: str) -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, f"140 kN, GL24h, {wording}")

    assert reply.result is not None
    assert reply.result.input.number_of_plates_ns == 1
    assert reply.result.input.shear_planes_s == 2
    assert assistant.state.connection_type == TWO_SHEAR_ONE_INTERNAL_PLATE
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.shear_planes_s == 2
    assert "Gleichung (8.11)" in reply.text
    assert "nicht zulässig" in reply.text


def test_chat_switches_between_connection_cases() -> None:
    assistant = StabduebelAssistant()
    one = respond(assistant, "140 kN, GL24h, ein Stahlblech")
    two = respond(assistant, "jetzt mit 2 Stahlblechen")

    assert one.result.input.shear_planes_s == 2
    assert assistant.state.connection_type == MULTI_SHEAR_TWO_INTERNAL_PLATES
    assert two.result.input.number_of_plates_ns == 2
    assert two.result.input.shear_planes_s == 4
    assert "mehrschnittig, 2 innenliegende Stahlbleche" in two.text


def test_followup_keeps_one_plate_case_and_routes_only_one_plate_variants() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h, 2 Stahlbleche")
    respond(assistant, "jetzt 1 innenliegendes Blech")
    reply = respond(assistant, "so wenig Dübel wie möglich")

    assert reply.result is not None
    assert assistant.state.connection_type == TWO_SHEAR_ONE_INTERNAL_PLATE
    assert assistant.state.shear_planes_s == 2
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.last_optimization.evaluated
    assert all(
        item.input.number_of_plates_ns == 1
        and item.input.shear_planes_s == 2
        for item in assistant.state.last_optimization.evaluated
    )


def test_einschnittig_asks_without_changing_state() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "140 kN, GL24h, 2 Stahlbleche")
    before_parameters = dict(assistant.state.parameters)
    before_fixed = set(assistant.state.fixed_parameters)
    before_connection = assistant.state.connection_type
    before_shear_planes = assistant.state.shear_planes_s
    before_result = assistant.state.last_result
    before_optimization = assistant.state.last_optimization

    reply = respond(assistant, "einschnittig")

    assert "echte einschnittige Stahl-Holz-Verbindung" in reply.text
    assert "Holz | Stahl | Holz" in reply.text
    assert assistant.state.parameters == before_parameters
    assert assistant.state.fixed_parameters == before_fixed
    assert assistant.state.connection_type == before_connection
    assert assistant.state.shear_planes_s == before_shear_planes
    assert assistant.state.last_result is before_result
    assert assistant.state.last_optimization is before_optimization


def test_optimizer_compares_both_but_selects_only_nationally_admissible_case() -> None:
    optimization = optimize_stabduebel(
        StabduebelInput(),
        minimize_fasteners=True,
    )

    assert {item.input.number_of_plates_ns for item in optimization.evaluated} == {1, 2}
    assert optimization.selected is not None
    assert optimization.selected.input.number_of_plates_ns == 2
    assert all(
        not item.validation.admissible
        for item in optimization.evaluated
        if item.input.number_of_plates_ns == 1
    )
