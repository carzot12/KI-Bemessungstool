from __future__ import annotations

"""
Parametrisierbarer Rechenkern für einen 4-schnittigen Stabdübel-Zugstoß
mit zwei innenliegenden Schlitzblechen.

Die Eingabewerte werden über ``StabduebelInput`` übergeben. Dadurch kann
das Modul direkt aus einer GUI (z. B. app.py / CustomTkinter) aufgerufen
werden.

Beispiel:

    from calculations.stabduebel import StabduebelInput, calculate_stabduebel

    eingabe = StabduebelInput(
        force_ed_kn=140.0,
        width_b_mm=200.0,
        height_h_mm=240.0,
        side_thickness_t1_mm=60.0,
        middle_thickness_t2_mm=68.0,
        plate_thickness_ts_mm=6.0,
        dowel_diameter_d_mm=12.0,
        rows_parallel_n=2,
        rows_perpendicular_m=4,
    )

    ergebnis = calculate_stabduebel(eingabe)
    print(ergebnis.summary_text())

Hinweis:
Die Implementierung bildet die im Referenzbeispiel verwendeten Formeln
nach. Vor einem Einsatz als freigegebene Bemessungssoftware müssen
Normstand, Anwendungsgrenzen, Rundungsregeln und Sonderfälle fachlich
validiert werden.
"""

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Any, Dict, List


# ============================================================
# Eingabe
# ============================================================

@dataclass(slots=True)
class StabduebelInput:
    # Projekt / Beschreibung
    project_name: str = "Zugstoß – 4-schnittiger Stabdübelanschluss"
    timber_grade: str = "GL24h"
    plate_steel_grade: str = "S235"
    dowel_steel_grade: str = "S235"

    # Einwirkung
    force_ed_kn: float = 140.0

    # Gesamtquerschnitt
    width_b_mm: float = 200.0
    height_h_mm: float = 240.0
    side_thickness_t1_mm: float = 60.0
    middle_thickness_t2_mm: float = 68.0

    # Stahlbleche
    number_of_plates_ns: int = 2
    plate_thickness_ts_mm: float = 6.0
    plate_fy_n_mm2: float = 235.0
    plate_fu_n_mm2: float = 360.0
    gamma_m0_steel: float = 1.00
    gamma_m2_steel: float = 1.25

    # Stabdübel
    dowel_diameter_d_mm: float = 12.0
    dowel_length_l_mm: float = 200.0
    dowel_setback_p_mm: float = 0.0
    dowel_fu_k_n_mm2: float = 360.0
    hole_diameter_d0_mm: float = 13.0

    # Anordnung
    rows_parallel_n: int = 2
    rows_perpendicular_m: int = 4
    shear_planes_s: int = 4

    # Abstände Holz
    a1_mm: float = 60.0
    a2_mm: float = 40.0
    a3_t_mm: float = 85.0
    a4_c_mm: float = 60.0

    # Randabstände Stahlblech
    e1_mm: float = 20.0
    e2_mm: float = 20.0

    # Holzkennwerte
    rho_k_kg_m3: float = 385.0
    ft_0_k_n_mm2: float = 19.2
    fv_k_n_mm2: float = 3.5
    k_mod: float = 0.80
    gamma_m_timber: float = 1.30

    # Nettoquerschnitt
    slot_air_per_cut_ts_l_mm: float = 1.0
    kt_e_side: float = 0.40

    # Stahl – Abscheren
    shear_factor_alpha_v: float = 0.60

    # Einhängeeffekt; im Referenzbeispiel 0
    fax_rk_n: float = 0.0


# ============================================================
# Ergebnis-Dataclasses
# ============================================================

@dataclass(slots=True)
class Check:
    name: str
    resistance_kn: float
    utilization: float
    passed: bool


