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
from backend.src.rag_chain import (
    FakeLLM,
    GroqLLM,
    OpenAILLM,
    RAGChain,
    create_llm_client,
    generate_llm_answer,
)
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


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

    def test_openai_llm_requires_api_key(self) -> None:
        with self.assertRaises(ValueError):
            OpenAILLM(api_key="")

    def test_create_llm_client_uses_fake_provider(self) -> None:
        llm = create_llm_client(provider="fake")

        self.assertIsInstance(llm, FakeLLM)

    def test_rag_chain_retrieves_context_and_calls_llm(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="Employees can read the internal company handbook.",
                metadata={
                    "chunk_id": "general-0",
                    "department": "general",
                    "filename": "handbook.md",
                },
            )
        ]
        embedded_chunks = embed_chunks(chunks, model)
        llm = FakeLLM(response="Employees can read the internal company handbook.")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_rag_chain")
            try:
                store.add_chunks(embedded_chunks)
                retriever = Retriever(store, model)
                rag_chain = RAGChain(retriever, llm)

                response = rag_chain.answer_question(
                    "What can employees read?",
                    role="employee",
                    top_k=1,
                )
            finally:
                store.close()

        self.assertEqual(response.answer, "Employees can read the internal company handbook.")
        self.assertEqual(response.model, "FakeLLM")
        self.assertEqual(len(response.sources), 1)
        self.assertIn("internal company handbook", llm.last_prompt)

    def test_rag_chain_blocks_when_no_allowed_sources_exist(self) -> None:
        model = HashEmbeddingModel(dimensions=8)
        chunks = [
            DocumentChunk(
                content="Finance budget details are restricted.",
                metadata={
                    "chunk_id": "finance-0",
                    "department": "finance",
                    "filename": "budget.md",
                },
            )
        ]
        embedded_chunks = embed_chunks(chunks, model)
        llm = FakeLLM()

        with tempfile.TemporaryDirectory() as temp_dir:
            store = ChromaVectorStore(temp_dir, collection_name="test_rag_chain_no_sources")
            try:
                store.add_chunks(embedded_chunks)
                retriever = Retriever(store, model)
                rag_chain = RAGChain(retriever, llm)

                response = rag_chain.answer_question(
                    "What is in the finance budget?",
                    role="employee",
                    top_k=1,
                )
            finally:
                store.close()

        self.assertEqual(
            response.answer,
            "I could not find relevant information you are allowed to access.",
        )
        self.assertEqual(response.sources, [])
        self.assertEqual(llm.last_prompt, "")


if __name__ == "__main__":
    unittest.main()
