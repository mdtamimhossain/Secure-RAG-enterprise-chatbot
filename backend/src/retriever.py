from __future__ import annotations

from typing import Any

from backend.src.embeddings import EmbeddingModel
from backend.src.rbac import build_department_filter
from backend.src.vector_store import ChromaVectorStore


class Retriever:
    """Role-aware retrieval layer for company document chunks."""

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_model: EmbeddingModel,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(
        self,
        query: str,
        role: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        where_filter = build_department_filter(role)
        return self.vector_store.search(
            query=query,
            embedding_model=self.embedding_model,
            top_k=top_k,
            where=where_filter,
        )
