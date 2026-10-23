from __future__ import annotations

"""Deterministischer Rechenkern für axial beanspruchte eingeklebte Stahlstäbe.

Der bewusst eng gefasste Anwendungsbereich folgt ausschließlich:

* ÖNORM B 1995-1-1:2023-08, Anhang I.3 und J
* Köberl (2018), Abschnitte 2-3.3.4 und 2-3.4.3

Nicht abgedeckte Klebstoffsysteme, Querbeanspruchung, kombinierte Beanspruchung
und konstruktive Sonderfälle werden nicht extrapoliert.
"""

from dataclasses import asdict, dataclass, replace
from math import pi
from typing import Any, Iterable


NORM_SOURCE = "ÖNORM B 1995-1-1:2023-08, Anhang I.3, Gl. (NA.I.1)"
SPACING_SOURCE = "ÖNORM B 1995-1-1:2023-08, Tabelle NA.I.2 und Bild NA.I.2"
ADHESIVE_SOURCE = "ÖNORM B 1995-1-1:2023-08, Tabelle NA.J.1"
WOOD_SOURCE = "ÖNORM B 1995-1-1:2023-08, Anhang I.3; Köberl (2018), Gl. (2.33)/(2.15)"
REFERENCE_SOURCE = "Köberl (2018), Tabellen 2-19 und 2-20"


@dataclass(frozen=True, slots=True)
class GluedRodInput:
    force_ed_kn: float
    width_b_mm: float
    height_h_mm: float
    rod_diameter_mm: float
    hole_diameter_mm: float
    effective_embedment_mm: float
    rod_count: int
    rows: int
    columns: int
    spacing_a2_mm: float
    edge_a4_c_mm: float
    tensile_stress_area_mm2: float
    rod_yield_strength_n_mm2: float
    gamma_m1_steel: float
    timber_tension_strength_n_mm2: float
    k_mod: float
    gamma_m_timber: float
    gamma_m_connection: float
    adhesive_system_qualified: bool
    uniform_group_load_confirmed: bool = False
    timber_grade: str = ""
    timber_product: str = "glulam"
    service_class: int = 1
    rod_grade: str = ""


@dataclass(frozen=True, slots=True)
class GluedRodGeometry:
    glue_line_thickness_mm: float
    minimum_embedment_mm: float
    minimum_spacing_a2_mm: float
    minimum_edge_a4_c_mm: float
    net_timber_area_mm2: float
    effective_timber_area_mm2: float
    rod_positions_mm: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class GluedRodCheck:
    name: str
    ed_kn: float
    rd_kn: float
    utilization: float
    status: str
    source: str
    governing_parameters: dict[str, float | str | bool]


