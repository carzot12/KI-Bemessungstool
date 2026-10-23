from __future__ import annotations

from dataclasses import asdict

from ai.agent import OllamaAgent
from ai.assistant import StabduebelAssistant
from calculations.stabduebel import StabduebelInput, calculate_stabduebel


def offline_assistant() -> StabduebelAssistant:
    assistant = StabduebelAssistant()
    assistant._force_local = True
    return assistant


def test_unambiguous_smalltalk_is_natural_without_design() -> None:
    assistant = offline_assistant()

    greeting = assistant.respond("Guten Tag")
    wellbeing = assistant.respond("Wie geht es dir?")
    thanks = assistant.respond("Danke")
    capabilities = assistant.respond("Was kannst du?")
    identity = assistant.respond("Wer bist du?")

    assert "Guten Tag" in greeting.text
    assert "aktuellen Entwurf" not in greeting.text
    assert "Danke, gut" in wellbeing.text
    assert thanks.text == "Gerne!"
    assert "Stabdübel-Zuglaschenstöße" in capabilities.text
    assert "deterministischen Engineering-Kern" in capabilities.text
    assert "Engineering-Assistent" in identity.text
    assert assistant.state.parameters == {}
    assert assistant.conversation.last_intent == "SMALLTALK"
    assert assistant.conversation.last_action == "CHAT"


def test_smalltalk_with_existing_design_uses_design_context() -> None:
    assistant = offline_assistant()
    result = calculate_stabduebel(StabduebelInput())
    assistant.state.last_result = result
    assistant.state.parameters = asdict(result.input)

    reply = assistant.respond("Danke!")

    assert "aktuellen Entwurf" in reply.text
    assert "Variante vergleichen" in reply.text
    assert assistant.state.last_result is result


def test_ollama_keeps_tool_free_smalltalk_instead_of_requesting_parameters(monkeypatch) -> None:
    assistant = StabduebelAssistant()
    agent = OllamaAgent(assistant, "test-model", "http://unused")
    monkeypatch.setattr(
        agent,
        "_request",
        lambda messages: {"content": "Hallo! Schön, dass du da bist.", "tool_calls": []},
    )

    reply = agent.respond("Hallo")

    assert reply.text == "Hallo! Schön, dass du da bist."
    assert "Bitte ergänze" not in reply.text
    assert assistant.state.parameters == {}
    assert assistant.agent_events == []


def test_smalltalk_output_guard_limits_scope_and_formality() -> None:
    assistant = StabduebelAssistant()

    assert assistant._guard_smalltalk_reply("Danke", "Sie sind willkommen!") == "Gerne!"
    capability = assistant._guard_smalltalk_reply(
        "Was kannst du?",
        "Ich helfe allgemein bei allen Holzkonstruktionen.",
    )
    assert "Stabdübel-Zuglaschenstöße" in capability
    assert "deterministischen Engineering-Kern" in capability


def test_mixed_greeting_and_thanks_keep_engineering_priority() -> None:
    assistant = offline_assistant()

    first = assistant.respond("Hallo, bemesse mir GL24h für 140 kN.")
    assert assistant.state.parameters["force_ed_kn"] == 140.0
    assert assistant.state.parameters["timber_grade"] == "GL24h"
    assert assistant.conversation.last_intent != "SMALLTALK"
    assert first.text

    second = assistant.respond("Danke, mach das jetzt mit Ø12.")
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 12.0
    assert assistant.conversation.last_intent != "SMALLTALK"
    assert second.text


def test_technical_followups_remain_deterministic() -> None:
    assistant = offline_assistant()
    result = calculate_stabduebel(StabduebelInput())
    assistant.state.last_result = result
    assistant.state.last_successful_result = result
    assistant.state.parameters = asdict(result.input)

    maximum = assistant.respond("Wie viel hält die Verbindung maximal?")
    explanation = assistant.respond("Warum ist dieser Nachweis maßgebend?")

    assert assistant.state.last_maximum_load is not None
    assert "maximale Bemessungslast" in maximum.text
    assert result.governing_check.name in explanation.text
    assert assistant.conversation.last_action == "EXPLAIN_RESULT"
