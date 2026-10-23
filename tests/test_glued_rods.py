from dataclasses import replace

import pytest

from calculations.glued_rods import (
    GluedRodCalculator,
    generate_glued_rod_variants,
    koerberl_gl24h_reference_input,
)


def test_koerberl_gl24h_reference_resistance() -> None:
    result = GluedRodCalculator().calculate(koerberl_gl24h_reference_input())

    assert result.geometry.net_timber_area_mm2 == pytest.approx(6019.8672889, rel=1e-9)
    assert result.adhesive_strength_n_mm2 == pytest.approx(2.0)
    assert result.governing_check.name == "Holzversagen am Stabende / Nettoquerschnitt"
    assert result.governing_check.rd_kn == pytest.approx(83.2186455, rel=1e-7)
    assert result.governing_check.rd_kn == pytest.approx(83.2, abs=0.05)
    assert result.passed


def test_invalid_hole_geometry_is_rejected() -> None:
    data = replace(koerberl_gl24h_reference_input(), hole_diameter_mm=8.0)
    with pytest.raises(ValueError, match="Bohrlochdurchmesser"):
        GluedRodCalculator().calculate(data)


def test_minimum_spacing_is_enforced_and_boundary_is_allowed() -> None:
    base = koerberl_gl24h_reference_input()
    assert GluedRodCalculator().calculate(base).geometry.minimum_spacing_a2_mm == 40.0
    with pytest.raises(ValueError, match="unterschreitet 5·d"):
        GluedRodCalculator().calculate(replace(base, spacing_a2_mm=39.99))


def test_minimum_edge_distance_is_enforced_and_boundary_is_allowed() -> None:
    base = koerberl_gl24h_reference_input()
    assert GluedRodCalculator().calculate(base).geometry.minimum_edge_a4_c_mm == 20.0
    with pytest.raises(ValueError, match="unterschreitet 2,5·d"):
        GluedRodCalculator().calculate(replace(base, edge_a4_c_mm=19.99))


def test_minimum_embedment_boundary() -> None:
    base = replace(
        koerberl_gl24h_reference_input(),
        effective_embedment_mm=80.0,
        force_ed_kn=1.0,
    )
    assert GluedRodCalculator().calculate(base).geometry.minimum_embedment_mm == 80.0
    with pytest.raises(ValueError, match="Einklebelänge"):
        GluedRodCalculator().calculate(replace(base, effective_embedment_mm=79.99))


def test_steel_failure_can_govern() -> None:
    data = replace(
        koerberl_gl24h_reference_input(force_ed_kn=120.0),
        timber_tension_strength_n_mm2=55.0,
        gamma_m_timber=1.0,
        rod_yield_strength_n_mm2=900.0,
        rod_grade="10.9",
    )
    result = GluedRodCalculator().calculate(data)
    assert result.governing_check.name == "Stahlversagen der Gewindestangen"
    assert result.governing_check.rd_kn == pytest.approx(131.76)
    assert result.passed


def test_bond_failure_can_govern() -> None:
    data = replace(
        koerberl_gl24h_reference_input(force_ed_kn=10.0),
        effective_embedment_mm=80.0,
        tensile_stress_area_mm2=200.0,
        timber_tension_strength_n_mm2=100.0,
    )
    result = GluedRodCalculator().calculate(data)
    assert result.governing_check.name == "Klebfugen-/Holzversagen entlang der Bohrlochwandung"


def test_variant_generator_only_uses_explicit_candidates() -> None:
    base = koerberl_gl24h_reference_input(force_ed_kn=50.0)
    variants = generate_glued_rod_variants(
        base,
        (
            {"rod_yield_strength_n_mm2": 900.0, "rod_grade": "10.9"},
            {"spacing_a2_mm": 39.0},
        ),
    )
    assert len(variants) == 1
    assert variants[0].input.rod_grade == "10.9"


def test_unqualified_adhesive_system_is_rejected() -> None:
    data = replace(koerberl_gl24h_reference_input(), adhesive_system_qualified=False)
    with pytest.raises(ValueError, match="Eignung des Klebersystems"):
        GluedRodCalculator().calculate(data)


def test_application_limits_are_enforced() -> None:
    base = koerberl_gl24h_reference_input()
    with pytest.raises(ValueError, match="6 mm bis 30 mm"):
        GluedRodCalculator().calculate(replace(base, rod_diameter_mm=5.0))
    with pytest.raises(ValueError, match="Nutzungsklasse 1 oder 2"):
        GluedRodCalculator().calculate(replace(base, service_class=3))
    with pytest.raises(ValueError, match="Brettschicht- und Balkenschichtholz"):
        GluedRodCalculator().calculate(replace(base, timber_product="solid_timber"))
