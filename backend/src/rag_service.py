from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from backend.src.chunking import chunk_documents
from backend.src.document_loader import load_documents
from backend.src.embeddings import EmbeddingModel, create_embedding_model, embed_chunks
from backend.src.rag_chain import LLMClient, RAGChain, create_llm_client
from backend.src.retriever import Retriever
from backend.src.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class RAGServiceSettings:
    data_dir: Path
    persist_dir: Path
    collection_name: str = "api_documents"


@dataclass(frozen=True)
class RAGService:
    rag_chain: RAGChain
    document_count: int
    chunk_count: int
    persist_dir: Path
    collection_name: str


@dataclass(frozen=True)
class RAGIndexStatus:
    document_count: int
    chunk_count: int
    collection_name: str


def default_rag_settings() -> RAGServiceSettings:
    backend_dir = Path(__file__).resolve().parents[1]
    return RAGServiceSettings(
        data_dir=backend_dir / "data",
        persist_dir=Path(tempfile.gettempdir()) / "secure_rag_chroma_api",
    )


def build_rag_service(
    settings: RAGServiceSettings | None = None,
    embedding_model: EmbeddingModel | None = None,
    llm_client: LLMClient | None = None,
) -> RAGService:
    """Build the indexed RAG service used by the API."""

    settings = settings or default_rag_settings()
    embedding_model = embedding_model or create_embedding_model()
    llm_client = llm_client or create_llm_client()

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
    rag_chain = RAGChain(retriever, llm_client)

    return RAGService(
        rag_chain=rag_chain,
        document_count=len(documents),
        chunk_count=len(chunks),
        persist_dir=settings.persist_dir,
        collection_name=settings.collection_name,
    )


def get_index_status(settings: RAGServiceSettings | None = None) -> RAGIndexStatus:
    """Return index counts without initializing embeddings, vector DB, or LLM clients."""

    settings = settings or default_rag_settings()
    documents = load_documents(settings.data_dir)
    chunks = chunk_documents(documents)

    return RAGIndexStatus(
        document_count=len(documents),
        chunk_count=len(chunks),
        collection_name=settings.collection_name,
    )
