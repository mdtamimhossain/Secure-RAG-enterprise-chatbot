from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.src.embeddings import HashEmbeddingModel
from backend.src.guardrails import check_input_guardrails
from backend.src.rag_chain import ChatHistoryMessage, LLMClient
from backend.src.rag_service import RAGServiceSettings, build_rag_service


DEFAULT_DATASET_PATH = Path(__file__).with_name("eval_dataset.json")


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    role: str
    expected_departments: list[str] = field(default_factory=list)
    forbidden_departments: list[str] = field(default_factory=list)
    expected_behavior: str = "answer_from_context"
    should_have_sources: bool = True
    history: list[ChatHistoryMessage] = field(default_factory=list)


@dataclass(frozen=True)
class EvalCaseResult:
    id: str
    passed: bool
    behavior_passed: bool
    expected_department_passed: bool
    forbidden_department_passed: bool
    source_visibility_passed: bool
    actual_departments: list[str]
    source_count: int
    answer: str
    failures: list[str]


@dataclass(frozen=True)
class EvalReport:
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    retrieval_accuracy: float
    rbac_accuracy: float
    behavior_accuracy: float
    source_visibility_accuracy: float
    results: list[EvalCaseResult]


class EvalLLM:
    """Deterministic LLM for local evals; it follows the source marker contract."""

    def generate(self, prompt: str) -> str:
        user_message = _extract_section(prompt, "User message:", "Answer:").lower()
        retrieved_context = _extract_section(prompt, "Retrieved context:", "User message:")

        if "Ignore previous instructions" in prompt:
            return "SOURCE_USAGE: none\nBlocked by guardrails."
        if user_message in {"hello", "hi", "hey"}:
            return "SOURCE_USAGE: casual\nHello. How can I help with Codemars today?"
        if "Retrieved context:\nNo retrieved context." in prompt:
            return (
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )
        if _needs_department(user_message, "finance") and "department=finance" not in retrieved_context:
            return (
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )
        if _needs_department(user_message, "hr") and "department=hr" not in retrieved_context:
            return (
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )
        if _needs_department(user_message, "executive") and "department=executive" not in retrieved_context:
            return (
                "SOURCE_USAGE: none\n"
                "I could not find specific information about that in your available company documents."
            )
        return "SOURCE_USAGE: context\nI found relevant Codemars document context for this question."


def load_eval_cases(dataset_path: str | Path = DEFAULT_DATASET_PATH) -> list[EvalCase]:
    rows = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    cases = []
    for row in rows:
        history = [
            ChatHistoryMessage(role=message["role"], content=message["content"])
            for message in row.get("history", [])
        ]
        cases.append(
            EvalCase(
                id=row["id"],
                question=row["question"],
                role=row["role"],
                expected_departments=row.get("expected_departments", []),
                forbidden_departments=row.get("forbidden_departments", []),
                expected_behavior=row.get("expected_behavior", "answer_from_context"),
                should_have_sources=row.get("should_have_sources", True),
                history=history,
            )
        )
    return cases


def run_evaluation(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    data_dir: str | Path | None = None,
    llm_client: LLMClient | None = None,
) -> EvalReport:
    cases = load_eval_cases(dataset_path)
    backend_dir = Path(__file__).resolve().parents[1]
    source_data_dir = Path(data_dir) if data_dir else backend_dir / "data"

    with tempfile.TemporaryDirectory() as temp_dir:
        service = build_rag_service(
            RAGServiceSettings(
                data_dir=source_data_dir,
                persist_dir=Path(temp_dir) / "eval_chroma",
                collection_name="eval_documents",
            ),
            embedding_model=HashEmbeddingModel(dimensions=64),
            llm_client=llm_client or EvalLLM(),
        )
        try:
            results = [evaluate_case(case, service.rag_chain) for case in cases]
        finally:
            service.rag_chain.retriever.vector_store.close()

    return build_eval_report(results)


def evaluate_case(case: EvalCase, rag_chain: Any) -> EvalCaseResult:
    guardrail_result = check_input_guardrails(case.question)
    if not guardrail_result.allowed:
        answer = guardrail_result.message
        sources: list[dict[str, Any]] = []
        actual_behavior = "guardrail_block"
    else:
        response = rag_chain.answer_question(
            case.question,
            role=case.role,
            top_k=3,
            chat_history=case.history,
        )
        answer = response.answer
        sources = response.sources
        actual_behavior = infer_behavior(answer, sources)

    departments = sorted(
        {
            source.get("metadata", {}).get("department", "")
            for source in sources
            if source.get("metadata", {}).get("department")
        }
    )

    behavior_passed = actual_behavior == case.expected_behavior
    expected_department_passed = all(
        department in departments for department in case.expected_departments
    )
    forbidden_department_passed = all(
        department not in departments for department in case.forbidden_departments
    )
    source_visibility_passed = bool(sources) == case.should_have_sources

    failures = []
    if not behavior_passed:
        failures.append(f"expected behavior {case.expected_behavior}, got {actual_behavior}")
    if not expected_department_passed:
        failures.append(f"missing expected departments {case.expected_departments}")
    if not forbidden_department_passed:
        failures.append(f"returned forbidden departments {case.forbidden_departments}")
    if not source_visibility_passed:
        failures.append(f"expected sources={case.should_have_sources}, got {bool(sources)}")

    return EvalCaseResult(
        id=case.id,
        passed=not failures,
        behavior_passed=behavior_passed,
        expected_department_passed=expected_department_passed,
        forbidden_department_passed=forbidden_department_passed,
        source_visibility_passed=source_visibility_passed,
        actual_departments=departments,
        source_count=len(sources),
        answer=answer,
        failures=failures,
    )


def infer_behavior(answer: str, sources: list[dict[str, Any]]) -> str:
    lowered_answer = answer.lower()
    if sources:
        return "answer_from_context"
    if "could not find specific information" in lowered_answer:
        return "no_available_context"
    return "casual"


def build_eval_report(results: list[EvalCaseResult]) -> EvalReport:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    return EvalReport(
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        pass_rate=_percentage(passed, total),
        retrieval_accuracy=_percentage(
            sum(1 for result in results if result.expected_department_passed),
            total,
        ),
        rbac_accuracy=_percentage(
            sum(1 for result in results if result.forbidden_department_passed),
            total,
        ),
        behavior_accuracy=_percentage(
            sum(1 for result in results if result.behavior_passed),
            total,
        ),
        source_visibility_accuracy=_percentage(
            sum(1 for result in results if result.source_visibility_passed),
            total,
        ),
        results=results,
    )


def _percentage(value: int, total: int) -> float:
    return round((value / total) * 100, 2) if total else 0


def _extract_section(text: str, start_marker: str, end_marker: str) -> str:
    start_index = text.find(start_marker)
    if start_index == -1:
        return ""
    start_index += len(start_marker)
    end_index = text.find(end_marker, start_index)
    if end_index == -1:
        return text[start_index:].strip()
    return text[start_index:end_index].strip()


def _needs_department(user_message: str, department: str) -> bool:
    keywords_by_department = {
        "finance": {"finance", "budget", "revenue", "expense", "reimbursement", "procurement"},
        "hr": {"hr", "leave", "onboarding", "performance", "employee relations"},
        "executive": {"executive", "acquisition", "board", "leadership", "strategy"},
    }
    return any(keyword in user_message for keyword in keywords_by_department[department])


def main() -> None:
    report = run_evaluation()
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
