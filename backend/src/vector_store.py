from __future__ import annotations

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
