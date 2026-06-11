from __future__ import annotations

import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.src.chunking import chunk_documents
from backend.src.document_loader import load_documents
from backend.src.embeddings import EmbeddingModel, create_embedding_model, embed_chunks
from backend.src.rag_chain import (
    ChatHistoryMessage,
    FakeLLM,
    LLMClient,
    RAGResponse,
    build_retrieval_query,
    create_llm_client,
    format_chat_history,
    generate_llm_answer,
    normalize_chat_history,
    parse_source_usage,
)
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class PortfolioRAGSettings:
    data_dir: Path
    persist_dir: Path
    collection_name: str = "portfolio_documents"


@dataclass(frozen=True)
class PortfolioRAGService:
    rag_chain: "PortfolioRAGChain"
    document_count: int
    chunk_count: int
    persist_dir: Path
    collection_name: str


def default_portfolio_settings() -> PortfolioRAGSettings:
    backend_dir = Path(__file__).resolve().parents[1]
    return PortfolioRAGSettings(
        data_dir=backend_dir / "data" / "portfolio",
        persist_dir=Path(tempfile.gettempdir()) / "portfolio_rag_chroma_api",
    )


def build_portfolio_rag_service(
    settings: PortfolioRAGSettings | None = None,
    embedding_model: EmbeddingModel | None = None,
    llm_client: LLMClient | None = None,
) -> PortfolioRAGService:
    settings = settings or default_portfolio_settings()
    embedding_model = embedding_model or create_embedding_model()
    llm_client = llm_client or create_portfolio_llm_client()

    documents = load_documents(settings.data_dir)
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks, embedding_model)

    vector_store = ChromaVectorStore(
        settings.persist_dir,
        collection_name=settings.collection_name,
        reset_collection=True,
    )
    vector_store.add_chunks(embedded_chunks)

    retriever = Retriever(vector_store, embedding_model)
    rag_chain = PortfolioRAGChain(retriever, llm_client)

    return PortfolioRAGService(
        rag_chain=rag_chain,
        document_count=len(documents),
        chunk_count=len(chunks),
        persist_dir=settings.persist_dir,
        collection_name=settings.collection_name,
    )


def create_portfolio_llm_client() -> LLMClient:
    if os.getenv("LLM_PROVIDER", "fake").lower() == "fake":
        return FakeLLM(response="SOURCE_USAGE: context\nI found relevant portfolio context for your question.")

    return create_llm_client()


class PortfolioRAGChain:
    def __init__(self, retriever: Retriever, llm_client: LLMClient) -> None:
        self.retriever = retriever
        self.llm_client = llm_client

    def answer_question(
        self,
        question: str,
        top_k: int = 4,
        chat_history: list[ChatHistoryMessage] | None = None,
    ) -> RAGResponse:
        if not question.strip():
            return RAGResponse(
                answer="Please ask a question about Tamim's work, projects, or skills.",
                sources=[],
                model=self.llm_client.__class__.__name__,
            )

        clean_history = normalize_chat_history(chat_history or [])
        retrieval_query = build_retrieval_query(question, clean_history)
        sources = self.retriever.retrieve(retrieval_query, role="visitor", top_k=top_k)
        prompt = build_portfolio_prompt(
            question=question,
            sources=sources,
            chat_history=clean_history,
        )
        llm_response = generate_llm_answer(prompt, self.llm_client)
        answer, should_show_sources = parse_source_usage(llm_response.answer)

        return RAGResponse(
            answer=answer,
            sources=sources if should_show_sources else [],
            model=llm_response.model,
        )


def build_portfolio_prompt(
    question: str,
    sources: list[dict[str, Any]],
    chat_history: list[ChatHistoryMessage] | None = None,
) -> str:
    context_blocks = []
    for index, source in enumerate(sources, start=1):
        metadata = source.get("metadata", {})
        filename = metadata.get("filename", "unknown")
        category = metadata.get("category", "unknown")
        content = source.get("content", "")
        context_blocks.append(
            f"Source {index} | category={category} | file={filename}\n{content}"
        )

    context = "\n\n".join(context_blocks) if context_blocks else "No retrieved context."
    conversation = format_chat_history(chat_history or [])
    return (
        "You are the public portfolio assistant for Md Tamim Hossain.\n\n"
        "Response rules:\n"
        "1. If the visitor greets you or makes casual conversation, respond naturally and briefly.\n"
        "2. If the visitor asks about Tamim, answer only from the retrieved portfolio context.\n"
        "3. Do not invent employment history, education, certifications, achievements, or private details.\n"
        "4. If the retrieved context does not contain the answer, say: "
        "\"I could not find that in Tamim's portfolio data.\"\n"
        "5. Keep answers helpful, professional, and recruiter-friendly.\n"
        "6. Do not expose private contact data. Share only public profile links listed in the context.\n\n"
        "Source display rule:\n"
        "Start your answer with exactly one hidden routing line:\n"
        "- SOURCE_USAGE: casual  -> for greetings, thanks, or casual conversation\n"
        "- SOURCE_USAGE: context -> when your answer uses retrieved portfolio context\n"
        "- SOURCE_USAGE: none    -> when the visitor asks about Tamim but the context does not contain the answer\n"
        "After that first line, write the visitor-facing answer.\n\n"
        f"Previous conversation:\n{conversation}\n\n"
        f"Retrieved portfolio context:\n{context}\n\n"
        f"Visitor message:\n{question}\n\n"
        "Answer:"
    )
