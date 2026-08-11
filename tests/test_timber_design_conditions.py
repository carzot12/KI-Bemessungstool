from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant
from calculations.stabduebel import StabduebelInput, calculate_stabduebel
from infopol.materials import (
    GAMMA_M_SOURCE,
    KMOD_SOURCE,
    LOAD_DURATION_CLASSES,
    TimberMaterialRepository,
    get_connection_gamma_m,
    get_kmod,
)


def respond(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


EXPECTED_KMOD = {
    1: (0.60, 0.70, 0.80, 0.90, 1.10),
    2: (0.60, 0.70, 0.80, 0.90, 1.10),
    3: (0.50, 0.55, 0.65, 0.70, 0.90),
}


@pytest.mark.parametrize("grade", ["C24", "GL24h"])
@pytest.mark.parametrize("service_class", [1, 2, 3])
def test_kmod_table_for_every_supported_duration(
    grade: str,
    service_class: int,
) -> None:
    material = TimberMaterialRepository().get(grade)
    values = tuple(
        get_kmod(material, service_class, duration)
        for duration in LOAD_DURATION_CLASSES
    )
    assert values == EXPECTED_KMOD[service_class]


def test_new_design_asks_for_both_missing_normative_conditions() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, "Bemesse einen Stabdübelanschluss für 140 kN mit GL24h.")

    assert reply.result is None
    assert "Nutzungsklasse" in reply.text
    assert "Klasse der Lasteinwirkungsdauer" in reply.text
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"


def test_missing_duration_and_missing_service_class_are_asked_separately() -> None:
    only_service = StabduebelAssistant()
    reply_duration = respond(only_service, "140 kN GL24h NK1")
    assert reply_duration.result is None
    assert "Klasse der Lasteinwirkungsdauer" in reply_duration.text

    only_duration = StabduebelAssistant()
    reply_service = respond(only_duration, "140 kN GL24h mittel")
    assert reply_service.result is None
    assert "Nutzungsklasse" in reply_service.text


def test_nk1_and_mittel_complete_pending_design_and_set_kmod() -> None:
    assistant = StabduebelAssistant()
    respond(
        assistant,
        "140 kN GL24h, Querschnitt 200x240 mm, 2 Stahlbleche, "
        "6 mm Blechdicke, möglichst wenige Stabdübel",
    )
    reply = respond(assistant, "NK1 und mittel")

    assert reply.result is not None
    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert reply.result.input.k_mod == pytest.approx(0.8)
    assert KMOD_SOURCE in reply.text


def test_service_class_and_duration_followups_recalculate_and_keep_state() -> None:
    assistant = StabduebelAssistant()
    first = respond(
        assistant,
        "140 kN GL24h NK1 mittel, Querschnitt 200x240 mm, "
        "2 Stahlbleche, 6 mm Blechdicke, möglichst wenige Stabdübel",
    )
    second = respond(assistant, "ändere auf NK2")
    third = respond(assistant, "was wäre bei kurzer Lasteinwirkungsdauer?")

    assert first.result is not None
    assert second.result is not None
    assert second.result.input.service_class == 2
    assert second.result.input.k_mod == pytest.approx(0.8)
    assert third.result is not None
    assert third.result.input.service_class == 2
    assert third.result.input.load_duration_class == "kurz"
    assert third.result.input.k_mod == pytest.approx(0.9)
    assert third.result.input.force_ed_kn == 140.0
    assert third.result.input.timber_grade == "GL24h"
    assert "What-if-Vergleich" in third.text


def test_kmod_question_is_answered_from_current_result_without_recalculation() -> None:
    assistant = StabduebelAssistant()
    respond(
        assistant,
        "140 kN GL24h NK3 ständig, Querschnitt 200x240 mm, "
        "2 Stahlbleche, 6 mm Blechdicke, möglichst wenige Stabdübel",
    )
    previous = assistant.state.last_optimization
    reply = respond(assistant, "Warum ist kmod jetzt 0,5?")

    assert "kmod = 0.5" in reply.text
    assert "Nutzungsklasse 3" in reply.text
    assert "ständig" in reply.text
    assert KMOD_SOURCE in reply.text
    assert assistant.state.last_optimization is previous


def test_nk1_nk2_comparison_uses_calculated_results() -> None:
    assistant = StabduebelAssistant()
    respond(
        assistant,
        "140 kN GL24h NK1 mittel, Querschnitt 200x240 mm, "
        "2 Stahlbleche, 6 mm Blechdicke, möglichst wenige Stabdübel",
    )
    reply = respond(assistant, "Vergleiche NK1 und NK2")

    assert "tatsächlich mit dem Python-Rechenkern berechneten" in reply.text
    assert "- NK1: kmod = 0.8" in reply.text
    assert "- NK2: kmod = 0.8" in reply.text


@pytest.mark.parametrize(
    ("wording", "expected"),
    [
        ("Nutzungsklasse 1", 1),
        ("NK 2", 2),
        ("Service Class 3", 3),
        ("ändere auf NK2", 2),
    ],
)
def test_service_class_wordings(wording: str, expected: int) -> None:
    assistant = StabduebelAssistant()
    extracted, _ = assistant._extract(wording)
    assert extracted["service_class"] == expected


def test_reference_case_remains_reproducible_and_gamma_m_is_documented() -> None:
    reference = calculate_stabduebel(StabduebelInput())
    explicit = calculate_stabduebel(
        StabduebelInput(
            service_class=1,
            load_duration_class="mittel",
            k_mod=0.8,
            gamma_m_timber=get_connection_gamma_m(),
        )
    )

    assert get_connection_gamma_m() == pytest.approx(1.3)
    assert "Tabelle 2.3" in GAMMA_M_SOURCE
    assert explicit.governing_check.name == reference.governing_check.name
    assert explicit.governing_check.utilization == pytest.approx(
        reference.governing_check.utilization
    )
