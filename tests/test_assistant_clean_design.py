from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import (
    MULTI_SHEAR_TWO_INTERNAL_PLATES,
    TWO_SHEAR_ONE_INTERNAL_PLATE,
    StabduebelAssistant,
)


def respond(assistant: StabduebelAssistant, text: str):
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        return assistant.respond(text)


COMPLETE_OPTIMIZATION = (
    "140 kN, GL24h, Querschnitt 200x240 mm, 2 innenliegende Bleche, "
    "6 mm Blechdicke, NK1, mittlere Lasteinwirkungsdauer, "
    "t1 60 mm, t2 68 mm, ts,L 1 mm, "
    "möglichst wenige Stabdübel"
)


def test_empty_new_design_has_no_hidden_construction_defaults() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, "Neue Bemessung")

    assert reply.result is None
    assert assistant.state.parameters == {}
    assert assistant.state.connection_type is None
    assert assistant.state.shear_planes_s == 0
    for required in (
        "Bemessungslast",
        "Holzfestigkeitsklasse",
        "Holzquerschnitt",
        "Anschlussaufbau",
        "Stahlblechdicke",
        "Nutzungsklasse",
        "Lasteinwirkungsdauer",
    ):
        assert required in reply.text


def test_explicit_new_design_discards_previous_construction() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE_OPTIMIZATION)
    reply = respond(assistant, "Neue Bemessung")

    assert reply.result is None
    assert assistant.state.parameters == {}
    assert assistant.state.connection_type is None
    assert assistant.state.shear_planes_s == 0


def test_required_dialog_keeps_one_internal_plate_atomically() -> None:
    assistant = StabduebelAssistant()

    first = respond(assistant, "ein innenliegendes Stahlblech GL24h")
    assert first.result is None
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.connection_type == TWO_SHEAR_ONE_INTERNAL_PLATE
    assert assistant.state.shear_planes_s == 2

    respond(assistant, "140 kN")
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.shear_planes_s == 2

    respond(assistant, "Querschnitt 200 x 200")
    assert assistant.state.parameters["width_b_mm"] == 200.0
    assert assistant.state.parameters["height_h_mm"] == 200.0

    fourth = respond(assistant, "NK1 und mittlere Lasteinwirkungsdauer")
    assert assistant.state.parameters["service_class"] == 1
    assert assistant.state.parameters["load_duration_class"] == "mittel"
    assert assistant.state.parameters["number_of_plates_ns"] == 1
    assert assistant.state.shear_planes_s == 2
    assert "Stahlblechdicke" in fourth.text
    assert "Stabdübeldurchmesser" in fourth.text

    respond(assistant, "6 mm Blechdicke")
    respond(assistant, "Seitenholz 97 mm, ts,L 1 mm")
    result = respond(assistant, "möglichst wenige Stabdübel")
    assert result.result is not None
    assert result.result.input.number_of_plates_ns == 1
    assert result.result.input.shear_planes_s == 2
    assert result.result.input.k_mod == pytest.approx(0.8)
    assert "nicht zulässig" in result.text


def test_all_required_values_in_one_sentence_start_optimization() -> None:
    assistant = StabduebelAssistant()
    reply = respond(assistant, COMPLETE_OPTIMIZATION)

    assert reply.result is not None
    assert reply.result.input.number_of_plates_ns == 2
    assert assistant.state.connection_type == MULTI_SHEAR_TWO_INTERNAL_PLATES
    assert reply.result.input.width_b_mm == 200.0
    assert reply.result.input.height_h_mm == 240.0
    assert reply.result.input.plate_thickness_ts_mm == 6.0
    assert reply.result.input.k_mod == pytest.approx(0.8)


def test_information_may_arrive_in_different_order_and_two_plates_persist() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, "NK2 und kurz")
    respond(assistant, "2 innenliegende Bleche, 8 mm Blechdicke")
    respond(assistant, "Querschnitt 200x240")
    reply = respond(
        assistant,
        "GL24h, 140 kN, t1 60 mm, t2 64 mm, ts,L 1 mm, möglichst wenige Stabdübel",
    )

    assert reply.result is not None
    assert assistant.state.parameters["number_of_plates_ns"] == 2
    assert assistant.state.shear_planes_s == 4
    assert reply.result.input.service_class == 2
    assert reply.result.input.load_duration_class == "kurz"
    assert reply.result.input.k_mod == pytest.approx(0.9)


