from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


class OpenAIEmbeddingModel:
    """Embedding model backed by the OpenAI embeddings API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "text-embedding-3-small",
        api_url: str = "https://api.openai.com/v1/embeddings",
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required to use OpenAIEmbeddingModel")

        self.model_name = model_name
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model_name,
            "input": texts,
            "encoding_format": "float",
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI embeddings request failed: {exc.code} {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenAI embeddings request failed: {exc.reason}") from exc

        embeddings_by_index = {
            item["index"]: item["embedding"] for item in response_data["data"]
        }
        return [embeddings_by_index[index] for index in range(len(texts))]


def create_embedding_model(
    provider: str | None = None,
    model_name: str | None = None,
) -> EmbeddingModel:
    """Create the embedding model configured for the app.

    Supported providers:
    - hash: fast deterministic vectors for tests/local scaffolding
    - sentence-transformer: real semantic embeddings
    - openai: OpenAI embeddings API
    """

    provider = (provider or os.getenv("EMBEDDING_PROVIDER", "hash")).lower()
    model_name = model_name or os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    if provider == "hash":
        return HashEmbeddingModel(dimensions=16)
    if provider in {"sentence-transformer", "sentence_transformer"}:
        return SentenceTransformerEmbeddingModel(model_name=model_name)
    if provider == "openai":
        openai_model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddingModel(model_name=openai_model_name)

    raise ValueError(f"Unsupported embedding provider: {provider}")


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
