from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.chunking import chunk_documents
from backend.src.document_loader import load_documents
from backend.src.embeddings import HashEmbeddingModel, embed_chunks


class IngestionPipelineTests(unittest.TestCase):
    def test_load_chunk_and_embed_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            file_path = data_dir / "general" / "handbook.md"
            file_path.parent.mkdir()
            file_path.write_text(
                "Employees can use the internal chatbot to ask questions about "
                "company policies, benefits, leave, payroll, and workplace tools.",
                encoding="utf-8",
            )

            documents = load_documents(data_dir)
            chunks = chunk_documents(documents, chunk_size=45, chunk_overlap=5)
            embedded_chunks = embed_chunks(chunks, HashEmbeddingModel(dimensions=8))

        self.assertEqual(len(documents), 1)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(len(embedded_chunks), len(chunks))

        first_chunk = embedded_chunks[0]
        self.assertEqual(first_chunk.metadata["filename"], "handbook.md")
        self.assertEqual(first_chunk.metadata["department"], "general")
        self.assertEqual(first_chunk.metadata["chunk_index"], "0")
        self.assertEqual(len(first_chunk.embedding), 8)


if __name__ == "__main__":
    unittest.main()
