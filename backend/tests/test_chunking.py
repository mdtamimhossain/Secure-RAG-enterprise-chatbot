from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.chunking import chunk_documents
from backend.src.document_loader import LoadedDocument


class ChunkingTests(unittest.TestCase):
    def test_short_document_creates_one_chunk(self) -> None:
        document = LoadedDocument(
            content="Short company policy.",
            metadata={"document_id": "doc-1", "department": "general"},
        )

        chunks = chunk_documents([document], chunk_size=100, chunk_overlap=10)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "Short company policy.")
        self.assertEqual(chunks[0].metadata["department"], "general")
        self.assertEqual(chunks[0].metadata["chunk_index"], "0")
        self.assertEqual(chunks[0].metadata["chunk_id"], "doc-1-0")

    def test_long_document_creates_multiple_chunks(self) -> None:
        document = LoadedDocument(
            content="abcdefghij",
            metadata={"document_id": "doc-2", "department": "hr"},
        )

        chunks = chunk_documents([document], chunk_size=4, chunk_overlap=1)

        self.assertEqual([chunk.content for chunk in chunks], ["abcd", "defg", "ghij"])

    def test_invalid_chunk_settings_raise_error(self) -> None:
        document = LoadedDocument(content="Text", metadata={"document_id": "doc-3"})

        with self.assertRaises(ValueError):
            chunk_documents([document], chunk_size=10, chunk_overlap=10)


if __name__ == "__main__":
    unittest.main()
