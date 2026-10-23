from __future__ import annotations

from ai.engineering_assessment import (
    SECTION_TITLES,
    _validate_report,
    build_assessment_context,
)
from desktop.bridge import DesktopBridge
from desktop.serializers import serialize_snapshot


def test_140_kn_context_and_compact_assessment_use_kernel_values() -> None:
    bridge = DesktopBridge(demo_enabled=True)
    snapshot = serialize_snapshot(bridge.assistant, bridge.conversation, demo=bridge.demo)
    context = build_assessment_context(snapshot, bridge.conversation)

    assert context is not None
    assert context.design_load == {"forceEdKn": 140.0}
    assert context.governing_check["name"] == "Verbindungsmittel im Holz"
    assert context.governing_check["utilizationPercent"] == 92.6
    assert len(context.calculated_checks) == 7
    assert all(item["label"] for item in context.alternative_variants)

    compact = snapshot["engineeringAssessment"]
    assert compact["suitable"] is True
    assert compact["utilizationPercent"] == 92.6
    assert compact["reservePercent"] == 7.4
    assert compact["governingCheck"] == "Verbindungsmittel im Holz"


def test_report_guard_rejects_unavailable_cost_claim_and_invented_number() -> None:
    bridge = DesktopBridge(demo_enabled=True)
    snapshot = serialize_snapshot(bridge.assistant, bridge.conversation, demo=bridge.demo)
    context = build_assessment_context(snapshot, bridge.conversation)
    assert context is not None
    sections = [
        {"title": title, "content": "Bewertung aus den vorliegenden Ergebnissen."}
        for title in SECTION_TITLES
    ]
    sections[0]["content"] = "Diese Variante ist am billigsten."
    try:
        _validate_report(sections, context)
        raise AssertionError("Kostenbehauptung wurde nicht zurückgewiesen")
    except ValueError as exc:
        assert "Bewertungsdimension" in str(exc)

    sections[0]["content"] = "Die Ausnutzung beträgt 77,7 %."
    try:
        _validate_report(sections, context)
        raise AssertionError("Erfundene Zahl wurde nicht zurückgewiesen")
    except ValueError as exc:
        assert "Nicht belegte Zahl" in str(exc)


def test_cheapest_question_is_refused_without_cost_data() -> None:
    bridge = DesktopBridge(demo_enabled=True)
    bridge.assistant.state.last_result = bridge.demo.result
    response = bridge.send_message({"text": "Welche Variante ist am billigsten?"})
    answer = response["data"]["conversation"][-1]["content"]
    assert "nicht möglich" in answer
    assert "keine Kostenwerte" in answer
    assert "am billigsten" not in answer


def test_detailed_report_endpoint_uses_context_without_changing_result(monkeypatch) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    bridge.assistant.state.last_result = bridge.demo.result
    before = bridge.assistant.state.last_result
    captured = {}

    monkeypatch.setattr(bridge.assistant, "provider_available", lambda provider: True)

    def fake_generate(assistant, context):
        captured["context"] = context
        return [
            {"title": title, "content": "Bewertung aus den vorliegenden Ergebnissen."}
            for title in SECTION_TITLES
        ]

    monkeypatch.setattr("desktop.bridge.generate_engineering_report", fake_generate)
    response = bridge.create_engineering_assessment()

    assert response["ok"] is True
    assert len(response["report"]["sections"]) == 11
    assert captured["context"].design_load["forceEdKn"] == 140.0
    assert bridge.assistant.state.last_result is before