@dataclass(frozen=True, slots=True)
class GluedRodResult:
    input: GluedRodInput
    geometry: GluedRodGeometry
    adhesive_strength_n_mm2: float
    checks: tuple[GluedRodCheck, ...]
    governing_check: GluedRodCheck
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GluedRodCalculator:
    """Calculator für Stäbe parallel zur Faser und Zug in Stabachse."""

    def calculate(self, data: GluedRodInput) -> GluedRodResult:
        geometry = self.geometry(data)
        adhesive_strength = self.adhesive_strength(data.effective_embedment_mm)

        steel_rd = (
            data.rod_count
            * data.rod_yield_strength_n_mm2
            * data.tensile_stress_area_mm2
            / data.gamma_m1_steel
            / 1000.0
        )
        bond_rd = (
            data.rod_count
            * pi
            * data.rod_diameter_mm
            * data.effective_embedment_mm
            * adhesive_strength
            * data.k_mod
            / data.gamma_m_connection
            / 1000.0
        )
        wood_rd = (
            geometry.effective_timber_area_mm2
            * data.timber_tension_strength_n_mm2
            * data.k_mod
            / data.gamma_m_timber
            / 1000.0
        )

        checks = (
            self._check(
                "Stahlversagen der Gewindestangen",
                data.force_ed_kn,
                steel_rd,
                NORM_SOURCE,
                {
                    "n": data.rod_count,
                    "fy_b_n_mm2": data.rod_yield_strength_n_mm2,
                    "Aef_mm2": data.tensile_stress_area_mm2,
                    "gamma_M1": data.gamma_m1_steel,
                },
            ),
            self._check(
                "Klebfugen-/Holzversagen entlang der Bohrlochwandung",
                data.force_ed_kn,
                bond_rd,
                f"{NORM_SOURCE}; {ADHESIVE_SOURCE}",
                {
                    "n": data.rod_count,
                    "d_mm": data.rod_diameter_mm,
                    "l_ef_mm": data.effective_embedment_mm,
                    "fk1k_n_mm2": adhesive_strength,
                    "k_mod": data.k_mod,
                    "gamma_M_connection": data.gamma_m_connection,
                },
            ),
            self._check(
                "Holzversagen am Stabende / Nettoquerschnitt",
                data.force_ed_kn,
                wood_rd,
                WOOD_SOURCE,
                {
                    "A_net_mm2": geometry.net_timber_area_mm2,
                    "A_effective_mm2": geometry.effective_timber_area_mm2,
                    "ft_0_k_n_mm2": data.timber_tension_strength_n_mm2,
                    "k_mod": data.k_mod,
                    "gamma_M_timber": data.gamma_m_timber,
                },
            ),
        )
        governing = min(checks, key=lambda item: item.rd_kn)

        # Bei mehreren Stäben verlangt Anhang I.3 Stahlversagen, sofern eine
        # ungleichmäßige Beanspruchung nicht ausgeschlossen werden kann.
        group_rule_ok = (
            data.rod_count == 1
            or data.uniform_group_load_confirmed
            or governing.name == "Stahlversagen der Gewindestangen"
        )
        return GluedRodResult(
            input=data,
            geometry=geometry,
            adhesive_strength_n_mm2=adhesive_strength,
            checks=checks,
            governing_check=governing,
            passed=all(check.status == "ERFÜLLT" for check in checks) and group_rule_ok,
        )

    def geometry(self, data: GluedRodInput) -> GluedRodGeometry:
        self._validate(data)
        d = data.rod_diameter_mm
        min_embedment = max(0.5 * d**2, 10.0 * d)
        min_spacing = 5.0 * d
        min_edge = 2.5 * d

        if data.effective_embedment_mm < min_embedment:
            raise ValueError(
                f"Wirksame Einklebelänge {data.effective_embedment_mm:g} mm unterschreitet "
                f"l_ef,min = {min_embedment:g} mm ({SPACING_SOURCE})."
            )
        if data.effective_embedment_mm > 1000.0:
            raise ValueError("Tabelle NA.J.1 deckt wirksame Einklebelängen nur bis 1000 mm ab.")
        if data.spacing_a2_mm < min_spacing:
            raise ValueError(
                f"a2 = {data.spacing_a2_mm:g} mm unterschreitet 5·d = {min_spacing:g} mm."
            )
        if data.edge_a4_c_mm < min_edge:
            raise ValueError(
                f"a4,c = {data.edge_a4_c_mm:g} mm unterschreitet 2,5·d = {min_edge:g} mm."
            )

        required_width = 2 * data.edge_a4_c_mm + (data.columns - 1) * data.spacing_a2_mm
        required_height = 2 * data.edge_a4_c_mm + (data.rows - 1) * data.spacing_a2_mm
        if required_width > data.width_b_mm or required_height > data.height_h_mm:
            raise ValueError("Stabanordnung passt mit den angegebenen Mindestabständen nicht in den Holzquerschnitt.")

        x0 = (data.width_b_mm - (data.columns - 1) * data.spacing_a2_mm) / 2.0
        y0 = (data.height_h_mm - (data.rows - 1) * data.spacing_a2_mm) / 2.0
        positions = tuple(
            (x0 + column * data.spacing_a2_mm, y0 + row * data.spacing_a2_mm)
            for row in range(data.rows)
            for column in range(data.columns)
        )
        net_area = (
            data.width_b_mm * data.height_h_mm
            - data.rod_count * pi * data.hole_diameter_mm**2 / 4.0
        )
        # Anhang I.3 begrenzt die wirksame Holzfläche auf 36·d² je Stab.
        effective_area = min(net_area, data.rod_count * 36.0 * d**2)
        return GluedRodGeometry(
            glue_line_thickness_mm=(data.hole_diameter_mm - d) / 2.0,
            minimum_embedment_mm=min_embedment,
            minimum_spacing_a2_mm=min_spacing,
            minimum_edge_a4_c_mm=min_edge,
            net_timber_area_mm2=net_area,
            effective_timber_area_mm2=effective_area,
            rod_positions_mm=positions,
        )

    @staticmethod
    def adhesive_strength(effective_embedment_mm: float) -> float:
        if effective_embedment_mm <= 250.0:
            return 4.0
        if effective_embedment_mm <= 500.0:
            return 5.25 - 0.005 * effective_embedment_mm
        if effective_embedment_mm <= 1000.0:
            return 3.5 - 0.0015 * effective_embedment_mm
        raise ValueError("Keine dokumentierte Klebefugenfestigkeit für l_ef > 1000 mm.")

    @staticmethod
    def _check(
        name: str,
        ed_kn: float,
        rd_kn: float,
        source: str,
        parameters: dict[str, float | str | bool],
    ) -> GluedRodCheck:
        utilization = ed_kn / rd_kn
        return GluedRodCheck(
            name=name,
            ed_kn=ed_kn,
            rd_kn=rd_kn,
            utilization=utilization,
            status="ERFÜLLT" if utilization <= 1.0 else "NICHT ERFÜLLT",
            source=source,
            governing_parameters=parameters,
        )

    @staticmethod
    def _validate(data: GluedRodInput) -> None:
        numeric_positive = {
            "force_ed_kn": data.force_ed_kn,
            "width_b_mm": data.width_b_mm,
            "height_h_mm": data.height_h_mm,
            "rod_diameter_mm": data.rod_diameter_mm,
            "hole_diameter_mm": data.hole_diameter_mm,
            "effective_embedment_mm": data.effective_embedment_mm,
            "spacing_a2_mm": data.spacing_a2_mm,
            "edge_a4_c_mm": data.edge_a4_c_mm,
            "tensile_stress_area_mm2": data.tensile_stress_area_mm2,
            "rod_yield_strength_n_mm2": data.rod_yield_strength_n_mm2,
            "gamma_m1_steel": data.gamma_m1_steel,
            "timber_tension_strength_n_mm2": data.timber_tension_strength_n_mm2,
            "k_mod": data.k_mod,
            "gamma_m_timber": data.gamma_m_timber,
            "gamma_m_connection": data.gamma_m_connection,
        }
        for name, value in numeric_positive.items():
            if value <= 0:
                raise ValueError(f"{name} muss größer als 0 sein.")
        if min(data.rod_count, data.rows, data.columns) < 1:
            raise ValueError("Stabanzahl, Reihen und Spalten müssen mindestens 1 sein.")
        if data.rod_count != data.rows * data.columns:
            raise ValueError("rod_count muss rows · columns entsprechen.")
        if data.hole_diameter_mm <= data.rod_diameter_mm:
            raise ValueError("Der Bohrlochdurchmesser muss größer als der Stabdurchmesser sein.")
        if not 6.0 <= data.rod_diameter_mm <= 30.0:
            raise ValueError("Anhang I gilt nur für Nenndurchmesser von 6 mm bis 30 mm.")
        if data.timber_product not in {"glulam", "glued_laminated_beam"}:
            raise ValueError(
                "Anhang I gilt nur für Brettschicht- und Balkenschichtholz."
            )
        if data.service_class not in {1, 2}:
            raise ValueError("Eingeklebte Stahlstäbe sind nur in Nutzungsklasse 1 oder 2 zulässig.")
        if not data.adhesive_system_qualified:
            raise ValueError(
                "Tabelle NA.J.1 darf nur bei nachgewiesener Eignung des Klebersystems verwendet werden."
            )


