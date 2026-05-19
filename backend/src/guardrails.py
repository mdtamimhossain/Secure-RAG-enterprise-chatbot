from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str
    message: str


PROMPT_INJECTION_PATTERNS = [
    r"\bignore (all )?(previous|prior|system|developer) instructions\b",
    r"\breveal (the )?(system|developer) prompt\b",
    r"\bshow (me )?(the )?(system|developer) prompt\b",
    r"\bbypass (rbac|access control|security|guardrails)\b",
    r"\boverride (the )?(policy|rules|instructions)\b",
    r"\bact as (an )?(unrestricted|jailbroken) assistant\b",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
]

PII_REQUEST_PATTERNS = [
    r"\b(show|list|give|tell).*(ssn|social security|personal phone|home address|private email)\b",
    r"\b(employee|staff).*(ssn|social security number|personal phone|home address)\b",
]

TOXIC_PATTERNS = [
    r"\bkill yourself\b",
    r"\bi hate (all )?\w+ people\b",
    r"\bmake a threat\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\bwho won (the )?(world cup|super bowl|ipl)\b",
    r"\bwhat is the capital of\b",
    r"\bbitcoin price\b",
    r"\bstock price\b",
    r"\bmovie recommendation\b",
]


def check_guardrails(text: str) -> GuardrailResult:
    """Run lightweight safety checks before retrieval and LLM generation."""

    normalized = " ".join(text.strip().split())
    if not normalized:
        return GuardrailResult(
            allowed=False,
            reason="empty_message",
            message="Please enter a message before sending.",
        )

    if _matches_any(normalized, PROMPT_INJECTION_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="prompt_injection",
            message=(
                "I cannot follow requests that try to bypass Codemars security, "
                "RBAC, or system instructions."
            ),
        )

    if _matches_any(normalized, PII_PATTERNS) or _matches_any(normalized, PII_REQUEST_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="sensitive_personal_data",
            message=(
                "I cannot process or reveal sensitive personal data such as SSNs, "
                "personal phone numbers, home addresses, or private emails."
            ),
        )

    if _matches_any(normalized, TOXIC_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="toxic_content",
            message="I cannot help with abusive, threatening, or harmful requests.",
        )

    if _matches_any(normalized, OUT_OF_SCOPE_PATTERNS):
        return GuardrailResult(
            allowed=False,
            reason="out_of_scope",
            message=(
                "I can help with Codemars company documents and internal workplace "
                "questions, but that request is outside this assistant's scope."
            ),
        )

    return GuardrailResult(allowed=True, reason="allowed", message="")


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
