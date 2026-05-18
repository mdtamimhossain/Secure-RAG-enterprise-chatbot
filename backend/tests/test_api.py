from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from fastapi.testclient import TestClient

from backend.main import app, get_rag_service


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        get_rag_service.cache_clear()
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_status_endpoint_returns_index_details(self) -> None:
        response = self.client.get("/status")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertGreaterEqual(body["document_count"], 1)
        self.assertGreaterEqual(body["chunk_count"], 1)
        self.assertEqual(body["collection_name"], "api_documents")

    def test_chat_endpoint_returns_answer(self) -> None:
        response = self.client.post(
            "/chat",
            json={
                "question": "What can employees read?",
                "role": "employee",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("answer", body)
        self.assertEqual(body["role"], "employee")
        self.assertIn("sources", body)


if __name__ == "__main__":
    unittest.main()
