from __future__ import annotations

import secrets
from dataclasses import dataclass


ALLOWED_DEMO_ROLES = {"employee", "hr", "finance", "executive"}


@dataclass(frozen=True)
class DemoSession:
    token: str
    name: str
    role: str


_SESSIONS: dict[str, DemoSession] = {}


def create_demo_session(name: str, role: str) -> DemoSession:
    clean_name = " ".join(name.strip().split())
    clean_role = role.strip().lower()
    if not clean_name:
        raise ValueError("Name is required")
    if clean_role not in ALLOWED_DEMO_ROLES:
        raise ValueError(f"Unsupported demo role: {role}")

    token = secrets.token_urlsafe(32)
    session = DemoSession(token=token, name=clean_name, role=clean_role)
    _SESSIONS[token] = session
    return session


def get_demo_session(token: str) -> DemoSession | None:
    return _SESSIONS.get(token)


def clear_demo_sessions() -> None:
    _SESSIONS.clear()
