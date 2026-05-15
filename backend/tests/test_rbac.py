from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rbac import build_department_filter, get_allowed_departments


class RbacTests(unittest.TestCase):
    def test_employee_can_access_general_and_hr_docs(self) -> None:
        self.assertEqual(get_allowed_departments("employee"), ["general", "hr"])

    def test_unknown_role_gets_general_docs_only(self) -> None:
        self.assertEqual(get_allowed_departments("unknown"), ["general"])

    def test_builds_chroma_department_filter(self) -> None:
        self.assertEqual(
            build_department_filter("finance"),
            {"department": {"$in": ["general", "finance"]}},
        )


if __name__ == "__main__":
    unittest.main()
