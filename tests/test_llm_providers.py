from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

from ai.assistant import StabduebelAssistant
from calculations.stabduebel import StabduebelInput
from desktop.bridge import DesktopBridge


def test_local_is_default_and_provider_switch_preserves_state() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    calculated = bridge.manual_calculate(asdict(StabduebelInput()))
    before = calculated["data"]["currentResult"]
    assert bridge.assistant.llm_provider == "local"

    switched = bridge.set_llm_provider({"provider": "openai"})
    assert switched["ok"] is True
    assert switched["data"]["agentStatus"]["provider"] == "openai"
    assert switched["data"]["currentResult"] == before

    back = bridge.set_llm_provider({"provider": "local"})
    assert back["data"]["agentStatus"]["provider"] == "local"
    assert back["data"]["currentResult"] == before


def test_openai_quota_error_returns_demo_hint_without_crash() -> None:
    assistant = StabduebelAssistant()
    assistant.llm_provider = "openai"
    assistant._api_key = "configured-not-hardcoded"
    assistant.llm_status = "ONLINE"
    assistant._agent = SimpleNamespace(
        respond=lambda _text: (_ for _ in ()).throw(
            RuntimeError("429 insufficient_quota credit_balance_exhausted")
        )
    )

    reply = assistant.respond("Hallo")
    assert reply.used_llm is False
    assert "auf die lokale KI wechseln" in reply.text
    assert assistant.llm_status == "ERROR"


def test_no_llm_keeps_deterministic_calculation_available() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    with patch.object(bridge.assistant, "provider_available", return_value=False):
        reply = bridge.manual_calculate(asdict(StabduebelInput()))
    assert reply["ok"] is True
    assert reply["data"]["currentResult"] is not None
