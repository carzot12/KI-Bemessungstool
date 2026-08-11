from __future__ import annotations

import unittest

from calculations.stabduebel import StabduebelInput, calculate_stabduebel
from infopol.materials import TimberMaterialRepository


class TimberMaterialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TimberMaterialRepository()

    def test_lists_solid_timber_and_glulam(self) -> None:
        grades = self.repository.grades()
        self.assertIn("C24", grades)
        self.assertIn("GL24c", grades)
        self.assertIn("GL24h", grades)

    def test_gl24h_drives_existing_stabduebel_calculation(self) -> None:
        material = self.repository.get("GL24h")
        data = StabduebelInput(
            timber_grade=material.grade,
            rho_k_kg_m3=material.value("rho_k"),
            ft_0_k_n_mm2=material.value("ft_0_k"),
            fv_k_n_mm2=material.value("fv_k"),
        )

        result = calculate_stabduebel(data)

        self.assertEqual(result.input.timber_grade, "GL24h")
        self.assertEqual(result.input.rho_k_kg_m3, 385.0)
        self.assertEqual(result.input.ft_0_k_n_mm2, 19.2)
        self.assertEqual(result.input.fv_k_n_mm2, 3.5)
        self.assertGreater(result.governing_check.resistance_kn, 0.0)
        self.assertEqual(len(result.checks), 7)


if __name__ == "__main__":
    unittest.main()
