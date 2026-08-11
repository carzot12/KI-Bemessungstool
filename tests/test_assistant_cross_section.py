from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai.assistant import StabduebelAssistant


class AssistantCrossSectionTests(unittest.TestCase):
    def respond(self, assistant: StabduebelAssistant, prompt: str):
        assistant.state.parameters.setdefault("service_class", 1)
        assistant.state.parameters.setdefault("load_duration_class", "mittel")
        assistant.state.fixed_parameters.update({"service_class", "load_duration_class"})
        assistant.state.parameters.setdefault("width_b_mm", 200.0)
        assistant.state.parameters.setdefault("height_h_mm", 240.0)
        assistant.state.parameters.setdefault("number_of_plates_ns", 2)
        assistant.state.parameters.setdefault("plate_thickness_ts_mm", 6.0)
        assistant._set_connection_state(int(assistant.state.parameters["number_of_plates_ns"]))
        assistant.state.minimize_fasteners = True
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            return assistant.respond(prompt)

    def assert_section(self, assistant, reply, width: float, height: float) -> None:
        self.assertIsNotNone(reply.result)
        self.assertEqual(reply.result.input.width_b_mm, width)
        self.assertEqual(reply.result.input.height_h_mm, height)
        self.assertEqual(assistant.state.parameters["width_b_mm"], width)
        self.assertEqual(assistant.state.parameters["height_h_mm"], height)
        self.assertIn("width_b_mm", assistant.state.fixed_parameters)
        self.assertIn("height_h_mm", assistant.state.fixed_parameters)

    def test_full_prompt_with_section_and_one_plate(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(
            assistant,
            "140 kN, GL24h, Querschnitt 200 × 240 mm, "
            "1 Stahlblech, möglichst wenige Stabdübel",
        )

        self.assert_section(assistant, reply, 200.0, 240.0)
        self.assertEqual(reply.result.input.number_of_plates_ns, 1)
        self.assertIn("Querschnitt: 200 × 240 mm", reply.recognized_parameters)

    def test_followup_changes_only_section(self) -> None:
        assistant = StabduebelAssistant()
        self.respond(
            assistant,
            "140 kN, GL24h, Querschnitt 200 × 240 mm, "
            "1 Stahlblech, möglichst wenige Stabdübel",
        )
        reply = self.respond(assistant, "jetzt mit 160 × 240 mm")

        self.assert_section(assistant, reply, 160.0, 240.0)
        self.assertEqual(reply.result.input.force_ed_kn, 140.0)
        self.assertEqual(reply.result.input.timber_grade, "GL24h")
        self.assertEqual(reply.result.input.number_of_plates_ns, 1)
        self.assertTrue(assistant.state.minimize_fasteners)

    def test_centimetres_are_converted_to_millimetres(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(
            assistant,
            "140 kN, GL24h, Querschnitt 20 × 24 cm",
        )

        self.assert_section(assistant, reply, 200.0, 240.0)

    def test_named_b_and_h_are_recognized(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(
            assistant,
            "140 kN, GL24h, b = 200 mm, h = 240 mm",
        )

        self.assert_section(assistant, reply, 200.0, 240.0)


if __name__ == "__main__":
    unittest.main()
