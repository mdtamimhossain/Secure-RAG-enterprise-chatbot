from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_service import RAGServiceSettings, build_rag_service, get_index_status


class RAGServiceTests(unittest.TestCase):
    def test_get_index_status_does_not_build_llm_or_vector_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            doc_path = data_dir / "general" / "handbook.md"
            doc_path.parent.mkdir(parents=True)
            doc_path.write_text("Employees can read company policies.", encoding="utf-8")

            status = get_index_status(
                RAGServiceSettings(
                    data_dir=data_dir,
                    persist_dir=root / "unused",
                    collection_name="test_status_only",
                )
            )

        self.assertEqual(status.document_count, 1)
        self.assertEqual(status.chunk_count, 1)
        self.assertEqual(status.collection_name, "test_status_only")

    def test_build_rag_service_indexes_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            persist_dir = root / "chroma"
            doc_path = data_dir / "general" / "handbook.md"
            doc_path.parent.mkdir(parents=True)
            doc_path.write_text("Employees can read company policies.", encoding="utf-8")

            service = build_rag_service(
                RAGServiceSettings(
                    data_dir=data_dir,
                    persist_dir=persist_dir,
                    collection_name="test_service_documents",
                )
            )
            try:
                response = service.rag_chain.answer_question(
                    "What can employees read?",
                    role="employee",
                    top_k=1,
                )
            finally:
                service.rag_chain.retriever.vector_store.close()

        self.assertEqual(service.document_count, 1)
        self.assertEqual(service.chunk_count, 1)
        self.assertEqual(service.collection_name, "test_service_documents")
        self.assertEqual(response.model, "FakeLLM")
        self.assertEqual(len(response.sources), 1)


if __name__ == "__main__":
    unittest.main()
