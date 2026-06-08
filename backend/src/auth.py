from __future__ import annotations

import secrets
from dataclasses import dataclass

from backend.src.database import create_session, get_or_create_user, get_session


ALLOWED_DEMO_ROLES = {"employee", "hr", "finance", "executive"}


@dataclass(frozen=True)
class DemoSession:
    token: str
    user_id: int
    name: str
    role: str


def create_demo_session(name: str, role: str) -> DemoSession:
    clean_name = " ".join(name.strip().split())
    clean_role = role.strip().lower()
    if not clean_name:
        raise ValueError("Name is required")
    if clean_role not in ALLOWED_DEMO_ROLES:
        raise ValueError(f"Unsupported demo role: {role}")

    user = get_or_create_user(clean_name, clean_role)
    stored_session = create_session(secrets.token_urlsafe(32), user)
    return DemoSession(
        token=stored_session.token,
        user_id=stored_session.user.id,
        name=stored_session.user.name,
        role=stored_session.user.role,
    )


def get_demo_session(token: str) -> DemoSession | None:
    stored_session = get_session(token)
    if not stored_session:
        return None

    return DemoSession(
        token=stored_session.token,
        user_id=stored_session.user.id,
        name=stored_session.user.name,
        role=stored_session.user.role,
    )


def clear_demo_sessions() -> None:
    # Tests now isolate database state through temporary DB paths or process
    # state. This function remains for backwards-compatible test setup.
    return None
