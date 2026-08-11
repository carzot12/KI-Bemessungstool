from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant
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
        "ein Stahlblech",
        "Holz-Stahl-Holz",
        "zweischnittig mit einem Stahlblech",
    ],
)
def test_assistant_recognizes_one_plate_connection_wordings(wording: str) -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, f"140 kN, GL24h, {wording}")

    assert reply.result is not None
    assert reply.result.input.number_of_plates_ns == 1
    assert reply.result.input.shear_planes_s == 2
    assert "Gleichung (8.11)" in reply.text
    assert "nicht zulässig" in reply.text


def test_chat_switches_between_connection_cases() -> None:
    assistant = StabduebelAssistant()
    one = respond(assistant, "140 kN, GL24h, ein Stahlblech")
    two = respond(assistant, "jetzt mit 2 Stahlblechen")

    assert one.result.input.shear_planes_s == 2
    assert two.result.input.number_of_plates_ns == 2
    assert two.result.input.shear_planes_s == 4
    assert "mehrschnittig, 2 innenliegende Stahlbleche" in two.text


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
