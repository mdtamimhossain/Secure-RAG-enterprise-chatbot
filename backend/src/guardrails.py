from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class MessageIntent(str, Enum):
    CASUAL = "casual"
    COMPANY = "company"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str
    message: str
    intent: MessageIntent = MessageIntent.UNKNOWN
    stage: str = "input"


PROMPT_INJECTION_PATTERNS = [
    r"\bignore (all )?(previous|prior|system|developer) instructions\b",
    r"\breveal (the )?(system|developer) prompt\b",
    r"\bshow (me )?(the )?(system|developer) prompt\b",
    r"\bbypass (rbac|access control|security|guardrails)\b",
    r"\boverride (the )?(policy|rules|instructions)\b",
    r"\bact as (an )?(unrestricted|jailbroken) assistant\b",
    r"\byou are now in developer mode\b",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    r"\b(?:\d[ -]*?){13,16}\b",
]

PII_REQUEST_PATTERNS = [
    r"\b(show|list|give|tell|export|download|share|send).*(ssn|social security|phone number|phone numbers|personal phone|mobile number|mobile numbers|home address|home addresses|private email|private emails|personal email|personal emails)\b",
    r"\b(employee|employees|staff|worker|workers).*(ssn|social security number|phone number|phone numbers|personal phone|mobile number|mobile numbers|home address|home addresses|private email|private emails|personal email|personal emails)\b",
    r"\ball (employee|employees|staff|worker|workers).*(phone|email|address|ssn|social security)\b",
]

TOXIC_PATTERNS = [
    r"\bkill yourself\b",
    r"\bi hate (all )?\w+ people\b",
    r"\bmake a threat\b",
    r"\bharass\b",
]

CASUAL_PATTERNS = [
    r"^(hi|hello|hey|good morning|good afternoon|good evening)\b",
    r"^(thanks|thank you|ok|okay|cool|great)\b",
    r"\bhow are you\b",
]

COMPANY_KEYWORDS = {
    "codemars",
    "company",
    "employee",
    "employees",
    "hr",
    "finance",
    "executive",
    "manager",
    "policy",
    "benefits",
    "leave",
    "handbook",
    "budget",
    "procurement",
    "expense",
    "reimbursement",
    "revenue",
    "remote",
    "helpdesk",
    "onboarding",
    "performance",
    "access",
    "security",
    "documents",
    "intranet",
}

OUT_OF_SCOPE_PATTERNS = [
    r"\bwho won (the )?(world cup|super bowl|ipl|nba finals)\b",
    r"\bwhat is the capital of\b",
    r"\bbitcoin price\b",
    r"\bstock price\b",
    r"\bmovie recommendation\b",
    r"\bwrite (a )?(poem|song|novel)\b",
    r"\bsolve this math\b",
]


def check_input_guardrails(text: str) -> GuardrailResult:
    """Run safety and scope checks before retrieval and LLM generation."""

    normalized = _normalize(text)
    if not normalized:
        return GuardrailResult(
            allowed=False,
            reason="empty_message",
            message="Please enter a message before sending.",
        )

    unsafe_result = _check_safety_patterns(normalized, stage="input")
    if unsafe_result:
        return unsafe_result

    intent = classify_message_intent(normalized)
    if intent == MessageIntent.OUT_OF_SCOPE:
        return GuardrailResult(
            allowed=False,
            reason="out_of_scope",
            intent=intent,
            message=(
                "I can help with Codemars company documents and internal workplace "
                "questions, but that request is outside this assistant's scope."
            ),
        )

    return GuardrailResult(allowed=True, reason="allowed", message="", intent=intent)


def check_output_guardrails(text: str) -> GuardrailResult:
    """Scan the assistant answer before it leaves the API."""

    normalized = _normalize(text)
    if not normalized:
        return GuardrailResult(allowed=True, reason="allowed", message="", stage="output")

    unsafe_result = _check_safety_patterns(normalized, stage="output")
    if unsafe_result:
        return unsafe_result

    return GuardrailResult(allowed=True, reason="allowed", message="", stage="output")


def check_guardrails(text: str) -> GuardrailResult:
    """Backward-compatible input guardrail entrypoint."""

    return check_input_guardrails(text)


def classify_message_intent(text: str) -> MessageIntent:
    normalized = _normalize(text).lower()
    if _matches_any(normalized, CASUAL_PATTERNS):
        return MessageIntent.CASUAL
    if _matches_any(normalized, OUT_OF_SCOPE_PATTERNS):
        return MessageIntent.OUT_OF_SCOPE
    if any(keyword in normalized for keyword in COMPANY_KEYWORDS):
        return MessageIntent.COMPANY
    if "?" in normalized:
        return MessageIntent.UNKNOWN
    return MessageIntent.CASUAL


def _check_safety_patterns(text: str, stage: str) -> GuardrailResult | None:
    if _matches_any(text, PROMPT_INJECTION_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="prompt_injection",
            stage=stage,
            message=(
                "I cannot follow requests that try to bypass Codemars security, "
                "RBAC, or system instructions."
            ),
        )

    if _matches_any(text, PII_PATTERNS) or _matches_any(text, PII_REQUEST_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="sensitive_personal_data",
            stage=stage,
            message=(
                "I cannot process or reveal sensitive personal data such as SSNs, "
                "personal phone numbers, home addresses, private emails, or payment numbers."
            ),
        )

    if _matches_any(text, TOXIC_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="toxic_content",
            stage=stage,
            message="I cannot help with abusive, threatening, or harmful requests.",
        )

    return None


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())
