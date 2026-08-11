from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai.assistant import StabduebelAssistant


class AssistantArrangementTests(unittest.TestCase):
    def respond(self, assistant: StabduebelAssistant, prompt: str):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            return assistant.respond(prompt)

    def assert_arrangement(self, reply, n: int, m: int) -> None:
        self.assertIsNotNone(reply.result)
        self.assertEqual(reply.result.input.rows_parallel_n, n)
        self.assertEqual(reply.result.input.rows_perpendicular_m, m)
        self.assertEqual(
            reply.result.input.rows_parallel_n
            * reply.result.input.rows_perpendicular_m,
            n * m,
        )

    def test_four_by_two_is_fixed_exactly(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(assistant, "140 kN, GL24h, 4 × 2 Stabdübel")

        self.assert_arrangement(reply, 4, 2)
        self.assertIn("rows_parallel_n", assistant.state.fixed_parameters)
        self.assertIn("rows_perpendicular_m", assistant.state.fixed_parameters)
        self.assertIn("4 × 2 = 8 Stabdübel", reply.recognized_parameters)

    def test_two_by_four_is_fixed_exactly(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(assistant, "140 kN, GL24h, 2 × 4 Stabdübel")

        self.assert_arrangement(reply, 2, 4)

    def test_follow_up_replaces_existing_arrangement(self) -> None:
        assistant = StabduebelAssistant()
        self.respond(assistant, "140 kN, GL24h, 2 × 4 Stabdübel")
        reply = self.respond(assistant, "ändere auf 4 × 2")

        self.assert_arrangement(reply, 4, 2)
        self.assertEqual(assistant.state.parameters["rows_parallel_n"], 4)
        self.assertEqual(assistant.state.parameters["rows_perpendicular_m"], 2)

    def test_total_without_arrangement_allows_optimizer_to_choose(self) -> None:
        assistant = StabduebelAssistant()
        reply = self.respond(assistant, "140 kN, GL24h, 8 Stabdübel")

        self.assertIsNotNone(reply.result)
        self.assertEqual(
            reply.result.input.rows_parallel_n
            * reply.result.input.rows_perpendicular_m,
            8,
        )
        self.assertNotIn("rows_parallel_n", assistant.state.fixed_parameters)
        self.assertNotIn("rows_perpendicular_m", assistant.state.fixed_parameters)


if __name__ == "__main__":
    unittest.main()
