from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_chain import ChatHistoryMessage
from backend.src.rag_service import build_rag_service


@dataclass(frozen=True)
class AnswerCheck:
    question: str
    role: str
    expected_source_department: str | None
    expected_answer_text: str
    note: str
    history: tuple[ChatHistoryMessage, ...] = ()


class QualityCheckLLM:
    """Deterministic local LLM used to verify RAG orchestration behavior.

    This does not judge natural language quality. It verifies that retrieved
    context, source hiding, RBAC, and follow-up memory are wired correctly before
    testing with a live model.
    """

    def __init__(self) -> None:
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        user_message = _extract_section(prompt, "User message:", "Answer:").lower()
        context = _extract_section(prompt, "Retrieved context:", "User message:").lower()

        if user_message in {"hi", "hello", "hey"}:
            return "SOURCE_USAGE: casual\nHello. How can I help with Codemars today?"

        if "sick" in user_message and "10 paid sick days" in context:
            return "SOURCE_USAGE: context\nEmployees receive 10 paid sick days per calendar year."

        if "meal reimbursement" in user_message and "35 per meal" in context:
            return "SOURCE_USAGE: context\nDomestic meal reimbursement is capped at 35 per meal."

        if "revenue target" in user_message and "18.5 million" in context:
            return "SOURCE_USAGE: context\nThe 2026 annual recurring revenue target is 18.5 million."

        if "carry-over" in user_message and "5 unused vacation days" in context:
            return (
                "SOURCE_USAGE: context\n"
                "Up to 5 unused vacation days may be carried into the next year until March 31."
            )

        if "pet insurance" in user_message:
            return (
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )

        return (
            "SOURCE_USAGE: none\n"
            "I could not find specific information about that in your available company documents."
        )


CHECKS = [
    AnswerCheck(
        question="hello",
        role="employee",
        expected_source_department=None,
        expected_answer_text="Hello",
        note="Greeting should answer naturally and hide sources.",
    ),
    AnswerCheck(
        question="How many sick days do employees get?",
        role="hr",
        expected_source_department="hr",
        expected_answer_text="10 paid sick days",
        note="Known HR policy should answer from HR context.",
    ),
    AnswerCheck(
        question="What is the meal reimbursement limit?",
        role="finance",
        expected_source_department="finance",
        expected_answer_text="35 per meal",
        note="Known finance policy should answer from finance context.",
    ),
    AnswerCheck(
        question="What is the 2026 revenue target?",
        role="employee",
        expected_source_department=None,
        expected_answer_text="could not find specific information",
        note="Employee should not receive restricted executive answer.",
    ),
    AnswerCheck(
        question="What about carry-over?",
        role="hr",
        expected_source_department="hr",
        expected_answer_text="5 unused vacation days",
        note="Follow-up should use previous leave context.",
        history=(
            ChatHistoryMessage(role="user", content="What is the leave policy?"),
            ChatHistoryMessage(
                role="assistant",
                content="Codemars leave policy includes vacation days, sick leave, and carry-over rules.",
            ),
        ),
    ),
    AnswerCheck(
        question="What is Codemars pet insurance policy?",
        role="employee",
        expected_source_department=None,
        expected_answer_text="could not find specific information",
        note="Unknown company policy should return safe not-found answer.",
    ),
]


def main() -> None:
    service = build_rag_service(llm_client=QualityCheckLLM())
    print("Answer quality check")
    print(f"Documents loaded: {service.document_count}")
    print(f"Chunks indexed: {service.chunk_count}")
    print(f"Collection: {service.collection_name}")
    print()

    passed = 0
    for index, check in enumerate(CHECKS, start=1):
        response = service.rag_chain.answer_question(
            question=check.question,
            role=check.role,
            top_k=3,
            chat_history=list(check.history),
        )
        departments = [
            source.get("metadata", {}).get("department", "unknown")
            for source in response.sources
        ]
        answer_ok = check.expected_answer_text.lower() in response.answer.lower()
        sources_ok = _sources_match(departments, check.expected_source_department)
        matched = answer_ok and sources_ok
        if matched:
            passed += 1

        print(f"{index}. {'PASS' if matched else 'FAIL'} | role={check.role}")
        print(f"Question: {check.question}")
        print(f"Expectation: {check.note}")
        print(f"Answer: {response.answer}")
        if response.sources:
            print("Visible sources:")
            for source_number, source in enumerate(response.sources, start=1):
                metadata = source.get("metadata", {})
                print(
                    f"  {source_number}. "
                    f"{metadata.get('filename', 'unknown')} | "
                    f"{metadata.get('department', 'unknown')} | "
                    f"{metadata.get('category', 'unknown')}"
                )
        else:
            print("Visible sources: none")
        print()

    print(f"Result: {passed}/{len(CHECKS)} answer checks passed")
    if passed != len(CHECKS):
        raise SystemExit(1)


def _sources_match(departments: list[str], expected_department: str | None) -> bool:
    if expected_department is None:
        return departments == []

    return expected_department in departments


def _extract_section(text: str, start_marker: str, end_marker: str) -> str:
    pattern = re.compile(
        rf"{re.escape(start_marker)}\n?(.*?){re.escape(end_marker)}",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


if __name__ == "__main__":
    main()