@dataclass(slots=True)
class StabduebelResult:
    input: StabduebelInput
    material: Dict[str, float]
    side_timber: Dict[str, float]
    middle_timber: Dict[str, float]
    steel_tension: Dict[str, float]
    steel_fastener: Dict[str, float]
    steel_block: Dict[str, float]
    timber_fastener: Dict[str, float]
    timber_block: Dict[str, float]
    checks: List[Check]
    governing_check: Check
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": asdict(self.input),
            "material": self.material,
            "side_timber": self.side_timber,
            "middle_timber": self.middle_timber,
            "steel_tension": self.steel_tension,
            "steel_fastener": self.steel_fastener,
            "steel_block": self.steel_block,
            "timber_fastener": self.timber_fastener,
            "timber_block": self.timber_block,
            "checks": [asdict(check) for check in self.checks],
            "governing_check": asdict(self.governing_check),
            "passed": self.passed,
        }

    def summary_text(self) -> str:
        lines = [
            "=" * 72,
            "STABDÜBELNACHWEIS",
            "=" * 72,
            f"Projekt: {self.input.project_name}",
            f"Einwirkung Ft,d: {self.input.force_ed_kn:.2f} kN",
            "",
            "Zusammenstellung:",
        ]

        for check in self.checks:
            status = "ERFÜLLT" if check.passed else "NICHT ERFÜLLT"
            lines.append(
                f"- {check.name:<42} "
                f"Rd = {check.resistance_kn:>8.2f} kN | "
                f"η = {check.utilization:>5.2f} | {status}"
            )

        lines.extend([
            "",
            f"Maßgebend: {self.governing_check.name}",
            f"Ausnutzung: {self.governing_check.utilization:.2f}",
            "GESAMTNACHWEIS: " + ("ERFÜLLT" if self.passed else "NICHT ERFÜLLT"),
            "=" * 72,
        ])
        return "\n".join(lines)


# ============================================================
# Validierung
# ============================================================

def validate_input(data: StabduebelInput) -> None:
    positive_values = {
        "force_ed_kn": data.force_ed_kn,
        "width_b_mm": data.width_b_mm,
        "height_h_mm": data.height_h_mm,
        "side_thickness_t1_mm": data.side_thickness_t1_mm,
        "middle_thickness_t2_mm": data.middle_thickness_t2_mm,
        "plate_thickness_ts_mm": data.plate_thickness_ts_mm,
        "dowel_diameter_d_mm": data.dowel_diameter_d_mm,
        "dowel_length_l_mm": data.dowel_length_l_mm,
        "hole_diameter_d0_mm": data.hole_diameter_d0_mm,
        "rho_k_kg_m3": data.rho_k_kg_m3,
        "ft_0_k_n_mm2": data.ft_0_k_n_mm2,
        "fv_k_n_mm2": data.fv_k_n_mm2,
        "k_mod": data.k_mod,
        "gamma_m_timber": data.gamma_m_timber,
    }

    for name, value in positive_values.items():
        if value <= 0:
            raise ValueError(f"{name} muss größer als 0 sein.")

    if data.rows_parallel_n < 1 or data.rows_perpendicular_m < 1:
        raise ValueError("Die Anzahl der Reihen n und m muss mindestens 1 sein.")

    if data.number_of_plates_ns < 1:
        raise ValueError("Die Anzahl der Stahlbleche muss mindestens 1 sein.")

    if data.shear_planes_s <= 0:
        raise ValueError("Die Schnittigkeit s muss größer als 0 sein.")

    if data.hole_diameter_d0_mm < data.dowel_diameter_d_mm:
        raise ValueError("Der Lochdurchmesser d0 darf nicht kleiner als d sein.")

    remaining_height = (
        data.height_h_mm
        - data.rows_perpendicular_m * data.dowel_diameter_d_mm
    )
    if remaining_height <= 0:
        raise ValueError("h - m·d muss größer als 0 sein.")

    if data.side_thickness_t1_mm <= data.slot_air_per_cut_ts_l_mm:
        raise ValueError("t1 - ts,L muss größer als 0 sein.")

    if (
        data.middle_thickness_t2_mm
        <= 2.0 * data.slot_air_per_cut_ts_l_mm
    ):
        raise ValueError("t2 - 2·ts,L muss größer als 0 sein.")


# ============================================================
# Hilfsfunktionen
# ============================================================

def ratio(demand: float, resistance: float) -> float:
    if resistance <= 0:
        return float("inf")
    return demand / resistance


def make_check(name: str, demand_kn: float, resistance_kn: float) -> Check:
    eta = ratio(demand_kn, resistance_kn)
    return Check(
        name=name,
        resistance_kn=resistance_kn,
        utilization=eta,
        passed=eta <= 1.0,
    )


