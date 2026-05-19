from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.src.embeddings import EmbeddedChunk, EmbeddingModel


DEFAULT_COLLECTION_NAME = "company_documents"


class ChromaVectorStore:
    """Small ChromaDB wrapper for storing and searching embedded chunks."""

    def __init__(
        self,
        persist_dir: str | Path,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        reset_collection: bool = False,
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is required for vector storage. Install it with: pip install chromadb"
            ) from exc

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))

        if reset_collection:
            try:
                self.client.delete_collection(name=collection_name)
            except Exception:
                pass

        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        if not chunks:
            return

        self.collection.upsert(
            ids=[chunk.metadata["chunk_id"] for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            embeddings=[chunk.embedding for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def search(
        self,
        query: str,
        embedding_model: EmbeddingModel,
        top_k: int = 3,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        query_embedding = embedding_model.embed_texts([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )

        return _format_results(results)

    def keyword_search(
        self,
        query: str,
        top_k: int = 3,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")
        if not query.strip():
            return []

        results = self.collection.get(
            where=where,
            include=["documents", "metadatas"],
        )
        query_terms = _tokenize(query)
        scored_results = []

        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            content = documents[index] if index < len(documents) else ""
            score = _keyword_score(query_terms, content, metadata)
            if score <= 0:
                continue
            scored_results.append(
                {
                    "id": chunk_id,
                    "content": content,
                    "metadata": metadata,
                    "distance": None,
                    "keyword_score": score,
                }
            )

        return sorted(scored_results, key=lambda result: result["keyword_score"], reverse=True)[:top_k]

    def close(self) -> None:
        """Release Chroma resources before deleting a temporary persist folder."""

        if hasattr(self.client, "_system"):
            self.client._system.stop()


def _format_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    formatted_results = []
    for index, chunk_id in enumerate(ids):
        formatted_results.append(
            {
                "id": chunk_id,
                "content": documents[index],
                "metadata": metadatas[index],
                "distance": distances[index] if index < len(distances) else None,
            }
        )

    return formatted_results


def _tokenize(text: str) -> list[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "can",
        "does",
        "for",
        "how",
        "is",
        "of",
        "on",
        "the",
        "to",
        "what",
        "with",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stop_words
    ]


def _keyword_score(query_terms: list[str], content: str, metadata: dict[str, Any]) -> float:
    if not query_terms:
        return 0

    content_text = content.lower()
    metadata_text = " ".join(
        str(metadata.get(field, "")).lower()
        for field in ("filename", "department", "category", "relative_path")
    )
    score = 0.0
    for term in query_terms:
        if term in content_text:
            score += 1.0
        if term in metadata_text:
            score += 2.0
    return score
