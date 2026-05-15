from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.chunking import chunk_documents
from backend.src.document_loader import load_documents
from backend.src.embeddings import HashEmbeddingModel, embed_chunks
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


class RealWorldSimulationTests(unittest.TestCase):
    def test_internal_employee_portal_retrieval_permissions(self) -> None:
        model = HashEmbeddingModel(dimensions=16)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            data_dir = temp_root / "data"
            persist_dir = temp_root / "chroma"

            self._write_document(
                data_dir / "general" / "employee_handbook.md",
                "All employees can use the internal portal to read company tools, "
                "workplace norms, holidays, and general policy announcements.",
            )
            self._write_document(
                data_dir / "hr" / "leave_policy.md",
                "The HR leave policy says employees receive annual leave and sick leave. "
                "Leave requests should be approved by the employee's manager.",
            )
            self._write_document(
                data_dir / "finance" / "budget_report.md",
                "The finance budget report contains restricted revenue forecasts, "
                "department budgets, and confidential planning numbers.",
            )

            documents = load_documents(data_dir)
            chunks = chunk_documents(documents, chunk_size=120, chunk_overlap=20)
            embedded_chunks = embed_chunks(chunks, model)

            store = ChromaVectorStore(persist_dir, collection_name="simulation_documents")
            try:
                store.add_chunks(embedded_chunks)
                retriever = Retriever(store, model)

                employee_results = retriever.retrieve(
                    "What does the finance budget report say about revenue?",
                    role="employee",
                    top_k=5,
                )
                finance_results = retriever.retrieve(
                    "What does the finance budget report say about revenue?",
                    role="finance",
                    top_k=5,
                )
                hr_results = retriever.retrieve(
                    "How does annual leave approval work?",
                    role="employee",
                    top_k=5,
                )
            finally:
                store.close()

        employee_departments = self._departments(employee_results)
        finance_departments = self._departments(finance_results)
        hr_departments = self._departments(hr_results)

        self.assertEqual(len(documents), 3)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(len(embedded_chunks), len(chunks))

        self.assertNotIn("finance", employee_departments)
        self.assertIn("finance", finance_departments)
        self.assertIn("hr", hr_departments)

    def _write_document(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _departments(self, results: list[dict]) -> set[str]:
        return {result["metadata"]["department"] for result in results}


if __name__ == "__main__":
    unittest.main()
