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
    ChatHistoryMessage,
    FakeLLM,
    GroqLLM,
    OpenAILLM,
    RAGChain,
    build_rag_prompt,
    build_retrieval_query,
    create_llm_client,
    generate_llm_answer,
    parse_source_usage,
)
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


class EmptyRetriever:
    def retrieve(self, question: str, role: str, top_k: int):
        return []


class RecordingRetriever:
    def __init__(self) -> None:
        self.last_question = ""

    def retrieve(self, question: str, role: str, top_k: int):
        self.last_question = question
        return []


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

    def test_prompt_tells_llm_to_handle_casual_chat(self) -> None:
        prompt = build_rag_prompt("Hi", sources=[])

        self.assertIn("casual conversation", prompt)
        self.assertIn("Do not mention missing documents for casual chat", prompt)
        self.assertIn("SOURCE_USAGE: casual", prompt)
        self.assertIn("No retrieved context.", prompt)

    def test_prompt_tells_llm_to_use_context_for_company_questions(self) -> None:
        prompt = build_rag_prompt("What is the leave policy?", sources=[])

        self.assertIn("answer only using", prompt)
        self.assertIn("SOURCE_USAGE: context", prompt)
        self.assertIn("I could not find specific information", prompt)

    def test_prompt_includes_previous_conversation_for_followups(self) -> None:
        prompt = build_rag_prompt(
            "yes",
            sources=[],
            chat_history=[
                ChatHistoryMessage(role="user", content="Can you explain remote work?"),
                ChatHistoryMessage(role="assistant", content="Do you want a shorter version?"),
            ],
        )

        self.assertIn("Previous conversation:", prompt)
        self.assertIn("User: Can you explain remote work?", prompt)
        self.assertIn("Assistant: Do you want a shorter version?", prompt)
        self.assertIn("User message:\nyes", prompt)

    def test_retrieval_query_uses_recent_user_context(self) -> None:
        query = build_retrieval_query(
            "yes",
            [
                ChatHistoryMessage(role="user", content="What is the remote work policy?"),
                ChatHistoryMessage(role="assistant", content="Do you want more detail?"),
            ],
        )

        self.assertIn("What is the remote work policy?", query)
        self.assertIn("yes", query)

    def test_retrieval_query_uses_assistant_context_for_followups(self) -> None:
        query = build_retrieval_query(
            "What about carry-over?",
            [
                ChatHistoryMessage(role="user", content="What is the leave policy?"),
                ChatHistoryMessage(
                    role="assistant",
                    content="Employees receive vacation days, sick leave, and carry-over rules.",
                ),
            ],
        )

        self.assertIn("What is the leave policy?", query)
        self.assertIn("carry-over rules", query)
        self.assertIn("What about carry-over?", query)

    def test_retrieval_query_ignores_history_for_new_topic(self) -> None:
        query = build_retrieval_query(
            "How do I reset my password?",
            [
                ChatHistoryMessage(role="user", content="What is the leave policy?"),
                ChatHistoryMessage(role="assistant", content="Employees receive vacation days."),
            ],
        )

        self.assertEqual(query, "How do I reset my password?")

    def test_parse_source_usage_hides_sources_for_casual_answer(self) -> None:
        answer, show_sources = parse_source_usage("SOURCE_USAGE: casual\nHello there.")

        self.assertEqual(answer, "Hello there.")
        self.assertFalse(show_sources)

    def test_parse_source_usage_shows_sources_for_context_answer(self) -> None:
        answer, show_sources = parse_source_usage("SOURCE_USAGE: context\nEmployees get benefits.")

        self.assertEqual(answer, "Employees get benefits.")
        self.assertTrue(show_sources)

    def test_rag_chain_sends_greeting_and_empty_context_to_llm(self) -> None:
        llm = FakeLLM(response="SOURCE_USAGE: casual\nHi. How can I help?")
        rag_chain = RAGChain(EmptyRetriever(), llm)

        response = rag_chain.answer_question("hello", role="employee")

        self.assertEqual(response.answer, "Hi. How can I help?")
        self.assertEqual(response.sources, [])
        self.assertEqual(response.model, "FakeLLM")
        self.assertIn("User message:\nhello", llm.last_prompt)
        self.assertIn("No retrieved context.", llm.last_prompt)

    def test_rag_chain_passes_history_to_prompt_and_retrieval(self) -> None:
        retriever = RecordingRetriever()
        llm = FakeLLM(response="SOURCE_USAGE: casual\nSure, I can explain that more simply.")
        rag_chain = RAGChain(retriever, llm)

        response = rag_chain.answer_question(
            "yes",
            role="employee",
            chat_history=[
                ChatHistoryMessage(role="user", content="Can you explain the helpdesk policy?"),
                ChatHistoryMessage(role="assistant", content="Do you want a simple summary?"),
            ],
        )

        self.assertEqual(response.answer, "Sure, I can explain that more simply.")
        self.assertIn("Can you explain the helpdesk policy?", retriever.last_question)
        self.assertIn("Previous conversation:", llm.last_prompt)

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
        llm = FakeLLM(response="SOURCE_USAGE: context\nEmployees can read the internal company handbook.")

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
        llm = FakeLLM(
            response=(
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )
        )

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
            "I could not find specific information about that in your available company documents.",
        )
        self.assertEqual(response.sources, [])
        self.assertIn("No retrieved context.", llm.last_prompt)


if __name__ == "__main__":
    unittest.main()
