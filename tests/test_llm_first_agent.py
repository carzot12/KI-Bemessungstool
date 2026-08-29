from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from ai.agent import EngineeringTools, LLMAgent
from ai.assistant import StabduebelAssistant


def offline_assistant() -> StabduebelAssistant:
    with patch.object(
        StabduebelAssistant, "_resolve_api_key",
        return_value=(None, "local_fallback"),
    ):
        assistant = StabduebelAssistant()
        # Preserve the historical no-key/OpenAI fallback semantics in this
        # test helper; dedicated provider tests cover the new local default.
        assistant.llm_provider = "openai"
        return assistant


class FakeResponses:
    def __init__(self, responses):
        self.items = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.items)


class FakeOnlineClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)
        self.models = SimpleNamespace(retrieve=lambda model: {"id": model})


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

    reply = agent.respond(
        "140 kN GL24h 200x240, NK1 mittel, 2 Bleche 6 mm, "
        "t1 60, t2 68, Schlitzwert 1 mm, den Rest entscheide du"
    )

    assert reply.used_llm is True
    assert reply.result is not None
    assert len(fake.calls) == 3
    assert fake.calls[1]["previous_response_id"] == "r1"
    assert fake.calls[2]["previous_response_id"] == "r2"
    assert assistant.message_history == [
        {"role": "user", "content": (
            "140 kN GL24h 200x240, NK1 mittel, 2 Bleche 6 mm, "
            "t1 60, t2 68, Schlitzwert 1 mm, den Rest entscheide du"
        )},
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
    assert "OpenAI API derzeit nicht verfügbar" in reply.text
    assert "auf die lokale KI wechseln" in reply.text
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


def test_small_talk_allows_zero_tools_and_preserves_design() -> None:
    assistant = offline_assistant()
    assistant.state.parameters["force_ed_kn"] = 140.0
    before = assistant.copy_state()
    fake = FakeResponses([
        final_response("r1", "Hallo! Schön, dass du da bist."),
        final_response("r2", "Gern – wir können weiterreden oder einen Anschluss untersuchen."),
        final_response("r3", "Ich unterstütze beim Entwerfen, Rechnen und Erklären."),
    ])
    agent = LLMAgent(assistant, SimpleNamespace(responses=fake), "test-model")

    first = agent.respond("Hallo")
    second = agent.respond("Wie geht's?")
    third = agent.respond("Was kannst du eigentlich?")

    assert all(reply.used_llm for reply in (first, second, third))
    assert all("tools" in call for call in fake.calls)
    assert assistant.agent_events == []
    assert assistant.state == before
    assert [item["role"] for item in assistant.message_history] == [
        "user", "assistant", "user", "assistant", "user", "assistant",
    ]


def test_agent_prompt_is_conversational_and_excludes_legacy_json_order() -> None:
    assistant = offline_assistant()
    assert "natürliches Gespräch" in assistant.agent_system_prompt
    assert "ohne Tool" in assistant.agent_system_prompt
    assert "V1 – STRUKTURIERTE AUSGABE" not in assistant.agent_system_prompt
    assert "Antworte ausschließlich im vom Aufrufer vorgegebenen JSON-Schema" not in assistant.agent_system_prompt
    assert "1 bis 4 kurzen" in assistant.agent_system_prompt
    assert "dupliziere keine Listen im Chat" not in assistant.agent_system_prompt
    assert "USER_FIXED" in assistant.agent_system_prompt
    assert "sichtbaren Chat niemals" in assistant.agent_system_prompt


def test_update_design_drops_unmentioned_defaults_and_zero_placeholders() -> None:
    assistant = offline_assistant()
    assistant.message_history.append({
        "role": "user",
        "content": "140 kN GL24h 200x240, rest mach selber",
    })
    from ai.agent import EngineeringTools
    tools = EngineeringTools(assistant)
    tools.update_design(
        {
            "force_ed_kn": 140, "timber_grade": "GL24h",
            "width_b_mm": 200, "height_h_mm": 240,
            "service_class": 1, "load_duration_class": "mittel",
            "dowel_diameter_d_mm": 0, "rows_parallel_n": 0,
        },
        "USER_FIXED", None, True,
    )
    assert assistant.state.parameters == {
        "force_ed_kn": 140, "timber_grade": "GL24h",
        "width_b_mm": 200, "height_h_mm": 240,
    }
    assert assistant.state.fixed_parameters == set(assistant.state.parameters)


def test_update_design_does_not_promote_model_inventions_to_user_fixed() -> None:
    assistant = offline_assistant()
    assistant.message_history.append({
        "role": "user",
        "content": "140 kN GL24h 200x240, möglichst wenige Stabdübel, rest mach selber",
    })
    tools = EngineeringTools(assistant)
    tools.update_design(
        {
            "force_ed_kn": 140, "timber_grade": "GL24h",
            "width_b_mm": 200, "height_h_mm": 240,
            "dowel_diameter_d_mm": 16, "rows_parallel_n": 2,
            "rows_perpendicular_m": 3, "number_of_plates_ns": 2,
        },
        "USER_FIXED", None, True,
    )
    assert assistant.state.fixed_parameters == {
        "force_ed_kn", "timber_grade", "width_b_mm", "height_h_mm",
    }
    assert "dowel_diameter_d_mm" not in assistant.state.parameters


def test_generic_feasibility_optimization_keeps_active_specific_goal() -> None:
    assistant = offline_assistant()
    assistant.state.optimization_goal = "MIN_FASTENER_COUNT"
    tools = EngineeringTools(assistant)
    captured = {}

    def fake_execute(command):
        captured["goal"] = assistant.state.optimization_goal
        captured["minimize"] = assistant.state.minimize_fasteners
        return SimpleNamespace(result=None)

    assistant.execute_local_command = fake_execute
    result = tools.optimize_design("BALANCED_DESIGN", {})

    assert result["objective"] == "MIN_FASTENER_COUNT"
    assert captured == {"goal": "MIN_FASTENER_COUNT", "minimize": True}


def test_model_objective_synonym_maps_to_minimum_fastener_count() -> None:
    assistant = offline_assistant()
    tools = EngineeringTools(assistant)
    captured = {}

    def fake_execute(command):
        captured["goal"] = assistant.state.optimization_goal
        captured["minimize"] = assistant.state.minimize_fasteners
        return SimpleNamespace(result=None)

    assistant.execute_local_command = fake_execute
    result = tools.optimize_design("MINIMIZE_NUMBER_OF_DOWELS", {})

    assert result["objective"] == "MIN_FASTENER_COUNT"
    assert captured == {"goal": "MIN_FASTENER_COUNT", "minimize": True}


def test_gui_runtime_core_routes_small_talk_to_llm_with_zero_tools() -> None:
    assistant = offline_assistant()
    assistant._api_key = "test-key"
    client = FakeOnlineClient([
        final_response("a", "Hallo! Wie kann ich dir helfen?"),
        final_response("b", "Mir geht es gut – womit möchtest du anfangen?"),
        final_response("c", "Ich kann Entwürfe untersuchen und technische Fragen erklären."),
    ])
    with patch("openai.OpenAI", return_value=client):
        replies = [
            assistant.respond("Hallo"),
            assistant.respond("Wie geht's?"),
            assistant.respond("Was kannst du?"),
        ]
    assert all(reply.used_llm for reply in replies)
    assert assistant.llm_online is True
    assert {
        key: assistant.last_runtime_trace[key] for key in (
            "USER_TEXT", "MODE", "LLM_AVAILABLE", "LLM_REQUEST_STARTED",
            "MODEL", "TOOL_CALLS", "RESPONSE_SOURCE",
        )
    } == {
        "USER_TEXT": "Was kannst du?", "MODE": "KI_ONLINE",
        "LLM_AVAILABLE": True, "LLM_REQUEST_STARTED": True,
        "MODEL": "gpt-5-mini", "TOOL_CALLS": 0,
        "RESPONSE_SOURCE": "LLM",
    }


def test_runtime_trace_proves_engineering_tools_then_returns_to_zero_tool_chat() -> None:
    assistant = offline_assistant()
    assistant._api_key = "test-key"
    client = FakeOnlineClient([
        call_response("d1", "update_design", {
            "parameters": {
                "force_kn": 140, "timber_grade": "GL24h",
                "width_mm": 200, "height_mm": 240,
                "service_class": 1, "load_duration_class": "mittel",
            },
            "provenance": "USER_FIXED", "source": None,
            "autonomy_mode": True,
        }),
        call_response("d2", "optimize_design", {
            "objective": "MIN_FASTENER_COUNT", "constraints": {},
        }),
        final_response("d3", "Ich habe den Auftrag mit den Engineering Tools untersucht."),
        final_response("e", "Sehr gern!"),
    ])
    with patch("openai.OpenAI", return_value=client):
        engineering = assistant.respond(
            "140kn gl24 200x240, möglichst wenig stabdübl, rest mach selber"
        )
        engineering_trace = dict(assistant.last_runtime_trace)
        thanks = assistant.respond("Danke")
    assert engineering.used_llm and engineering_trace["TOOL_CALLS"] == 2
    assert engineering_trace["RESPONSE_SOURCE"] == "LLM"
    assert thanks.used_llm
    assert assistant.last_runtime_trace["TOOL_CALLS"] == 0
    assert assistant.last_runtime_trace["RESPONSE_SOURCE"] == "LLM"
