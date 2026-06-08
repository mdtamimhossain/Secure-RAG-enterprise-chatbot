from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.database import (
    clear_conversation_messages,
    create_conversation,
    create_session,
    get_chat_messages,
    get_conversation,
    get_or_create_user,
    list_conversations,
    get_session,
    save_chat_message,
)


class DatabaseTests(unittest.TestCase):
    def test_creates_user_session_and_loads_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.sqlite3"

            user = get_or_create_user("Md Tamim", "employee", database_path)
            session = create_session("token-123", user, database_path)
            loaded_session = get_session("token-123", database_path)

        self.assertEqual(session.token, "token-123")
        self.assertIsNotNone(loaded_session)
        self.assertEqual(loaded_session.user.name, "Md Tamim")
        self.assertEqual(loaded_session.user.role, "employee")

    def test_saves_loads_and_clears_chat_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.sqlite3"
            user = get_or_create_user("Finance User", "finance", database_path)
            conversation = create_conversation(user.id, "Expense question", database_path)

            save_chat_message(
                user_id=user.id,
                conversation_id=conversation.id,
                sender="user",
                content="What is the meal limit?",
                database_path=database_path,
            )
            save_chat_message(
                user_id=user.id,
                conversation_id=conversation.id,
                sender="assistant",
                content="Domestic meal reimbursement is capped at 35 per meal.",
                sources=[{"metadata": {"department": "finance"}}],
                database_path=database_path,
            )
            messages = get_chat_messages(user.id, conversation.id, database_path)
            clear_conversation_messages(user.id, conversation.id, database_path)
            cleared_messages = get_chat_messages(user.id, conversation.id, database_path)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["sender"], "user")
        self.assertEqual(messages[1]["sources"][0]["metadata"]["department"], "finance")
        self.assertEqual(cleared_messages, [])

    def test_conversations_are_user_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.sqlite3"
            first_user = get_or_create_user("First User", "employee", database_path)
            second_user = get_or_create_user("Second User", "employee", database_path)
            conversation = create_conversation(first_user.id, "Leave policy", database_path)

            first_user_conversations = list_conversations(first_user.id, database_path)
            second_user_conversation = get_conversation(conversation.id, second_user.id, database_path)

        self.assertEqual(len(first_user_conversations), 1)
        self.assertEqual(first_user_conversations[0].title, "Leave policy")
        self.assertIsNone(second_user_conversation)


if __name__ == "__main__":
    unittest.main()