def effective_number_of_fasteners(
    n: int,
    a1_mm: float,
    d_mm: float,
) -> float:
    """
    n_eff = min[n ; n^0.9 · (a1 / (13·d))^(1/4)]
    """
    calculated = (n ** 0.9) * ((a1_mm / (13.0 * d_mm)) ** 0.25)
    return min(float(n), calculated)


# ============================================================
# Material
# ============================================================

def calculate_material(data: StabduebelInput) -> Dict[str, float]:
    ft_0_d_n_mm2 = (
        data.k_mod
        * data.ft_0_k_n_mm2
        / data.gamma_m_timber
    )

    # Umrechnung N/mm² -> kN/cm²: Faktor 0,1
    ft_0_d_kn_cm2 = ft_0_d_n_mm2 * 0.1

    kh = min(
        (600.0 / max(data.width_b_mm, data.height_h_mm)) ** 0.1,
        1.1,
    )

    fh_0_k_n_mm2 = (
        0.082
        * (1.0 - 0.01 * data.dowel_diameter_d_mm)
        * data.rho_k_kg_m3
    )

    my_rk_nmm = (
        0.30
        * data.dowel_fu_k_n_mm2
        * data.dowel_diameter_d_mm ** 2.6
    )

    return {
        "ft_0_d_n_mm2": ft_0_d_n_mm2,
        "ft_0_d_kn_cm2": ft_0_d_kn_cm2,
        "kh": kh,
        "fh_0_k_n_mm2": fh_0_k_n_mm2,
        "my_rk_nmm": my_rk_nmm,
    }


# ============================================================
# Seitenholz – Zug im Nettoquerschnitt
# ============================================================

def calculate_side_timber(
    data: StabduebelInput,
    material: Dict[str, float],
) -> Dict[str, float]:
    a_net_cm2 = (
        (data.side_thickness_t1_mm - data.slot_air_per_cut_ts_l_mm)
        * (
            data.height_h_mm
            - data.rows_perpendicular_m * data.dowel_diameter_d_mm
        )
        * 1e-2
    )

    sigma_kn_cm2 = (
        (1.0 / data.shear_planes_s)
        * data.force_ed_kn
        / a_net_cm2
    )

    resistance_stress_kn_cm2 = (
        data.kt_e_side
        * material["kh"]
        * material["ft_0_d_kn_cm2"]
    )

    eta = ratio(sigma_kn_cm2, resistance_stress_kn_cm2)

    # Äquivalenter Gesamtwiderstand bezogen auf Ft,d
    resistance_kn = data.force_ed_kn / eta

    return {
        "a_net_cm2": a_net_cm2,
        "a_net_mm2": a_net_cm2 * 100.0,
        "sigma_t_0_d_kn_cm2": sigma_kn_cm2,
        "kt_e": data.kt_e_side,
        "kh": material["kh"],
        "ft_0_d_kn_cm2": material["ft_0_d_kn_cm2"],
        "resistance_stress_kn_cm2": resistance_stress_kn_cm2,
        "resistance_kn": resistance_kn,
        "utilization": eta,
    }


# ============================================================
# Mittelholz – Zug im Nettoquerschnitt
# ============================================================

def calculate_middle_timber(
    data: StabduebelInput,
    material: Dict[str, float],
) -> Dict[str, float]:
    a_net_cm2 = (
        (
            data.middle_thickness_t2_mm
            - 2.0 * data.slot_air_per_cut_ts_l_mm
        )
        * (
            data.height_h_mm
            - data.rows_perpendicular_m * data.dowel_diameter_d_mm
        )
        * 1e-2
    )

    sigma_kn_cm2 = (
        (2.0 / data.shear_planes_s)
        * data.force_ed_kn
        / a_net_cm2
    )

    resistance_stress_kn_cm2 = (
        material["kh"]
        * material["ft_0_d_kn_cm2"]
    )

    eta = ratio(sigma_kn_cm2, resistance_stress_kn_cm2)
    resistance_kn = data.force_ed_kn / eta

    return {
        "a_net_cm2": a_net_cm2,
        "a_net_mm2": a_net_cm2 * 100.0,
        "sigma_t_0_d_kn_cm2": sigma_kn_cm2,
        "kh": material["kh"],
        "ft_0_d_kn_cm2": material["ft_0_d_kn_cm2"],
        "resistance_stress_kn_cm2": resistance_stress_kn_cm2,
        "resistance_kn": resistance_kn,
        "utilization": eta,
    }


