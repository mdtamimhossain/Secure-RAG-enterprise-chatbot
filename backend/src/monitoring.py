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


def default_log_dir() -> Path:
    configured_dir = os.getenv("RAG_LOG_DIR")
    if configured_dir:
        return Path(configured_dir)
    return Path(__file__).resolve().parents[1] / "logs"


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

    target_dir = Path(log_dir) if log_dir else default_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / "guardrail_events.jsonl"
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    return event


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
