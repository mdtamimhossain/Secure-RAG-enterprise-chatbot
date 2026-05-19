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
        vector_results = self.vector_store.search(
            query=query,
            embedding_model=self.embedding_model,
            top_k=top_k,
            where=where_filter,
        )
        keyword_results = self.vector_store.keyword_search(
            query=query,
            top_k=top_k,
            where=where_filter,
        )
        return merge_retrieval_results(vector_results, keyword_results, top_k=top_k)


def merge_retrieval_results(
    vector_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for result in keyword_results + vector_results:
        result_id = result.get("id")
        if not result_id or result_id in seen_ids:
            continue
        seen_ids.add(result_id)
        merged.append(result)
        if len(merged) == top_k:
            break

    return merged