# ============================================================
# Stahlblech – Zug im Brutto- und Nettoquerschnitt
# ============================================================

def calculate_steel_tension(data: StabduebelInput) -> Dict[str, float]:
    plate_width_mm = (
        2.0 * data.e2_mm
        + (data.rows_perpendicular_m - 1) * data.a2_mm
    )

    gross_area_mm2 = (
        data.number_of_plates_ns
        * data.plate_thickness_ts_mm
        * plate_width_mm
    )

    net_area_mm2 = (
        data.number_of_plates_ns
        * data.plate_thickness_ts_mm
        * (
            plate_width_mm
            - data.rows_perpendicular_m * data.hole_diameter_d0_mm
        )
    )

    n_pl_rd_kn = (
        gross_area_mm2
        * data.plate_fy_n_mm2
        / data.gamma_m0_steel
        * 1e-3
    )

    n_u_rd_kn = (
        0.9
        * net_area_mm2
        * data.plate_fu_n_mm2
        / data.gamma_m2_steel
        * 1e-3
    )

    resistance_kn = min(n_pl_rd_kn, n_u_rd_kn)

    return {
        "plate_width_mm": plate_width_mm,
        "gross_area_mm2": gross_area_mm2,
        "net_area_mm2": net_area_mm2,
        "n_pl_rd_kn": n_pl_rd_kn,
        "n_u_rd_kn": n_u_rd_kn,
        "resistance_kn": resistance_kn,
        "utilization": ratio(data.force_ed_kn, resistance_kn),
    }


# ============================================================
# Verbindungsmittel im Stahlblech
# ============================================================

def calculate_steel_fastener(data: StabduebelInput) -> Dict[str, float]:
    d = data.dowel_diameter_d_mm
    d0 = data.hole_diameter_d0_mm
    p2 = data.a2_mm

    k1 = min(
        2.8 * data.e2_mm / d0 - 1.7,
        1.4 * p2 / d0 - 1.7,
        2.5,
    )

    alpha_d = data.e1_mm / (3.0 * d0)

    alpha_b = min(
        alpha_d,
        data.dowel_fu_k_n_mm2 / data.plate_fu_n_mm2,
        1.0,
    )

    fb_rd_kn = (
        k1
        * alpha_b
        * data.plate_fu_n_mm2
        * d
        * data.plate_thickness_ts_mm
        / data.gamma_m2_steel
        * 1e-3
    )

    dowel_area_mm2 = pi / 4.0 * d**2

    fv_rd_kn = (
        data.shear_factor_alpha_v
        * data.dowel_fu_k_n_mm2
        * dowel_area_mm2
        / data.gamma_m2_steel
        * 1e-3
    )

    n_eff = effective_number_of_fasteners(
        data.rows_parallel_n,
        data.a1_mm,
        d,
    )

    fv_ed_kn = (
        data.force_ed_kn
        / (
            n_eff
            * data.rows_perpendicular_m
            * data.number_of_plates_ns
        )
    )

    resistance_per_fastener_kn = min(
        fb_rd_kn,
        2.0 * fv_rd_kn,
    )

    eta = ratio(fv_ed_kn, resistance_per_fastener_kn)

    # Gesamtwiderstand, damit dieser Nachweis direkt mit Ft,d
    # verglichen werden kann.
    total_resistance_kn = (
        resistance_per_fastener_kn
        * n_eff
        * data.rows_perpendicular_m
        * data.number_of_plates_ns
    )

    return {
        "k1": k1,
        "alpha_d": alpha_d,
        "alpha_b": alpha_b,
        "dowel_area_mm2": dowel_area_mm2,
        "fb_rd_kn": fb_rd_kn,
        "fv_rd_kn": fv_rd_kn,
        "n_eff": n_eff,
        "fv_ed_kn": fv_ed_kn,
        "resistance_per_fastener_kn": resistance_per_fastener_kn,
        "resistance_kn": total_resistance_kn,
        "utilization": eta,
    }


# ============================================================
# Blockversagen Stahlblech
# ============================================================