def test_utilization_objectives_are_selected_from_calculated_variants() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE_OPTIMIZATION)

    highest = respond(
        assistant, "Welche Variante hat die höchste zulässige Ausnutzung?"
    )
    assert highest.result is not None
    assert highest.result.governing_check.utilization <= 1.0
    feasible = [
        item.result.governing_check.utilization
        for item in assistant.state.last_optimization.evaluated
        if item.validation.admissible and item.result.passed
    ]
    assert highest.result.governing_check.utilization == pytest.approx(max(feasible))

    under_80 = respond(assistant, "Finde Varianten unter 80 %.")
    assert under_80.result is not None
    assert under_80.result.governing_check.utilization <= 0.8

    between = respond(assistant, "Welche Lösung liegt zwischen 70 und 80 %?")
    assert between.result is not None
    assert 0.7 <= between.result.governing_check.utilization <= 0.8


@pytest.mark.parametrize(
    ("wording", "limit"),
    [("Ziel η <= 1.00", 1.0), ("Ziel eta <= 0.80", 0.8)],
)
def test_eta_limit_notation_is_deterministically_enforced(
    wording: str,
    limit: float,
) -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE_OPTIMIZATION)
    reply = respond(assistant, wording)

    assert reply.result is not None
    assert assistant.state.max_utilization == pytest.approx(limit)
    assert reply.result.governing_check.utilization <= limit


def test_top_five_variants_are_real_and_sorted_by_active_objective() -> None:
    assistant = StabduebelAssistant()
    respond(assistant, COMPLETE_OPTIMIZATION)
    reply = respond(
        assistant,
        "Zeig mir die 5 besten Varianten mit der höchsten zulässigen Ausnutzung.",
    )

    assert "Beste tatsächlich berechnete Varianten" in reply.text
    assert all(f"{index}." in reply.text for index in range(1, 6))
    utilizations = [
        item.result.governing_check.utilization
        for item in assistant.state.last_optimization.evaluated
        if item.validation.admissible and item.result.passed
    ]
    assert reply.result.governing_check.utilization == pytest.approx(max(utilizations))


def test_fixed_variant_maximum_load_and_multi_diameter_comparison() -> None:
    assistant = StabduebelAssistant()
    fixed = respond(
        assistant,
            "140 kN, GL24h, Querschnitt 200x240 mm, 2 Stahlbleche, "
            "6 mm Blechdicke, t1 60, t2 68, ts,L 1, NK1, mittel, 2x4 Stabdübel, Ø12",
    )
    assert fixed.result is not None

    maximum = respond(assistant, "Wie viel kN trägt diese Variante maximal?")
    assert "per Bisektion" in maximum.text
    assert "2 × 4 = 8" in maximum.text
    assert "Ø12 mm" in maximum.text

    comparison = respond(assistant, "Was ist mit Ø12, Ø16 und Ø20?")
    assert "Ø12 mm" in comparison.text
    assert "Ø16 mm" in comparison.text
    assert "Ø20 mm" in comparison.text


def test_two_explicit_arrangements_are_compared_exactly() -> None:
    assistant = StabduebelAssistant()
    respond(
        assistant,
            "140 kN, GL24h, Querschnitt 200x240 mm, 2 Stahlbleche, "
            "6 mm Blechdicke, t1 60, t2 68, ts,L 1, NK1, mittel, möglichst wenige Stabdübel",
    )
    comparison = respond(assistant, "Vergleiche 2x4 Ø12 mit 2x3 Ø16.")

    assert "2 × 4 = 8" in comparison.text
    assert "Ø12 mm" in comparison.text
    assert "2 × 3 = 6" in comparison.text
    assert "Ø16 mm" in comparison.text
