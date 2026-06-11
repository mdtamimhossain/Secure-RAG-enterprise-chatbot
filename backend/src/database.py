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

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            sources_json TEXT NOT NULL DEFAULT '[]',
            guardrail_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );
        """
    )
    if not _column_exists(connection, "chat_messages", "conversation_id"):
        connection.execute("ALTER TABLE chat_messages ADD COLUMN conversation_id INTEGER")
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


@dataclass(frozen=True)
class StoredConversation:
    id: int
    user_id: int
    title: str
    created_at: str
    updated_at: str


def _column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


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


def create_conversation(
    user_id: int,
    title: str = "New chat",
    database_path: str | Path | None = None,
) -> StoredConversation:
    timestamp = now_iso()
    connection = get_connection(database_path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO conversations (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, timestamp, timestamp),
        )
        connection.commit()
        return StoredConversation(
            id=cursor.lastrowid,
            user_id=user_id,
            title=title,
            created_at=timestamp,
            updated_at=timestamp,
        )
    finally:
        connection.close()


def get_conversation(
    conversation_id: int,
    user_id: int,
    database_path: str | Path | None = None,
) -> StoredConversation | None:
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            return None
        return _conversation_from_row(row)
    finally:
        connection.close()


def list_conversations(user_id: int, database_path: str | Path | None = None) -> list[StoredConversation]:
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
        return [_conversation_from_row(row) for row in rows]
    finally:
        connection.close()


def get_or_create_latest_conversation(
    user_id: int,
    database_path: str | Path | None = None,
) -> StoredConversation:
    conversations = list_conversations(user_id, database_path)
    if conversations:
        return conversations[0]
    return create_conversation(user_id, database_path=database_path)


def delete_conversation(
    user_id: int,
    conversation_id: int,
    database_path: str | Path | None = None,
) -> bool:
    connection = get_connection(database_path)
    try:
        row = connection.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            return False

        connection.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND conversation_id = ?",
            (user_id, conversation_id),
        )
        connection.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        connection.commit()
        return True
    finally:
        connection.close()


def _conversation_from_row(row: sqlite3.Row) -> StoredConversation:
    return StoredConversation(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


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
    conversation_id: int,
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
                (user_id, conversation_id, sender, content, sources_json, guardrail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                conversation_id,
                sender,
                content,
                json.dumps(sources or []),
                json.dumps(guardrail) if guardrail else None,
                now_iso(),
            ),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ? AND user_id = ?",
            (now_iso(), conversation_id, user_id),
        )
        connection.commit()
    finally:
        connection.close()


def get_chat_messages(
    user_id: int,
    conversation_id: int,
    database_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """
            SELECT sender, content, sources_json, guardrail_json, created_at
            FROM chat_messages
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY id ASC
            """,
            (user_id, conversation_id),
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


def clear_conversation_messages(
    user_id: int,
    conversation_id: int,
    database_path: str | Path | None = None,
) -> None:
    connection = get_connection(database_path)
    try:
        connection.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND conversation_id = ?",
            (user_id, conversation_id),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ? AND user_id = ?",
            (now_iso(), conversation_id, user_id),
        )
        connection.commit()
    finally:
        connection.close()
