import pytest

from calculations.stabduebel import StabduebelInput, calculate_stabduebel


def test_140_kn_reference_calculation_is_stable() -> None:
    result = calculate_stabduebel(StabduebelInput())

    assert result.side_timber["a_net_cm2"] == pytest.approx(113.28, rel=1e-9)
    assert result.middle_timber["a_net_cm2"] == pytest.approx(126.72, rel=1e-9)
    assert result.material["fh_0_k_n_mm2"] == pytest.approx(27.7816, rel=1e-6)
    assert result.material["my_rk_nmm"] == pytest.approx(69070.88096, rel=1e-6)

    expected = {
        "Seitenholz – Nettoquerschnitt": (234.70108, 0.596503),
        "Mittelholz – Nettoquerschnitt": (328.183713, 0.426590),
        "Stahlblech – Zug": (335.9232, 0.416762),
        "Verbindungsmittel im Stahlblech": (312.538863, 0.447944),
        "Blockversagen Stahlblech": (476.939459, 0.293538),
        "Verbindungsmittel im Holz": (151.248066, 0.925632),
        "Blockscheren im Holz": (273.927877, 0.511083),
    }
    assert len(result.checks) == 7
    for check in result.checks:
        resistance, utilization = expected[check.name]
        assert check.resistance_kn == pytest.approx(resistance, rel=1e-6)
        assert check.utilization == pytest.approx(utilization, abs=1e-6)
        assert check.passed

    assert result.governing_check.name == "Verbindungsmittel im Holz"
    assert result.governing_check.utilization == pytest.approx(0.925632, rel=1e-6)
    assert result.passed
