from __future__ import annotations

from dataclasses import dataclass

from backend.src.document_loader import LoadedDocument


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    metadata: dict[str, str]


def chunk_documents(
    documents: list[LoadedDocument],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[DocumentChunk]:
    """Split loaded documents into smaller chunks for vector search."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[DocumentChunk] = []

    for document in documents:
        text = document.content.strip()
        if not text:
            continue

        for chunk_index, chunk_text in enumerate(_split_text(text, chunk_size, chunk_overlap)):
            metadata = {
                **document.metadata,
                "chunk_index": str(chunk_index),
                "chunk_id": f"{document.metadata.get('document_id', 'document')}-{chunk_index}",
            }
            chunks.append(DocumentChunk(content=chunk_text, metadata=metadata))

    return chunks


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - chunk_overlap

    return chunks
