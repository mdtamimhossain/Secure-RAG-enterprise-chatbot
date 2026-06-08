from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_service import build_rag_service


@dataclass(frozen=True)
class RetrievalCheck:
    question: str
    role: str
    expected_department: str | None
    note: str


CHECKS = [
    RetrievalCheck(
        question="How many sick days do employees get?",
        role="hr",
        expected_department="hr",
        note="HR should retrieve the sick leave policy.",
    ),
    RetrievalCheck(
        question="What is the meal reimbursement limit?",
        role="finance",
        expected_department="finance",
        note="Finance should retrieve expense reimbursement policy.",
    ),
    RetrievalCheck(
        question="How do I reset my password?",
        role="employee",
        expected_department="general",
        note="Employee should retrieve general IT support content.",
    ),
    RetrievalCheck(
        question="What is the 2026 revenue target?",
        role="executive",
        expected_department="executive",
        note="Executive should retrieve restricted strategy data.",
    ),
    RetrievalCheck(
        question="What is the 2026 revenue target?",
        role="employee",
        expected_department=None,
        note="Employee should not retrieve executive data.",
    ),
    RetrievalCheck(
        question="What are the cloud budget alerts?",
        role="finance",
        expected_department="finance",
        note="Finance should retrieve FinOps budget information.",
    ),
    RetrievalCheck(
        question="What is the badge replacement process?",
        role="employee",
        expected_department="general",
        note="Employee should retrieve general office/security information.",
    ),
]


def main() -> None:
    service = build_rag_service()
    print("Retrieval quality check")
    print(f"Documents loaded: {service.document_count}")
    print(f"Chunks indexed: {service.chunk_count}")
    print(f"Collection: {service.collection_name}")
    print()

    passed = 0
    for index, check in enumerate(CHECKS, start=1):
        sources = service.rag_chain.retriever.retrieve(
            query=check.question,
            role=check.role,
            top_k=3,
        )
        departments = [
            source.get("metadata", {}).get("department", "unknown")
            for source in sources
        ]
        matched = _matches_expected(departments, check.expected_department)
        if matched:
            passed += 1

        print(f"{index}. {'PASS' if matched else 'FAIL'} | role={check.role}")
        print(f"Question: {check.question}")
        print(f"Expectation: {check.note}")
        if not sources:
            print("Sources: none")
        else:
            print("Sources:")
            for source_number, source in enumerate(sources, start=1):
                metadata = source.get("metadata", {})
                filename = metadata.get("filename", "unknown")
                department = metadata.get("department", "unknown")
                category = metadata.get("category", "unknown")
                preview = " ".join(source.get("content", "").split())[:180]
                print(f"  {source_number}. {filename} | {department} | {category}")
                print(f"     {preview}")
        print()

    print(f"Result: {passed}/{len(CHECKS)} retrieval checks passed")
    if passed != len(CHECKS):
        raise SystemExit(1)


def _matches_expected(departments: list[str], expected_department: str | None) -> bool:
    if expected_department is None:
        return "executive" not in departments and "finance" not in departments and "hr" not in departments

    return expected_department in departments


if __name__ == "__main__":
    main()