def calculate_steel_block(data: StabduebelInput) -> Dict[str, float]:
    ant_mm2 = (
        (data.rows_perpendicular_m - 1)
        * (data.a2_mm - data.hole_diameter_d0_mm)
        * data.plate_thickness_ts_mm
    )

    anv_mm2 = (
        (
            (data.rows_parallel_n - 1)
            * (data.a1_mm - data.hole_diameter_d0_mm)
            + (
                data.e1_mm
                - data.hole_diameter_d0_mm / 2.0
            )
        )
        * data.plate_thickness_ts_mm
        * 2.0
    )

    v_eff_one_plate_rd_kn = (
        (
            data.plate_fu_n_mm2
            * ant_mm2
            / data.gamma_m2_steel
        )
        +
        (
            data.plate_fy_n_mm2
            / sqrt(3.0)
            * anv_mm2
            / data.gamma_m0_steel
        )
    ) * 1e-3

    total_resistance_kn = (
        data.number_of_plates_ns
        * v_eff_one_plate_rd_kn
    )

    return {
        "ant_mm2": ant_mm2,
        "anv_mm2": anv_mm2,
        "v_eff_one_plate_rd_kn": v_eff_one_plate_rd_kn,
        "resistance_kn": total_resistance_kn,
        "utilization": ratio(data.force_ed_kn, total_resistance_kn),
    }


# ============================================================
# Verbindungsmittel im Holz – genaues Verfahren
# ============================================================

def calculate_timber_fastener(
    data: StabduebelInput,
    material: Dict[str, float],
) -> Dict[str, float]:
    d = data.dowel_diameter_d_mm
    t1 = data.side_thickness_t1_mm
    t2 = data.middle_thickness_t2_mm
    ts = data.plate_thickness_ts_mm
    l = data.dowel_length_l_mm
    p = data.dowel_setback_p_mm

    fh = material["fh_0_k_n_mm2"]
    my = material["my_rk_nmm"]
    fax = data.fax_rk_n

    th_1_mm = min(
        t1,
        t1 - p,
        l + p - t1 - 2.0 * ts - t2,
    )
    if th_1_mm <= 0:
        raise ValueError(
            "Die wirksame Seitenholzdicke th,1 ist nicht positiv. "
            "Bitte Dübellänge, Rücksprung und Querschnitt prüfen."
        )

    # Scherfugen I und IV
    mode_f_i_n = fh * th_1_mm * d

    mode_g_i_n = (
        fh
        * th_1_mm
        * d
        * (
            sqrt(
                2.0
                + (
                    4.0 * my
                    / (fh * d * th_1_mm**2)
                )
            )
            - 1.0
        )
        + fax / 4.0
    )

    mode_h_i_n = (
        2.3 * sqrt(my * fh * d)
        + fax / 4.0
    )

    fv_rk_i_n = min(
        mode_f_i_n,
        mode_g_i_n,
        mode_h_i_n,
    )

    # Scherfuge II
    mode_l_ii_n = 0.5 * fh * t2 * d
    mode_m_ii_n = (
        2.3 * sqrt(my * fh * d)
        + fax / 4.0
    )

    fv_rk_ii_n = min(
        mode_l_ii_n,
        mode_m_ii_n,
    )

    # Scherfuge III
    mode_f_iii_n = fh * t2 * d
    mode_h_iii_n = (
        2.3 * sqrt(my * fh * d)
        + fax / 4.0
    )

    fv_rk_iii_n = min(
        mode_f_iii_n,
        mode_h_iii_n,
    )

    fv_rk_one_dowel_n = (
        2.0 * fv_rk_i_n
        + 2.0 * min(fv_rk_ii_n, fv_rk_iii_n)
    )

    n_eff = effective_number_of_fasteners(
        data.rows_parallel_n,
        data.a1_mm,
        d,
    )

    fv_rk_total_kn = (
        n_eff
        * data.rows_perpendicular_m
        * fv_rk_one_dowel_n
        * 1e-3
    )

    fv_rd_kn = (
        data.k_mod
        * fv_rk_total_kn
        / data.gamma_m_timber
    )

    return {
        "th_1_mm": th_1_mm,
        "mode_f_i_n": mode_f_i_n,
        "mode_g_i_n": mode_g_i_n,
        "mode_h_i_n": mode_h_i_n,
        "fv_rk_i_n": fv_rk_i_n,
        "mode_l_ii_n": mode_l_ii_n,
        "mode_m_ii_n": mode_m_ii_n,
        "fv_rk_ii_n": fv_rk_ii_n,
        "mode_f_iii_n": mode_f_iii_n,
        "mode_h_iii_n": mode_h_iii_n,
        "fv_rk_iii_n": fv_rk_iii_n,
        "fv_rk_one_dowel_n": fv_rk_one_dowel_n,
        "n_eff": n_eff,
        "fv_rk_total_kn": fv_rk_total_kn,
        "resistance_kn": fv_rd_kn,
        "utilization": ratio(data.force_ed_kn, fv_rd_kn),
    }


