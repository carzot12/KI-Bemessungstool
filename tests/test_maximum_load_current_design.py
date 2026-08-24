from unittest.mock import patch

from ai.assistant import StabduebelAssistant
from desktop.bridge import DesktopBridge


def test_maximum_load_uses_current_calculated_connection() -> None:
    with patch.object(
        StabduebelAssistant, "_resolve_api_key", return_value=(None, "test")
    ):
        bridge = DesktopBridge(demo_enabled=False)
    bridge.compact_calculate({
        "force_ed_kn": 140, "timber_grade": "GL24h",
        "width_b_mm": 200, "height_h_mm": 240,
        "service_class": 1, "load_duration_class": "mittel",
        "objective": "BALANCED_DESIGN",
    })
    current = bridge.assistant.state.last_result
    assert current is not None and current.passed

    text = bridge.assistant._maximum_load_text()

    assert "maximale Bemessungslast" in text
    assert f"{current.input.rows_parallel_n} × {current.input.rows_perpendicular_m}" in text
    assert f"Ø{current.input.dowel_diameter_d_mm:g} mm" in text
    numeric = float(text.split("rund ", 1)[1].split(" kN", 1)[0])
    assert numeric >= current.input.force_ed_kn
