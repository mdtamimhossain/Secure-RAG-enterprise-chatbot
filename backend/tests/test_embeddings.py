from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.chunking import DocumentChunk
from backend.src.embeddings import HashEmbeddingModel, embed_chunks


class EmbeddingsTests(unittest.TestCase):
    def test_hash_embedding_model_creates_fixed_size_vector(self) -> None:
        model = HashEmbeddingModel(dimensions=8)

        vectors = model.embed_texts(["company policy"])

        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), 8)

    def test_embed_chunks_keeps_content_and_metadata(self) -> None:
        chunk = DocumentChunk(
            content="Employees can ask questions about policies.",
            metadata={"chunk_id": "doc-1-0", "department": "general"},
        )
        model = HashEmbeddingModel(dimensions=4)

        embedded_chunks = embed_chunks([chunk], model)

        self.assertEqual(len(embedded_chunks), 1)
        self.assertEqual(embedded_chunks[0].content, chunk.content)
        self.assertEqual(embedded_chunks[0].metadata["department"], "general")
        self.assertEqual(len(embedded_chunks[0].embedding), 4)

    def test_empty_chunk_list_returns_empty_list(self) -> None:
        model = HashEmbeddingModel()

        embedded_chunks = embed_chunks([], model)

        self.assertEqual(embedded_chunks, [])


if __name__ == "__main__":
    unittest.main()
