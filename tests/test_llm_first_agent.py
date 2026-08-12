from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from ai.agent import EngineeringTools, LLMAgent
from ai.assistant import StabduebelAssistant


def offline_assistant() -> StabduebelAssistant:
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        return StabduebelAssistant()


class FakeResponses:
    def __init__(self, responses):
        self.items = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.items)


def call_response(identifier: str, name: str, arguments: dict):
    call = SimpleNamespace(
        type="function_call", name=name, arguments=json.dumps(arguments),
        call_id=f"call-{identifier}",
    )
    return SimpleNamespace(id=identifier, output=[call], output_text="")


def final_response(identifier: str, text: str):
    return SimpleNamespace(id=identifier, output=[], output_text=text)


def test_conversation_history_and_multi_tool_loop() -> None:
    assistant = offline_assistant()
    fake = FakeResponses([
        call_response("r1", "update_design", {
            "parameters": {
                "force_kn": 140, "timber_grade": "GL24h",
                "width_mm": 200, "height_mm": 240,
                "plate_count": 2, "plate_thickness_mm": 6,
                "side_thickness_mm": 60, "middle_thickness_mm": 68,
                "slot_allowance_mm": 1, "service_class": 1,
                "load_duration_class": "mittel",
            },
            "provenance": "USER_FIXED", "source": None, "autonomy_mode": True,
        }),
        call_response("r2", "optimize_design", {
            "objective": "MIN_FASTENER_COUNT", "constraints": {},
        }),
        final_response("r3", "Ich habe den Entwurf mit dem Rechenkern optimiert."),
    ])
    agent = LLMAgent(assistant, SimpleNamespace(responses=fake), "test-model")

    reply = agent.respond("140 kN GL24h, den Rest entscheide du")

    assert reply.used_llm is True
    assert reply.result is not None
    assert len(fake.calls) == 3
    assert fake.calls[1]["previous_response_id"] == "r1"
    assert fake.calls[2]["previous_response_id"] == "r2"
    assert assistant.message_history == [
        {"role": "user", "content": "140 kN GL24h, den Rest entscheide du"},
        {"role": "assistant", "content": reply.text},
    ]
    assert assistant.state.autonomy_mode is True


def test_user_fixed_value_is_protected_from_ai_derived_update() -> None:
    assistant = offline_assistant()
    tools = EngineeringTools(assistant)
    tools.update_design({"dowel_diameter_mm": 16}, "USER_FIXED", None, None)
    tools.update_design(
        {"dowel_diameter_mm": 12}, "AI_DERIVED", "knowledge", None
    )
    assert assistant.state.parameters["dowel_diameter_d_mm"] == 16
    assert "dowel_diameter_d_mm" in assistant.state.fixed_parameters
    assert assistant.state.parameter_provenance["dowel_diameter_d_mm"] == "USER_FIXED"


def test_agent_context_contains_required_compact_sections() -> None:
    context = offline_assistant().agent_context()
    required = {
        "current_design", "current_result", "last_successful_result",
        "previous_design", "previous_result", "last_optimization",
        "optimization_goal", "autonomy_mode", "user_fixed_constraints",
        "ai_derived_constraints", "parameter_provenance", "missing_information",
        "pending_clarification", "connection_type", "shear_planes",
        "considered_variants", "knowledge_sources_used",
    }
    assert required <= context.keys()


def test_knowledge_tool_returns_verified_source_without_changing_state() -> None:
    assistant = offline_assistant()
    tools = EngineeringTools(assistant)
    before = assistant.copy_state()
    result = tools.search_knowledge_base("Was bedeutet Lasteinwirkungsdauer mittel?")
    assert result["found"] is True
    assert result["sources"]
    assert assistant.state == before


def test_restore_previous_design_undoes_tool_update() -> None:
    assistant = offline_assistant()
    tools = EngineeringTools(assistant)
    tools.update_design({"dowel_diameter_mm": 12}, "USER_FIXED", None, None)
    tools.update_design({"dowel_diameter_mm": 16}, "USER_FIXED", None, None)
    restored = tools.restore_previous_design()
    assert restored["restored"]["dowel_diameter_d_mm"] == 12


def test_no_key_selects_explicit_local_mode() -> None:
    assistant = offline_assistant()
    assert assistant.llm_status == "LOCAL"
    assert assistant.llm_online is False
    reply = assistant.respond("Was fehlt noch?")
    assert reply.used_llm is False


def test_invalid_model_does_not_silently_fallback() -> None:
    assistant = offline_assistant()
    assistant._api_key = "test-key"
    failing_client = SimpleNamespace(
        models=SimpleNamespace(retrieve=lambda _model: (_ for _ in ()).throw(RuntimeError("model not found")))
    )
    with patch("openai.OpenAI", return_value=failing_client):
        reply = assistant.respond("Hallo")
    assert assistant.llm_status == "ERROR"
    assert "LLM-Aufruf fehlgeschlagen" in reply.text
    assert "model not found" in reply.text
    assert assistant.state.parameters == {}


def test_context_reference_is_left_to_llm_not_local_parser() -> None:
    assistant = offline_assistant()
    assistant.message_history.extend([
        {"role": "assistant", "content": "Soll ich Ø12 oder Ø16 untersuchen?"},
    ])
    fake = FakeResponses([final_response("r1", "Ich untersuche Ø16.")])
    agent = LLMAgent(assistant, SimpleNamespace(responses=fake), "test-model")
    agent.respond("16")
    sent = fake.calls[0]["input"]
    assert sent[0]["content"] == "Soll ich Ø12 oder Ø16 untersuchen?"
    assert "USER_MESSAGE:\n16" in sent[-1]["content"]
