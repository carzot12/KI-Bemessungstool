from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ai.assistant import StabduebelAssistant
from calculations.oenorm_validation import validate_oenorm
from calculations.stabduebel import (
    StabduebelInput,
    calculate_material,
    calculate_timber_fastener,
    effective_number_of_fasteners,
)
from infopol.materials import TimberMaterialRepository, get_kmod
from knowledge.sources import IHBV_ZUGLASCHENSTOSS_2022, find_sources


def test_ihbv_holz_holz_reference_confirms_shared_calculation_values() -> None:
    """IV.2.1.1 kontrolliert gemeinsame Größen, nicht den Stahlblechaufbau."""
    reference = IHBV_ZUGLASCHENSTOSS_2022
    data = StabduebelInput(
        width_b_mm=100.0,
        height_h_mm=160.0,
        dowel_diameter_d_mm=reference["dowel_diameter_mm"],
        rho_k_kg_m3=reference["rho_k_kg_m3"],
        ft_0_k_n_mm2=reference["ft_0_k_n_mm2"],
        k_mod=reference["k_mod"],
        gamma_m_timber=reference["gamma_m"],
    )
    material = calculate_material(data)

    assert reference["implemented_connection"] is False
    assert material["ft_0_d_n_mm2"] == pytest.approx(8.92, abs=0.01)
    assert material["fh_0_k_n_mm2"] == pytest.approx(25.3, abs=0.05)
    assert material["my_rk_nmm"] == pytest.approx(6.91e4, rel=5e-4)
    assert effective_number_of_fasteners(5, 60.0, 12.0) == pytest.approx(3.35, abs=0.01)


def test_ihbv_reference_minimum_distances_match_validator() -> None:
    reference = IHBV_ZUGLASCHENSTOSS_2022
    spacings = reference["spacings_mm"]
    data = StabduebelInput(
        dowel_diameter_d_mm=12.0,
        a1_mm=spacings["a1"],
        a2_mm=spacings["a2"],
        a3_t_mm=spacings["a3_t"],
        a4_c_mm=spacings["a4_c"],
    )
    checks = {check.name: check for check in validate_oenorm(data).checks}

    assert checks["Achsabstand a1"].required == 60.0
    assert checks["Achsabstand a2"].required == 36.0
    assert checks["Beanspruchter Endabstand a3,t"].required == 84.0
    assert checks["Unbeanspruchter Randabstand a4,c"].required == 36.0
    assert all(checks[name].passed for name in (
        "Achsabstand a1", "Achsabstand a2",
        "Beanspruchter Endabstand a3,t", "Unbeanspruchter Randabstand a4,c",
    ))


def test_ihbv_table_v29_confirms_one_plate_johansen_value() -> None:
    data = StabduebelInput(
        number_of_plates_ns=1,
        width_b_mm=238.0,
        side_thickness_t1_mm=116.5,
        plate_thickness_ts_mm=5.0,
        dowel_diameter_d_mm=12.0,
        rho_k_kg_m3=350.0,
        rows_parallel_n=1,
        rows_perpendicular_m=1,
    )
    material = calculate_material(data)
    resistance = calculate_timber_fastener(data, material)

    assert material["fh_0_k_n_mm2"] == pytest.approx(25.3, abs=0.05)
    assert material["my_rk_nmm"] == pytest.approx(69070.0, rel=5e-4)
    assert resistance["mode_h_n"] * 1e-3 == pytest.approx(10.5, abs=0.05)
    assert resistance["fv_rk_per_shear_plane_n"] * 1e-3 == pytest.approx(10.5, abs=0.05)


def test_ihbv_kmod_control_and_source_index() -> None:
    material = TimberMaterialRepository().get("C24")
    assert get_kmod(material, 2, "mittel") == 0.80
    assert any(item.reference == "Tabelle III.5" for item in find_sources("kmod"))
    assert any(item.reference == "Tabelle V.8" for item in find_sources("lochleibungsfestigkeit"))
    assert any(item.reference == "Tabelle V.14" for item in find_sources("fließmoment"))
    assert any(item.reference == "Tabelle V.34" for item in find_sources("n_eff"))


def test_assistant_cites_ihbv_and_refuses_out_of_scope_design() -> None:
    assistant = StabduebelAssistant()
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        source_answer = assistant.respond("Gibt es dazu ein Beispiel in der IHBV-Sammlung?")
        refusal = assistant.respond("Bemesse mir einen Biegeträger.")

    assert "IV.2.1.1" in source_answer.text
    assert "Holz-Holz" in source_answer.text
    assert "ausschließlich" in refusal.text
    assert assistant.state.last_result is None
    assert assistant.state.last_optimization is None
