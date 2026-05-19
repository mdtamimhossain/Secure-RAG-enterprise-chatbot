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
from backend.src.vector_store import ChromaVectorStore


class VectorStoreTests(unittest.TestCase):
    def test_adds_and_searches_chunks(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="Employees can ask questions about company policies.",
                metadata={
                    "chunk_id": "general-0",
                    "department": "general",
                    "allowed_roles": "employee,hr,finance,manager,executive,admin",
                },
            ),
            DocumentChunk(
                content="Finance reports are restricted to finance leaders.",
                metadata={
                    "chunk_id": "finance-0",
                    "department": "finance",
                    "allowed_roles": "finance,executive,admin",
                },
            ),
        ]
        embedded_chunks = embed_chunks(chunks, model)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_documents")
            try:
                store.add_chunks(embedded_chunks)

                results = store.search("company policy", model, top_k=1)
            finally:
                store.close()

        self.assertEqual(len(results), 1)
        self.assertIn("content", results[0])
        self.assertIn("metadata", results[0])
        self.assertIn("distance", results[0])

    def test_search_can_filter_by_department(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="General handbook for all employees.",
                metadata={"chunk_id": "general-0", "department": "general"},
            ),
            DocumentChunk(
                content="Finance annual budget details.",
                metadata={"chunk_id": "finance-0", "department": "finance"},
            ),
        ]
        embedded_chunks = embed_chunks(chunks, model)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_filtered_documents")
            try:
                store.add_chunks(embedded_chunks)

                results = store.search(
                    "budget",
                    model,
                    top_k=2,
                    where={"department": "finance"},
                )
            finally:
                store.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["department"], "finance")

    def test_keyword_search_scores_content_and_metadata(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="General handbook for employees.",
                metadata={"chunk_id": "general-0", "department": "general", "filename": "handbook.md"},
            ),
            DocumentChunk(
                content="Approved expenses can be reimbursed with receipts.",
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
            store = ChromaVectorStore(temp_dir, collection_name="test_keyword_documents")
            try:
                store.add_chunks(embedded_chunks)

                results = store.keyword_search(
                    "expense reimbursement",
                    top_k=2,
                    where={"department": "finance"},
                )
            finally:
                store.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["department"], "finance")
        self.assertGreater(results[0]["keyword_score"], 0)


if __name__ == "__main__":
    unittest.main()
