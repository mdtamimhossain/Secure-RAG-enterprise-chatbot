from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.chunking import DocumentChunk
from backend.src.embeddings import HashEmbeddingModel, embed_chunks
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


class RetrieverTests(unittest.TestCase):
    def test_retriever_applies_role_department_filter(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="General company handbook.",
                metadata={"chunk_id": "general-0", "department": "general"},
            ),
            DocumentChunk(
                content="Finance budget and revenue plan.",
                metadata={"chunk_id": "finance-0", "department": "finance"},
            ),
        ]
        embedded_chunks = embed_chunks(chunks, model)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_retriever")
            try:
                store.add_chunks(embedded_chunks)
                retriever = Retriever(store, model)

                employee_results = retriever.retrieve("budget revenue", role="employee", top_k=5)
                finance_results = retriever.retrieve("budget revenue", role="finance", top_k=5)
            finally:
                store.close()

        employee_departments = {result["metadata"]["department"] for result in employee_results}
        finance_departments = {result["metadata"]["department"] for result in finance_results}

        self.assertNotIn("finance", employee_departments)
        self.assertIn("finance", finance_departments)

    def test_empty_query_returns_no_results(self) -> None:
        model = HashEmbeddingModel()

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_empty_query")
            try:
                retriever = Retriever(store, model)
                results = retriever.retrieve("   ", role="employee")
            finally:
                store.close()

        self.assertEqual(results, [])

    def test_hybrid_retrieval_uses_keyword_match_with_rbac(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="General workplace norms and tools.",
                metadata={"chunk_id": "general-0", "department": "general", "filename": "handbook.md"},
            ),
            DocumentChunk(
                content="Approved expenses can be reimbursed with receipts and manager approval.",
                metadata={
                    "chunk_id": "finance-0",
                    "department": "finance",
                    "filename": "codemars_finance_expense_reimbursement_policy.md",
                    "category": "expense_policy",
                },
            ),
        ]
        embedded_chunks = embed_chunks(chunks, model)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_hybrid_retriever")
            try:
                store.add_chunks(embedded_chunks)
                retriever = Retriever(store, model)

                employee_results = retriever.retrieve(
                    "What expenses can be reimbursed?",
                    role="employee",
                    top_k=3,
                )
                finance_results = retriever.retrieve(
                    "What expenses can be reimbursed?",
                    role="finance",
                    top_k=3,
                )
            finally:
                store.close()

        employee_departments = {result["metadata"]["department"] for result in employee_results}
        finance_departments = {result["metadata"]["department"] for result in finance_results}

        self.assertNotIn("finance", employee_departments)
        self.assertIn("finance", finance_departments)


if __name__ == "__main__":
    unittest.main()