# ============================================================
# Blockscheren im Holz
# ============================================================

def calculate_timber_block(
    data: StabduebelInput,
    material: Dict[str, float],
) -> Dict[str, float]:
    d = data.dowel_diameter_d_mm
    t1 = data.side_thickness_t1_mm
    t2 = data.middle_thickness_t2_mm
    ts_l = data.slot_air_per_cut_ts_l_mm
    s = data.shear_planes_s
    n = data.rows_parallel_n
    m = data.rows_perpendicular_m

    fh = material["fh_0_k_n_mm2"]
    my = material["my_rk_nmm"]

    lv_1_mm = data.a3_t_mm - d / 2.0
    lv_2_mm = data.a1_mm - d
    lt_1_mm = data.a2_mm - d

    l_net_v_mm = (
        2.0 * lv_1_mm
        + 2.0 * (n - 1) * lv_2_mm
    )

    l_net_t_mm = (
        (m - 1) * lt_1_mm
    )

    a_net_t_mm2 = (
        l_net_t_mm
        * (
            2.0 * t1
            + t2
            - s * ts_l
        )
    )

    t_eff_eh_mm = (
        2.0
        * sqrt(my / (fh * d))
    )

    t_eff_dg_mm = (
        t1
        * (
            sqrt(
                2.0
                + 4.0 * my / (fh * d * t1**2)
            )
            - 1.0
        )
    )

    a_net_v_i_f_mm2 = (
        l_net_v_mm
        * (t1 - ts_l)
    )

    a_net_v_i_g_mm2 = (
        l_net_v_mm / 2.0
        * (
            l_net_t_mm
            + 2.0 * t_eff_dg_mm
        )
    )

    a_net_v_i_h_mm2 = (
        l_net_v_mm / 2.0
        * (
            l_net_t_mm
            + 2.0 * t_eff_eh_mm
        )
    )

    a_net_v_i_mm2 = min(
        a_net_v_i_f_mm2,
        a_net_v_i_g_mm2,
        a_net_v_i_h_mm2,
    )

    a_net_v_ii_mm2 = (
        l_net_v_mm
        * (t2 - 2.0 * ts_l)
    )

    a_net_v_iii_f_mm2 = (
        l_net_v_mm
        * (t2 - 2.0 * ts_l)
    )

    a_net_v_iii_h_mm2 = (
        l_net_v_mm / 2.0
        * (
            l_net_t_mm
            + 2.0 * t_eff_eh_mm
        )
    )

    a_net_v_iii_mm2 = min(
        a_net_v_iii_f_mm2,
        a_net_v_iii_h_mm2,
    )

    a_net_v_mm2 = (
        2.0 * a_net_v_i_mm2
        + 2.0 * min(
            a_net_v_ii_mm2,
            a_net_v_iii_mm2,
        )
    )

    tension_model_kn = (
        1.50
        * a_net_t_mm2
        * data.ft_0_k_n_mm2
        * 1e-3
    )

    shear_model_kn = (
        0.70
        * a_net_v_mm2
        * data.fv_k_n_mm2
        * 1e-3
    )

    f_bs_rk_kn = max(
        tension_model_kn,
        shear_model_kn,
    )

    f_bs_rd_kn = (
        data.k_mod
        * f_bs_rk_kn
        / data.gamma_m_timber
    )

    return {
        "lv_1_mm": lv_1_mm,
        "lv_2_mm": lv_2_mm,
        "lt_1_mm": lt_1_mm,
        "l_net_v_mm": l_net_v_mm,
        "l_net_t_mm": l_net_t_mm,
        "a_net_t_mm2": a_net_t_mm2,
        "t_eff_eh_mm": t_eff_eh_mm,
        "t_eff_dg_mm": t_eff_dg_mm,
        "a_net_v_i_f_mm2": a_net_v_i_f_mm2,
        "a_net_v_i_g_mm2": a_net_v_i_g_mm2,
        "a_net_v_i_h_mm2": a_net_v_i_h_mm2,
        "a_net_v_i_mm2": a_net_v_i_mm2,
        "a_net_v_ii_mm2": a_net_v_ii_mm2,
        "a_net_v_iii_f_mm2": a_net_v_iii_f_mm2,
        "a_net_v_iii_h_mm2": a_net_v_iii_h_mm2,
        "a_net_v_iii_mm2": a_net_v_iii_mm2,
        "a_net_v_mm2": a_net_v_mm2,
        "tension_model_kn": tension_model_kn,
        "shear_model_kn": shear_model_kn,
        "f_bs_rk_kn": f_bs_rk_kn,
        "resistance_kn": f_bs_rd_kn,
        "utilization": ratio(data.force_ed_kn, f_bs_rd_kn),
    }


