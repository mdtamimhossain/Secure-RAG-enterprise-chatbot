from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from backend.src.chunking import DocumentChunk


class EmbeddingModel(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Convert texts into vector embeddings."""


@dataclass(frozen=True)
class EmbeddedChunk:
    content: str
    metadata: dict[str, str]
    embedding: list[float]


class HashEmbeddingModel:
    """Small deterministic embedding model for local tests and early development.

    This is not semantic AI. It only creates stable numeric vectors so the rest
    of the RAG pipeline can be built before adding a real embedding model.
    """

    def __init__(self, dimensions: int = 16) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []

        for index in range(self.dimensions):
            byte = digest[index % len(digest)]
            values.append((byte / 127.5) - 1.0)

        return values


class SentenceTransformerEmbeddingModel:
    """Real embedding model backed by sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for real embeddings. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


def embed_chunks(
    chunks: list[DocumentChunk],
    embedding_model: EmbeddingModel,
) -> list[EmbeddedChunk]:
    """Add vector embeddings to document chunks."""

    if not chunks:
        return []

    texts = [chunk.content for chunk in chunks]
    vectors = embedding_model.embed_texts(texts)

    if len(vectors) != len(chunks):
        raise ValueError("Embedding model returned a different number of vectors")

    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, vectors):
        embedded_chunks.append(
            EmbeddedChunk(
                content=chunk.content,
                metadata=chunk.metadata,
                embedding=vector,
            )
        )

    return embedded_chunks
