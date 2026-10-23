from __future__ import annotations

"""Presentation reports built only from serialized deterministic results."""

from datetime import datetime
from base64 import b64decode
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RED = colors.HexColor("#B20D30")
GREEN = colors.HexColor("#228B57")
LIGHT = colors.HexColor("#F3F4F6")


def _same_design(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(value == right.get(key) for key, value in left.items() if key != "project_name")


def _validate_geometry_values(geometry: dict[str, Any]) -> None:
    layers = geometry.get("crossSectionLayersMm") or []
    if abs(sum(layers) - geometry.get("sectionWidthMm", 0)) > 1e-6:
        raise ValueError("Schichtsumme und Querschnittsbreite b sind nicht konsistent.")
    n = int(geometry.get("rowsParallel", 0))
    m = int(geometry.get("rowsPerpendicular", 0))
    if len(geometry.get("dowelPositionsLeftMm") or []) != n * m or len(geometry.get("dowelPositionsRightMm") or []) != n * m:
        raise ValueError("Dübelkoordinaten und Anordnung n x m sind nicht konsistent.")
    if len(geometry.get("platePositionsMm") or []) != int(geometry.get("plateCount", 0)):
        raise ValueError("Blechanzahl und Blechpositionen sind nicht konsistent.")
    if abs(geometry["plateBottomMm"] - geometry["plateTopMm"] - geometry["plateHeightMm"]) > 1e-6:
        raise ValueError("Blechhöhe und Blechkoordinaten sind nicht konsistent.")
    if abs(2 * (geometry["columnPositionsMm"][-1] + geometry["e1Mm"]) - geometry["plateLengthMm"]) > 1e-6:
        raise ValueError("Blechlänge und Dübelkoordinaten sind nicht konsistent.")


def _validated_geometry(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = snapshot.get("currentResult") or {}
    data = result.get("input") or {}
    geometry = snapshot.get("connectionGeometry") or {}
    current = snapshot.get("currentVariant") or {}
    if not data or not geometry:
        raise ValueError("Geometrie des aktuellen Berechnungssnapshots fehlt.")
    if current and not _same_design(data, current.get("input") or {}):
        raise ValueError("Bericht und aktuell gewählte Variante sind nicht konsistent.")
    _validate_geometry_values(geometry)
    return geometry


def _technical_image(drawing: dict[str, Any], max_width: float, max_height: float) -> Image:
    data_url = str(drawing.get("dataUrl") or "")
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("Technische UI-Darstellung ist kein PNG-Datenbild.")
    raw = b64decode(data_url[len(prefix):], validate=True)
    image = Image(BytesIO(raw))
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return image


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def create_report(
    snapshot: dict[str, Any], report_type: str, output_dir: Path,
    filename: str | None = None,
    technical_drawings: dict[str, dict[str, Any]] | None = None,
) -> Path:
    result = snapshot.get("currentResult")
    if not result:
        raise ValueError("Für einen Bericht ist zuerst eine Berechnung erforderlich.")
    geometry = _validated_geometry(snapshot)
    expected_views = {"side", "top", "section", "isometric"}
    if not isinstance(technical_drawings, dict) or set(technical_drawings) != expected_views:
        raise ValueError("Für den Bericht werden alle vier technischen UI-Darstellungen benötigt.")
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "variantenbericht" if report_type == "variants" else "berechnungsbericht"
    target = output_dir / (filename or f"KI-Tool_{suffix}.pdf")
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=18 * mm,
                            leftMargin=18 * mm, topMargin=17 * mm,
                            bottomMargin=17 * mm, title="KI-Tool",
                            author="holz.bau forschungs gmbh")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"],
                              textColor=RED, fontSize=22, leading=27,
                              alignment=TA_LEFT, spaceAfter=8 * mm))
    styles["Heading1"].textColor = RED
    styles["Heading1"].fontSize = 16
    styles["Heading2"].spaceBefore = 3 * mm
    body = styles["BodyText"]
    body.spaceAfter = 2.5 * mm
    data = result["input"]
    status = "ZULÄSSIG UND ERFÜLLT" if result["passed"] and result["normAdmissible"] else "NICHT ERFÜLLT"
    report_variants = snapshot.get("reportVariants") or [snapshot.get("currentVariant")]
    report_variants = [item for item in report_variants if item]

    def title(page_title: str, subtitle: str = "") -> list[Any]:
        items: list[Any] = [Paragraph(page_title, styles["Heading1"])]
        if subtitle:
            items += [Paragraph(subtitle, body), Spacer(1, 3 * mm)]
        return items

    story: list[Any] = [
        Paragraph("KI-gestütztes Bemessungstool Holzbau", styles["ReportTitle"]),
        Paragraph("Bemessungsbericht · Zuglaschenstoß mit Stabdübeln", styles["Heading1"]),
        Paragraph(f"Projekt: {_fmt(snapshot.get('projectName') or data.get('project_name') or 'Ohne Projektname')}", styles["Heading2"]),
        Paragraph(f"Erstellt am {datetime.now().strftime('%d.%m.%Y, %H:%M Uhr')}", body),
        Spacer(1, 7 * mm),
        Paragraph("1. Aufgabenstellung / Eingaben", styles["Heading2"]),
        _table([
            ["Bemessungsfall", "Zuglaschenstoß mit innenliegenden Stahlblechen und Stabdübeln"],
            ["Material / Nutzung", f"{data['timber_grade']} · NK {data['service_class']} · {data['load_duration_class']}"],
            ["Bemessungslast Ft,Ed", f"{_fmt(data['force_ed_kn'])} kN"],
        ], col_widths=[55, 115]),
        Spacer(1, 5 * mm),
        Paragraph("Gewählte Variante / Favorit", styles["Heading2"]),
        _table([
            ["Bemessungslast Ft,d", f"{_fmt(data['force_ed_kn'])} kN"],
            ["Holz / Querschnitt", f"{data['timber_grade']} · {_fmt(data['width_b_mm'])} × {_fmt(data['height_h_mm'])} mm"],
            ["Nutzung", f"NK {data['service_class']} · {data['load_duration_class']}"],
            ["Aufbau", f"{data['number_of_plates_ns']} Blech(e), ts={_fmt(data['plate_thickness_ts_mm'])} mm"],
            ["Breitenaufteilung", f"t1={_fmt(data['side_thickness_t1_mm'])} mm · t2={_fmt(data['middle_thickness_t2_mm'])} mm"],
            ["Stabdübel", f"Ø{_fmt(data['dowel_diameter_d_mm'])} mm · {data['rows_parallel_n']} × {data['rows_perpendicular_m']} = {data['rows_parallel_n'] * data['rows_perpendicular_m']} je Stoßseite"],
            ["Ausnutzung / Status", f"{result['utilization'] * 100:.1f} % · {status}"],
        ], col_widths=[55, 115]),
        Spacer(1, 4 * mm), Paragraph(snapshot.get("recommendation") or "", body),

        PageBreak(), *title("Variantenvergleich", "Ausschließlich tatsächlich berechnete, zulässige und deduplizierte Varianten."),
    ]
    variant_rows = [["Kategorie", "Aufbau", "Ø / Raster", "Anzahl", "η", "Maßgebend"]]
    for item in report_variants:
        variant_rows.append([
            item.get("category", item.get("label", "Variante")),
            f"{item['plateCount']} Blech(e), ts {item['plateThicknessMm']} mm",
            f"{item['diameterMm']} mm / {item['rowsParallel']}×{item['rowsPerpendicular']}",
            item["fastenerCount"], f"{item['utilization'] * 100:.1f} %",
            item["governingCheck"],
        ])
    story += [_table(variant_rows, header=True, font_size=7.2,
                     col_widths=[38, 37, 30, 16, 16, 33]),
              Spacer(1, 6 * mm), Paragraph("Entscheidungshilfe", styles["Heading2"])]
    for item in report_variants:
        story.append(Paragraph(
            f"<b>{item.get('category', item['label'])}</b>: {item.get('characteristic') or item.get('interestReason', '')} "
            f"Tatsächliche Ausnutzung {item['utilization'] * 100:.1f} %, Reserve {item['reserve'] * 100:.1f} %.", body))
    story += [Spacer(1, 3 * mm), Paragraph(
        "Die Kategorie „ausgewogen“ ist eine heuristische Rangordnung im berechneten Variantenraum; "
        "sie ist keine Kostenberechnung und ersetzt keine projektspezifische Wirtschaftlichkeitsprüfung.", styles["Italic"])]
    opt = snapshot.get("lastOptimization") or {}
    if opt:
        story.append(Paragraph(
            f"Untersucht: {opt.get('evaluatedCount', 0)} Varianten; technisch geeignet: {opt.get('feasibleCount', 0)}; "
            f"kuratierte Shortlist: {opt.get('shortlistedCount', 0)}.", body))

    geometry_rows = [["Bereich", "Parameter", "Wert"],
        ["Querschnitt", "b × h", f"{_fmt(geometry['sectionWidthMm'])} × {_fmt(geometry['sectionHeightMm'])} mm"],
        ["Bleche", "Anzahl / ts / L / H", f"{geometry['plateCount']} / {_fmt(geometry['plateThicknessMm'])} / {_fmt(geometry['plateLengthMm'])} / {_fmt(geometry['plateHeightMm'])} mm"],
        ["Schichten", "über b", " | ".join(_fmt(v) for v in geometry["crossSectionLayersMm"]) + " mm"],
        ["Stabdübel", "d / n × m", f"{_fmt(geometry['dowelDiameterMm'])} mm / {geometry['rowsParallel']} × {geometry['rowsPerpendicular']}"],
        ["Holzabstände", "a1 / a2 / a3,t / a4,c", f"{_fmt(geometry['a1Mm'])} / {_fmt(geometry['a2Mm'])} / {_fmt(geometry['a3tMm'])} / {_fmt(geometry['a4cMm'])} mm"],
        ["Blechabstände", "e1 / e2", f"{_fmt(geometry['e1Mm'])} / {_fmt(geometry['e2Mm'])} mm"],
        ["Tatsächliche Ränder", "oben / unten", f"{_fmt(geometry['topTimberEdgeDistanceMm'])} / {_fmt(geometry['bottomTimberEdgeDistanceMm'])} mm"],
    ]
    req_rows = [["Parameter", "Minimum", "Ist", "Status"]]
    for check in result.get("geometryRequirements") or []:
        req_rows.append([check["name"], f"{_fmt(check['required'])} {check['unit']}",
                         f"{_fmt(check['actual'])} {check['unit']}", check["status"]])
    story += [PageBreak(), *title("Geometrie und Mindestabstände",
              "Tabellen und Zeichnungen verwenden denselben ConnectionGeometry-Snapshot."),
              _table(geometry_rows, header=True, col_widths=[38, 55, 77]),
              Spacer(1, 6 * mm), Paragraph("Normative Geometrieprüfung", styles["Heading2"]),
              _table(req_rows, header=True, col_widths=[65, 35, 35, 35]),
              Spacer(1, 3 * mm), Paragraph(
                  "Automatisch erzeugte Querreihen sind symmetrisch zentriert: oben = unten = "
                  f"{_fmt(geometry['topTimberEdgeDistanceMm'])} mm. e1 und e2 sind dokumentierte "
                  "Stahlblechrandabstände; der Rechenkern führt dafür keine separate normative Mindestwertprüfung.", body),

              PageBreak(), *title("Technische Darstellungen · Seitenansicht und Draufsicht",
              "Direkt aus denselben React-SVGs und demselben ConnectionGeometry-Snapshot wie die Benutzeroberfläche."),
              Paragraph("Seitenansicht", styles["Heading2"]),
              _technical_image(technical_drawings["side"], 170 * mm, 72 * mm),
              Spacer(1, 3 * mm), Paragraph("Draufsicht", styles["Heading2"]),
              _technical_image(technical_drawings["top"], 170 * mm, 60 * mm),

              PageBreak(), *title("Technische Darstellungen · Schnitt und 3D",
              "Bemaßungen, Beschriftungen, Orientierung und Proportionen entsprechen unmittelbar der Oberfläche."),
              Paragraph("Schnitt A-A", styles["Heading2"]),
              _technical_image(technical_drawings["section"], 170 * mm, 92 * mm),
              Spacer(1, 3 * mm), Paragraph("3D-Darstellung", styles["Heading2"]),
              _technical_image(technical_drawings["isometric"], 170 * mm, 72 * mm),
    ]
    check_rows = [["Nachweis", "Ed [kN]", "Rd [kN]", "Ausnutzung", "Status"]]
    governing_row = None
    for check in result["checks"]:
        check_rows.append([check["name"], f"{data['force_ed_kn']:.2f}", f"{check['resistance_kn']:.2f}",
                           f"{check['utilization'] * 100:.1f} %",
                           "erfüllt" if check["passed"] else "nicht erfüllt"])
        if check["name"] == result["governingCheck"]:
            governing_row = len(check_rows) - 1
    check_table = _table(check_rows, header=True, col_widths=[65, 24, 26, 28, 27])
    if governing_row is not None:
        check_table.setStyle(TableStyle([
            ("BACKGROUND", (0, governing_row), (-1, governing_row), colors.HexColor("#FBE9ED")),
            ("FONTNAME", (0, governing_row), (-1, governing_row), "Helvetica-Bold"),
        ]))
    story += [PageBreak(), *title("Nachweise der Favoritenvariante"),
              check_table,
              Spacer(1, 8 * mm), Paragraph("Gesamtbewertung", styles["Heading2"]),
              Paragraph(f"Maßgebend: {result['governingCheck']}. Maximale Ausnutzung: {result['utilization'] * 100:.1f} %. Status: {status}.", body)]
    maximum = snapshot.get("lastMaximumLoad")
    if maximum:
        story.append(Paragraph(
            f"Tragfähigkeitsuntersuchung bei unveränderter Geometrie: Ft,d={maximum['forceEdKn']} kN, "
            f"maßgebend {maximum['governingCheck']}, Ausnutzung {maximum['utilization']:.2f}.", body))

    story += [PageBreak(), *title("KI-Auswertung / Empfehlung und Quellen"),
              Paragraph(snapshot.get("recommendation") or "Keine KI-Einschätzung vorhanden.", body),
              Spacer(1, 5 * mm), Paragraph(
                  "Die sprachliche Einordnung bewertet ausschließlich Resultate des deterministischen Rechenkerns. "
                  "Sie ändert keine Nachweisformel, keinen Normwert und keine berechnete Geometrie.", styles["Italic"]),
              Spacer(1, 7 * mm), Paragraph("Quellen und Normstellen", styles["Heading2"])]
    sources = snapshot.get("sources") or []
    story.extend(Paragraph(f"• {source}", body) for source in sources)
    story += [Spacer(1, 8 * mm), Paragraph("Hinweis Prototyp", styles["Heading2"]), Paragraph(
        "Dieses Demonstrationswerkzeug unterstützt den Entwurf. Projektbezogene Randbedingungen, "
        "Ausführung, Gesamttragwerk und prüffähige Freigabe sind durch eine qualifizierte Fachperson zu beurteilen.", body)]

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#D9DEE5"))
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 8 * mm, "KI-Tool · technischer Entwurfsbericht")
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Seite {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return target


def _table(rows: list[list[Any]], header: bool = False, font_size: float = 9,
           col_widths: list[float] | None = None) -> Table:
    cell_style = ParagraphStyle("TableCell", fontName="Helvetica", fontSize=font_size,
                                leading=font_size + 2, textColor=colors.black)
    head_style = ParagraphStyle("TableHead", parent=cell_style,
                                fontName="Helvetica-Bold", textColor=colors.white)
    wrapped = [[Paragraph(str(cell), head_style if header and row_index == 0 else cell_style)
                for cell in row] for row_index, row in enumerate(rows)]
    widths = [value * mm for value in col_widths] if col_widths else None
    table = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9DEE5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(style))
    return table
