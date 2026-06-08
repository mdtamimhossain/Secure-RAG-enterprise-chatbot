from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    configured_path = os.getenv("RAG_DATABASE_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).resolve().parents[1] / "data" / "codemars_demo.sqlite3"


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path else default_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(normalized_name, role)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            sources_json TEXT NOT NULL DEFAULT '[]',
            guardrail_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    connection.commit()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


@dataclass(frozen=True)
class StoredUser:
    id: int
    name: str
    role: str


@dataclass(frozen=True)
class StoredSession:
    token: str
    user: StoredUser


def get_or_create_user(name: str, role: str, database_path: str | Path | None = None) -> StoredUser:
    clean_name = " ".join(name.strip().split())
    normalized_name = normalize_name(clean_name)
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            "SELECT id, name, role FROM users WHERE normalized_name = ? AND role = ?",
            (normalized_name, role),
        ).fetchone()
        if row:
            return StoredUser(id=row["id"], name=row["name"], role=row["role"])

        cursor = connection.execute(
            """
            INSERT INTO users (name, normalized_name, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean_name, normalized_name, role, now_iso()),
        )
        connection.commit()
        return StoredUser(id=cursor.lastrowid, name=clean_name, role=role)
    finally:
        connection.close()


def create_session(token: str, user: StoredUser, database_path: str | Path | None = None) -> StoredSession:
    connection = get_connection(database_path)
    try:
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user.id, now_iso()),
        )
        connection.commit()
        return StoredSession(token=token, user=user)
    finally:
        connection.close()


def get_session(token: str, database_path: str | Path | None = None) -> StoredSession | None:
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            """
            SELECT
                sessions.token,
                users.id AS user_id,
                users.name,
                users.role
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None

        return StoredSession(
            token=row["token"],
            user=StoredUser(id=row["user_id"], name=row["name"], role=row["role"]),
        )
    finally:
        connection.close()


def save_chat_message(
    *,
    user_id: int,
    sender: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    guardrail: dict[str, Any] | None = None,
    database_path: str | Path | None = None,
) -> None:
    connection = get_connection(database_path)
    try:
        connection.execute(
            """
            INSERT INTO chat_messages
                (user_id, sender, content, sources_json, guardrail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                sender,
                content,
                json.dumps(sources or []),
                json.dumps(guardrail) if guardrail else None,
                now_iso(),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def get_chat_messages(user_id: int, database_path: str | Path | None = None) -> list[dict[str, Any]]:
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """
            SELECT sender, content, sources_json, guardrail_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        connection.close()

    messages = []
    for row in rows:
        messages.append(
            {
                "sender": row["sender"],
                "text": row["content"],
                "sources": json.loads(row["sources_json"] or "[]"),
                "guardrail": json.loads(row["guardrail_json"]) if row["guardrail_json"] else None,
                "createdAt": row["created_at"],
            }
        )
    return messages


def clear_user_chat_messages(user_id: int, database_path: str | Path | None = None) -> None:
    connection = get_connection(database_path)
    try:
        connection.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        connection.commit()
    finally:
        connection.close()
