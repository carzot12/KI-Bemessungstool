from __future__ import annotations

from dataclasses import asdict
import subprocess

from calculations.stabduebel import StabduebelInput
from desktop.bridge import DesktopBridge
from desktop.reports import create_report


def test_pdf_smoke_uses_current_favorite_snapshot(tmp_path, technical_drawings) -> None:
    bridge = DesktopBridge(demo_enabled=False)
    reference = StabduebelInput(
        project_name="PDF Referenzprojekt",
        force_ed_kn=140.0,
        timber_grade="GL24h",
        width_b_mm=200.0,
        height_h_mm=240.0,
        number_of_plates_ns=2,
        plate_thickness_ts_mm=6.0,
        side_thickness_t1_mm=60.0,
        middle_thickness_t2_mm=68.0,
        dowel_diameter_d_mm=12.0,
        hole_diameter_d0_mm=13.0,
        rows_parallel_n=2,
        rows_perpendicular_m=4,
        a1_mm=60.0,
        a2_mm=40.0,
        a3_t_mm=85.0,
        a4_c_mm=60.0,
        e1_mm=20.0,
        e2_mm=20.0,
    )
    response = bridge.manual_calculate(asdict(reference))
    assert response["ok"] is True
    snapshot = response["data"]
    assert snapshot["currentVariant"]["input"] == snapshot["currentResult"]["input"]

    report = create_report(
        snapshot, "calculation", tmp_path,
        filename="PDF_Referenzbericht.pdf",
        technical_drawings=technical_drawings,
    )

    assert report.exists()
    assert report.stat().st_size > 1_000
    assert report.read_bytes().startswith(b"%PDF-")
    info = subprocess.run(
        ["pdfinfo", str(report)], check=True, capture_output=True, text=True,
    ).stdout
    pages_line = next(line for line in info.splitlines() if line.startswith("Pages:"))
    assert int(pages_line.split(":", 1)[1]) > 0
    text = subprocess.run(
        ["pdftotext", str(report), "-"], check=True,
        capture_output=True, text=True,
    ).stdout
    for expected in (
        "PDF Referenzprojekt",
        "Gewählte Variante / Favorit",
        "Geometrie und Mindestabstände",
        "Nachweise der Favoritenvariante",
        "Quellen und Normstellen",
        "200 × 240 mm",
        "Ø12 mm",
        "2 × 4 = 8 je Stoßseite",
    ):
        assert expected in text
