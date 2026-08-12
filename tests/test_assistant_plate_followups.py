from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai.assistant import StabduebelAssistant


class AssistantPlateFollowupTests(unittest.TestCase):
    def respond(self, assistant: StabduebelAssistant, prompt: str):
        assistant.state.parameters.setdefault("service_class", 1)
        assistant.state.parameters.setdefault("load_duration_class", "mittel")
        assistant.state.fixed_parameters.update({"service_class", "load_duration_class"})
        assistant.state.parameters.setdefault("width_b_mm", 200.0)
        assistant.state.parameters.setdefault("height_h_mm", 240.0)
        assistant.state.parameters.setdefault("number_of_plates_ns", 2)
        assistant.state.parameters.setdefault("plate_thickness_ts_mm", 6.0)
        assistant.state.parameters.setdefault("side_thickness_t1_mm", 60.0)
        assistant.state.parameters.setdefault("middle_thickness_t2_mm", 68.0)
        assistant.state.parameters.setdefault("slot_air_per_cut_ts_l_mm", 1.0)
        assistant._set_connection_state(int(assistant.state.parameters["number_of_plates_ns"]))
        assistant.state.minimize_fasteners = True
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            return assistant.respond(prompt)

    def assert_one_plate_result(self, assistant, reply) -> None:
        self.assertEqual(assistant.state.parameters["number_of_plates_ns"], 1)
        self.assertIn("number_of_plates_ns", assistant.state.fixed_parameters)
        self.assertIsNotNone(reply.result)
        self.assertEqual(reply.result.input.number_of_plates_ns, 1)
        self.assertTrue(
            all(
                variant.input.number_of_plates_ns == 1
                for variant in assistant.state.last_optimization.evaluated
            )
        )

    def test_followup_with_one_plate_keeps_previous_design_data(self) -> None:
        assistant = StabduebelAssistant()
        self.respond(
            assistant,
            "Bemesse 140 kN mit GL24h und möglichst wenigen Stabdübeln.",
        )
        reply = self.respond(assistant, "jetzt mit einem Stahlblech")

        self.assert_one_plate_result(assistant, reply)
        self.assertEqual(reply.result.input.force_ed_kn, 140.0)
        self.assertEqual(reply.result.input.timber_grade, "GL24h")
        self.assertTrue(assistant.state.minimize_fasteners)

    def test_direct_one_plate_optimization(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(
            assistant,
            "140 kN, GL24h, 1 Stahlblech, möglichst wenige Stabdübel",
        )

        self.assert_one_plate_result(assistant, reply)
        self.assertTrue(assistant.state.minimize_fasteners)

    def test_minimum_question_uses_existing_state(self) -> None:
        assistant = StabduebelAssistant()
        self.respond(assistant, "Bemesse 140 kN mit GL24h.")
        reply = self.respond(
            assistant,
            "Wie viele Stabdübel brauche ich bei einem Stahlblech mindestens?",
        )

        self.assert_one_plate_result(assistant, reply)
        self.assertEqual(reply.result.input.force_ed_kn, 140.0)
        self.assertEqual(reply.result.input.timber_grade, "GL24h")
        self.assertTrue(assistant.state.minimize_fasteners)


if __name__ == "__main__":
    unittest.main()
