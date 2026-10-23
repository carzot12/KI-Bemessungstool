from __future__ import annotations

from dataclasses import asdict
import subprocess

import pytest

from calculations.stabduebel import StabduebelInput
from desktop.bridge import DesktopBridge
from desktop.reports import create_report


def test_new_session_is_empty_and_reference_example_is_explicit() -> None:
    bridge = DesktopBridge()
    snapshot = bridge.bootstrap()["data"]
    assert snapshot["technicalState"] == {}
    assert snapshot["currentResult"] is None
    assert snapshot["variants"] == []
    assert snapshot["visualizationModel"] is None
    assert snapshot["sources"] == []

    example = bridge.manual_example()["data"]
    assert example["force_ed_kn"] == 140.0
    assert bridge.bootstrap()["data"]["currentResult"] is None


def test_reset_clears_shared_design_but_keeps_clean_conversation() -> None:
    bridge = DesktopBridge(demo_enabled=False)
    bridge.manual_calculate(asdict(StabduebelInput()))
    assert bridge.bootstrap()["data"]["currentResult"] is not None

    reset = bridge.reset_design()["data"]
    assert reset["technicalState"] == {}
    assert reset["currentResult"] is None
    assert reset["variants"] == []
    assert len(reset["conversation"]) == 1


def test_reports_contain_only_available_result_and_variants(tmp_path, technical_drawings) -> None:
    bridge = DesktopBridge(demo_enabled=False)
    bridge.manual_calculate(asdict(StabduebelInput()))
    snapshot = bridge.bootstrap()["data"]

    calculation = create_report(snapshot, "calculation", tmp_path, technical_drawings=technical_drawings)
    variants = create_report(snapshot, "variants", tmp_path, technical_drawings=technical_drawings)
    assert calculation.exists() and calculation.stat().st_size > 1_000
    assert variants.exists() and variants.stat().st_size > 1_000


def test_report_without_calculation_is_rejected(tmp_path) -> None:
    bridge = DesktopBridge(demo_enabled=False)
    snapshot = bridge.bootstrap()["data"]
    try:
        create_report(snapshot, "calculation", tmp_path)
    except ValueError as exc:
        assert "Berechnung" in str(exc)
    else:
        raise AssertionError("Leerer Entwurf darf keinen Bericht erzeugen")


def test_report_geometry_is_identical_to_python_snapshot(tmp_path, technical_drawings) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    snapshot = bridge.bootstrap()["data"]
    geometry = snapshot["connectionGeometry"]
    report = create_report(snapshot, "calculation", tmp_path, technical_drawings=technical_drawings)
    text = subprocess.run(
        ["pdftotext", str(report), "-"], check=True,
        capture_output=True, text=True,
    ).stdout

    assert "Geometrie und Mindestabstände" in text
    assert f"{geometry['sectionWidthMm']:g} × {geometry['sectionHeightMm']:g} mm" in text
    assert f"{geometry['plateLengthMm']:g} / {geometry['plateHeightMm']:g} mm" in text
    assert (
        f"{geometry['a1Mm']:g} / {geometry['a2Mm']:g} / "
        f"{geometry['a3tMm']:g} / {geometry['a4cMm']:g} mm"
    ) in text
    assert f"{geometry['e1Mm']:g} / {geometry['e2Mm']:g} mm" in text
    assert "Normative Geometrieprüfung" in text
    assert "Technische Darstellungen" in text
    assert "Seitenansicht" in text
    assert "Draufsicht" in text
    assert "Schnitt A-A" in text
    assert "3D-Darstellung" in text


def test_report_rejects_inconsistent_snapshot_geometry(tmp_path) -> None:
    bridge = DesktopBridge(demo_enabled=True)
    snapshot = bridge.bootstrap()["data"]
    snapshot["connectionGeometry"]["crossSectionLayersMm"] = [1.0, 2.0]

    with pytest.raises(ValueError, match="Schichtsumme"):
        create_report(snapshot, "calculation", tmp_path)