# ============================================================
# Hauptfunktion
# ============================================================

def calculate_stabduebel(data: StabduebelInput) -> StabduebelResult:
    validate_input(data)

    material = calculate_material(data)
    side_timber = calculate_side_timber(data, material)
    middle_timber = calculate_middle_timber(data, material)
    steel_tension = calculate_steel_tension(data)
    steel_fastener = calculate_steel_fastener(data)
    steel_block = calculate_steel_block(data)
    timber_fastener = calculate_timber_fastener(data, material)
    timber_block = calculate_timber_block(data, material)

    checks = [
        make_check(
            "Seitenholz – Nettoquerschnitt",
            data.force_ed_kn,
            side_timber["resistance_kn"],
        ),
        make_check(
            "Mittelholz – Nettoquerschnitt",
            data.force_ed_kn,
            middle_timber["resistance_kn"],
        ),
        make_check(
            "Stahlblech – Zug",
            data.force_ed_kn,
            steel_tension["resistance_kn"],
        ),
        make_check(
            "Verbindungsmittel im Stahlblech",
            data.force_ed_kn,
            steel_fastener["resistance_kn"],
        ),
        make_check(
            "Blockversagen Stahlblech",
            data.force_ed_kn,
            steel_block["resistance_kn"],
        ),
        make_check(
            "Verbindungsmittel im Holz",
            data.force_ed_kn,
            timber_fastener["resistance_kn"],
        ),
        make_check(
            "Blockscheren im Holz",
            data.force_ed_kn,
            timber_block["resistance_kn"],
        ),
    ]

    governing_check = max(checks, key=lambda item: item.utilization)
    passed = all(check.passed for check in checks)

    return StabduebelResult(
        input=data,
        material=material,
        side_timber=side_timber,
        middle_timber=middle_timber,
        steel_tension=steel_tension,
        steel_fastener=steel_fastener,
        steel_block=steel_block,
        timber_fastener=timber_fastener,
        timber_block=timber_block,
        checks=checks,
        governing_check=governing_check,
        passed=passed,
    )


# ============================================================
# Beispiel / Testlauf
# ============================================================

if __name__ == "__main__":
    example = StabduebelInput()
    result = calculate_stabduebel(example)

    print(result.summary_text())

    print("\nReferenzwerte des Beispiels:")
    print(f"A1,netto:       {result.side_timber['a_net_cm2']:.2f} cm²")
    print(f"A2,netto:       {result.middle_timber['a_net_cm2']:.2f} cm²")
    print(f"N_u,Rd Stahl:   {result.steel_tension['n_u_rd_kn']:.2f} kN")
    print(f"F_b,Rd Stahl:   {result.steel_fastener['fb_rd_kn']:.2f} kN")
    print(f"V_eff,1,Rd:     {result.steel_block['v_eff_one_plate_rd_kn']:.2f} kN")
    print(f"F_v,Rd Holz:    {result.timber_fastener['resistance_kn']:.2f} kN")
    print(f"F_bs,Rd Holz:   {result.timber_block['resistance_kn']:.2f} kN")
