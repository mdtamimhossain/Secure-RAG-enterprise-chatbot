from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_service import build_rag_service
from backend.src.rag_chain import ChatHistoryMessage, build_retrieval_query


@dataclass(frozen=True)
class RetrievalCheck:
    question: str
    role: str
    expected_department: str | None
    note: str
    history: tuple[ChatHistoryMessage, ...] = ()


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
    RetrievalCheck(
        question="What about carry-over?",
        role="hr",
        expected_department="hr",
        note="Follow-up should use previous leave-policy context.",
        history=(
            ChatHistoryMessage(role="user", content="What is the leave policy?"),
            ChatHistoryMessage(
                role="assistant",
                content="Codemars leave policy includes vacation days, sick leave, and carry-over rules.",
            ),
        ),
    ),
    RetrievalCheck(
        question="How do I reset my password?",
        role="employee",
        expected_department="general",
        note="New topic should retrieve password help, not old leave-policy context.",
        history=(
            ChatHistoryMessage(role="user", content="What is the leave policy?"),
            ChatHistoryMessage(role="assistant", content="Codemars employees receive vacation days."),
        ),
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
        retrieval_query = build_retrieval_query(check.question, list(check.history))
        sources = service.rag_chain.retriever.retrieve(
            query=retrieval_query,
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
        if check.history:
            print("Retrieval query:")
            print(_indent(retrieval_query))
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


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


if __name__ == "__main__":
    main()
