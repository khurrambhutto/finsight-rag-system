from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_title(content: str, *, fallback: str = "New chat") -> str:
    compact = " ".join(content.split()).strip()
    if not compact:
        return fallback
    return compact[:57] + "..." if len(compact) > 60 else compact


class ChatStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        if not self.db_path.is_absolute():
            backend_root = Path(__file__).resolve().parents[3]
            self.db_path = (backend_root / self.db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chat_threads_user_updated
                ON chat_threads(user_id, updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_created
                ON chat_messages(thread_id, created_at ASC);
                """
            )

    def list_threads(self, *, user_id: str) -> list[dict[str, str | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.created_at,
                    t.updated_at,
                    (
                        SELECT m.content
                        FROM chat_messages AS m
                        WHERE m.thread_id = t.id
                        ORDER BY m.created_at DESC, m.id DESC
                        LIMIT 1
                    ) AS preview
                FROM chat_threads AS t
                WHERE t.user_id = ?
                ORDER BY t.updated_at DESC, t.created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_thread(self, *, user_id: str, title: str = "New chat") -> dict[str, str | None]:
        thread_id = str(uuid.uuid4())
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_threads (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (thread_id, user_id, title, now, now),
            )
        return {
            "id": thread_id,
            "title": title,
            "preview": None,
            "created_at": now,
            "updated_at": now,
        }

    def get_thread(self, *, user_id: str, thread_id: str) -> dict[str, object]:
        with self._connect() as connection:
            thread = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_threads
                WHERE id = ? AND user_id = ?
                """,
                (thread_id, user_id),
            ).fetchone()
            if thread is None:
                raise KeyError(thread_id)

            message_rows = connection.execute(
                """
                SELECT id, role, content, model, created_at
                FROM chat_messages
                WHERE thread_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (thread_id,),
            ).fetchall()

        messages = [dict(row) for row in message_rows]
        preview = messages[-1]["content"] if messages else None
        return {
            "id": thread["id"],
            "title": thread["title"],
            "preview": preview,
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"],
            "messages": messages,
        }

    def get_messages(self, *, user_id: str, thread_id: str) -> list[dict[str, str | None]]:
        self._require_thread(user_id=user_id, thread_id=thread_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, role, content, model, created_at
                FROM chat_messages
                WHERE thread_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_thread_title_from_message(self, *, user_id: str, thread_id: str, content: str) -> None:
        thread = self._require_thread(user_id=user_id, thread_id=thread_id)
        if thread["title"] != "New chat":
            return
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE chat_threads
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (_normalize_title(content), _utc_now(), thread_id),
            )

    def add_message(
        self,
        *,
        user_id: str,
        thread_id: str,
        role: str,
        content: str,
        model: str | None = None,
    ) -> dict[str, str | None]:
        self._require_thread(user_id=user_id, thread_id=thread_id)
        message_id = str(uuid.uuid4())
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages (id, thread_id, role, content, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, thread_id, role, content, model, now),
            )
            connection.execute(
                """
                UPDATE chat_threads
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, thread_id),
            )
        return {
            "id": message_id,
            "role": role,
            "content": content,
            "model": model,
            "created_at": now,
        }

    def _require_thread(self, *, user_id: str, thread_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_threads
                WHERE id = ? AND user_id = ?
                """,
                (thread_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError(thread_id)
        return row


@lru_cache
def get_chat_store(db_path: str) -> ChatStore:
    return ChatStore(db_path)
