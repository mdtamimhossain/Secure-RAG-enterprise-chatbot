from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_chain import FakeLLM, GroqLLM, generate_llm_answer


class RagChainTests(unittest.TestCase):
    def test_fake_llm_returns_test_answer(self) -> None:
        llm = FakeLLM(response="Employees can read the company handbook.")

        response = generate_llm_answer("What can employees read?", llm)

        self.assertEqual(response.answer, "Employees can read the company handbook.")
        self.assertEqual(response.model, "FakeLLM")

    def test_fake_llm_handles_empty_prompt(self) -> None:
        llm = FakeLLM()

        response = generate_llm_answer("   ", llm)

        self.assertEqual(response.answer, "I need a question before I can answer.")

    def test_groq_llm_requires_api_key(self) -> None:
        with self.assertRaises(ValueError):
            GroqLLM(api_key="")


if __name__ == "__main__":
    unittest.main()
