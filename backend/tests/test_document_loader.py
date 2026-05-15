from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.document_loader import load_documents


class DocumentLoaderTests(unittest.TestCase):
    def test_loads_one_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            file_path = data_dir / "general" / "handbook.md"
            file_path.parent.mkdir()
            file_path.write_text("Welcome to the company handbook.", encoding="utf-8")

            documents = load_documents(data_dir)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].content, "Welcome to the company handbook.")
        self.assertEqual(documents[0].metadata["filename"], "handbook.md")
        self.assertEqual(documents[0].metadata["department"], "general")

    def test_adds_department_access_metadata(self) -> None:
        expected_roles_by_department = {
            "general": "employee,hr,finance,manager,executive,admin",
            "hr": "employee,hr,manager,executive,admin",
            "finance": "finance,executive,admin",
        }

        for department, expected_roles in expected_roles_by_department.items():
            with self.subTest(department=department):
                with tempfile.TemporaryDirectory() as temp_dir:
                    data_dir = Path(temp_dir)
                    file_path = data_dir / department / "policy.txt"
                    file_path.parent.mkdir()
                    file_path.write_text("Company policy text.", encoding="utf-8")

                    documents = load_documents(data_dir)

                self.assertEqual(len(documents), 1)
                self.assertEqual(documents[0].metadata["department"], department)
                self.assertEqual(documents[0].metadata["allowed_roles"], expected_roles)

    def test_ignores_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            file_path = data_dir / "hr" / "empty_policy.md"
            file_path.parent.mkdir()
            file_path.write_text("   ", encoding="utf-8")

            documents = load_documents(data_dir)

        self.assertEqual(documents, [])


if __name__ == "__main__":
    unittest.main()