def generate_glued_rod_variants(
    base: GluedRodInput,
    documented_candidates: Iterable[dict[str, Any]],
) -> tuple[GluedRodResult, ...]:
    """Berechnet ausschließlich explizit quellenbelegte Kandidaten.

    Das Modul erfindet bewusst keine Durchmesser- oder Längenreihe. Der Aufrufer
    muss jeden Kandidaten aus einer Zulassung oder Bemessungsunterlage übergeben.
    Unzulässige Geometrien werden verworfen.
    """

    calculator = GluedRodCalculator()
    results: list[GluedRodResult] = []
    for candidate in documented_candidates:
        try:
            results.append(calculator.calculate(replace(base, **candidate)))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(results, key=lambda result: result.governing_check.rd_kn, reverse=True))


def koerberl_gl24h_reference_input(force_ed_kn: float = 83.2) -> GluedRodInput:
    """Referenz aus Köberl (2018); Ed ist nur der wählbare Prüfwert.

    Die Quelle ist eine Tragfähigkeitsstudie und nennt kein Ed. Der dokumentierte
    Sollwert des maßgebenden Widerstands beträgt 83,2 kN.
    """

    return GluedRodInput(
        force_ed_kn=force_ed_kn,
        width_b_mm=80.0,
        height_h_mm=80.0,
        rod_diameter_mm=8.0,
        hole_diameter_mm=11.0,
        effective_embedment_mm=1000.0,
        rod_count=4,
        rows=2,
        columns=2,
        spacing_a2_mm=40.0,
        edge_a4_c_mm=20.0,
        tensile_stress_area_mm2=36.6,
        rod_yield_strength_n_mm2=640.0,
        gamma_m1_steel=1.0,
        timber_tension_strength_n_mm2=19.2,
        k_mod=0.9,
        gamma_m_timber=1.25,
        gamma_m_connection=1.3,
        adhesive_system_qualified=True,
        uniform_group_load_confirmed=True,
        timber_grade="GL24h",
        timber_product="glulam",
        service_class=2,
        rod_grade="8.8",
    )
