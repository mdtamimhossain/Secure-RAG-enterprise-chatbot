from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GuardrailEvent:
    question: str
    role: str
    reason: str
    stage: str
    intent: str
    message: str
    timestamp: str


@dataclass(frozen=True)
class ChatEvent:
    question: str
    role: str
    status: str
    model: str
    latency_ms: float
    source_count: int
    source_departments: list[str]
    guardrail_reason: str
    error: str
    timestamp: str


@dataclass(frozen=True)
class MonitoringMetrics:
    total_chats: int
    successful_chats: int
    blocked_chats: int
    errored_chats: int
    average_latency_ms: float
    average_source_count: float
    roles: dict[str, int]
    guardrail_reasons: dict[str, int]
    source_departments: dict[str, int]
    recent_events: list[dict[str, Any]]


def default_log_dir() -> Path:
    configured_dir = os.getenv("RAG_LOG_DIR")
    if configured_dir:
        return Path(configured_dir)
    return Path(__file__).resolve().parents[1] / "logs"


def log_chat_event(
    *,
    question: str,
    role: str,
    status: str,
    model: str,
    latency_ms: float,
    source_count: int = 0,
    source_departments: list[str] | None = None,
    guardrail_reason: str = "",
    error: str = "",
    log_dir: str | Path | None = None,
) -> ChatEvent:
    """Append a chat request event to a JSONL monitoring log."""

    event = ChatEvent(
        question=question,
        role=role,
        status=status,
        model=model,
        latency_ms=round(latency_ms, 2),
        source_count=source_count,
        source_departments=source_departments or [],
        guardrail_reason=guardrail_reason,
        error=error,
        timestamp=datetime.now(UTC).isoformat(),
    )

    _append_jsonl("chat_events.jsonl", asdict(event), log_dir=log_dir)
    return event


def log_guardrail_event(
    *,
    question: str,
    role: str,
    reason: str,
    stage: str,
    intent: str,
    message: str,
    log_dir: str | Path | None = None,
) -> GuardrailEvent:
    """Append a blocked guardrail event to a JSONL audit log."""

    event = GuardrailEvent(
        question=question,
        role=role,
        reason=reason,
        stage=stage,
        intent=intent,
        message=message,
        timestamp=datetime.now(UTC).isoformat(),
    )

    _append_jsonl("guardrail_events.jsonl", asdict(event), log_dir=log_dir)

    return event


def get_monitoring_metrics(log_dir: str | Path | None = None, recent_limit: int = 8) -> MonitoringMetrics:
    """Aggregate local JSONL logs into dashboard-friendly monitoring metrics."""

    target_dir = Path(log_dir) if log_dir else default_log_dir()
    events = read_jsonl(target_dir / "chat_events.jsonl")

    total = len(events)
    successful = sum(1 for event in events if event.get("status") == "success")
    blocked = sum(1 for event in events if event.get("status") == "blocked")
    errored = sum(1 for event in events if event.get("status") == "error")
    latency_values = [float(event.get("latency_ms", 0)) for event in events]
    source_values = [int(event.get("source_count", 0)) for event in events]

    return MonitoringMetrics(
        total_chats=total,
        successful_chats=successful,
        blocked_chats=blocked,
        errored_chats=errored,
        average_latency_ms=round(sum(latency_values) / total, 2) if total else 0,
        average_source_count=round(sum(source_values) / total, 2) if total else 0,
        roles=_count_by_key(events, "role"),
        guardrail_reasons=_count_by_key(events, "guardrail_reason", skip_empty=True),
        source_departments=_count_source_departments(events),
        recent_events=events[-recent_limit:][::-1],
    )


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Small helper for tests and local inspection."""

    log_path = Path(path)
    if not log_path.exists():
        return []

    rows = []
    with log_path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _append_jsonl(filename: str, payload: dict[str, Any], log_dir: str | Path | None = None) -> None:
    target_dir = Path(log_dir) if log_dir else default_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / filename
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _count_by_key(
    events: list[dict[str, Any]],
    key: str,
    *,
    skip_empty: bool = False,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = str(event.get(key, ""))
        if skip_empty and not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _count_source_departments(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        for department in event.get("source_departments", []):
            counts[department] = counts.get(department, 0) + 1
    return counts
