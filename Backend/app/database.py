
from __future__ import annotations

import json
import os
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "egovassist.db"
)


DATABASE_PATH = Path(
    os.getenv(
        "EGOVASSIST_DB_PATH",
        str(DEFAULT_DATABASE_PATH),
    )
)


def _utc_now() -> str:

    return (
        datetime.now(timezone.utc)
        .isoformat()
    )


def _get_connection() -> sqlite3.Connection:

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    return connection


def initialize_database() -> None:

    connection = _get_connection()

    try:

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,

                user_id TEXT NOT NULL,

                title TEXT NOT NULL,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                pinned INTEGER NOT NULL DEFAULT 0
            );


            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,

                conversation_id TEXT NOT NULL,

                role TEXT NOT NULL,

                content TEXT NOT NULL,

                language TEXT NOT NULL DEFAULT 'en',

                evidence_json TEXT NOT NULL DEFAULT '[]',

                created_at TEXT NOT NULL,

                FOREIGN KEY (
                    conversation_id
                )
                REFERENCES conversations(id)
                ON DELETE CASCADE
            );


            CREATE INDEX IF NOT EXISTS
                idx_conversations_user_updated
            ON conversations (
                user_id,
                updated_at DESC
            );


            CREATE INDEX IF NOT EXISTS
                idx_messages_conversation_created
            ON messages (
                conversation_id,
                created_at ASC
            );


            --------------------------------------------------
            -- EXACT SOURCE LOCATOR CACHE
            --------------------------------------------------

            CREATE TABLE IF NOT EXISTS evidence_source_cache (

                cache_key TEXT PRIMARY KEY,

                chunk_id TEXT,

                source_url TEXT NOT NULL,

                source_title TEXT,

                source_type TEXT,

                source_text TEXT,

                locator_json TEXT NOT NULL,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL
            );


            CREATE INDEX IF NOT EXISTS
                idx_evidence_source_cache_chunk
            ON evidence_source_cache (
                chunk_id
            );


            CREATE INDEX IF NOT EXISTS
                idx_evidence_source_cache_url
            ON evidence_source_cache (
                source_url
            );

            """
        )

        connection.commit()

    finally:

        connection.close()


def _conversation_from_row(
    row: sqlite3.Row,
) -> dict[str, Any]:

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "pinned": bool(row["pinned"]),
    }


def _message_from_row(
    row: sqlite3.Row,
) -> dict[str, Any]:

    evidence = []

    raw_evidence = (
        row["evidence_json"]
        or "[]"
    )

    try:

        parsed = json.loads(
            raw_evidence
        )

        if isinstance(
            parsed,
            list,
        ):

            evidence = parsed

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):

        evidence = []

    return {
        "id": row["id"],
        "conversation_id": row[
            "conversation_id"
        ],
        "role": row["role"],
        "content": row["content"],
        "language": row["language"],
        "evidence": evidence,
        "created_at": row["created_at"],
    }


def create_conversation(
    user_id: str,
    title: str = "New Chat",
) -> dict[str, Any]:

    conversation_id = str(
        uuid.uuid4()
    )

    now = _utc_now()

    connection = _get_connection()

    try:

        connection.execute(
            """
            INSERT INTO conversations (
                id,
                user_id,
                title,
                created_at,
                updated_at,
                pinned
            )
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                conversation_id,
                user_id,
                title,
                now,
                now,
            ),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE id = ?
            """,
            (
                conversation_id,
            ),
        ).fetchone()

        return _conversation_from_row(
            row
        )

    finally:

        connection.close()


def get_conversations(
    user_id: str,
) -> list[dict[str, Any]]:

    connection = _get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE user_id = ?
            ORDER BY
                pinned DESC,
                updated_at DESC
            """,
            (
                user_id,
            ),
        ).fetchall()

        return [
            _conversation_from_row(row)
            for row in rows
        ]

    finally:

        connection.close()


def get_conversation(
    conversation_id: str,
    user_id: str,
) -> dict[str, Any] | None:

    connection = _get_connection()

    try:

        conversation = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (
                conversation_id,
                user_id,
            ),
        ).fetchone()

        if conversation is None:
            return None

        messages = connection.execute(
            """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (
                conversation_id,
            ),
        ).fetchall()

        result = _conversation_from_row(
            conversation
        )

        result["messages"] = [
            _message_from_row(row)
            for row in messages
        ]

        return result

    finally:

        connection.close()


def conversation_belongs_to_user(
    conversation_id: str,
    user_id: str,
) -> bool:

    connection = _get_connection()

    try:

        row = connection.execute(
            """
            SELECT 1
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
            """,
            (
                conversation_id,
                user_id,
            ),
        ).fetchone()

        return row is not None

    finally:

        connection.close()


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    language: str = "en",
    evidence: list | None = None,
) -> dict[str, Any]:

    message_id = str(
        uuid.uuid4()
    )

    now = _utc_now()

    evidence_payload = (
        evidence
        if isinstance(
            evidence,
            list,
        )
        else []
    )

    connection = _get_connection()

    try:

        connection.execute(
            """
            INSERT INTO messages (
                id,
                conversation_id,
                role,
                content,
                language,
                evidence_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                str(content or ""),
                language or "en",
                json.dumps(
                    evidence_payload,
                    ensure_ascii=False,
                ),
                now,
            ),
        )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                conversation_id,
            ),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM messages
            WHERE id = ?
            """,
            (
                message_id,
            ),
        ).fetchone()

        return _message_from_row(
            row
        )

    finally:

        connection.close()


def update_conversation_title(
    conversation_id: str,
    user_id: str,
    title: str,
) -> dict[str, Any] | None:

    cleaned_title = (
        str(title or "").strip()
    )

    if not cleaned_title:
        cleaned_title = "New Chat"

    cleaned_title = (
        cleaned_title[:120]
    )

    now = _utc_now()

    connection = _get_connection()

    try:

        cursor = connection.execute(
            """
            UPDATE conversations
            SET
                title = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (
                cleaned_title,
                now,
                conversation_id,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            return None

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (
                conversation_id,
                user_id,
            ),
        ).fetchone()

        return _conversation_from_row(
            row
        )

    finally:

        connection.close()


def delete_conversation(
    conversation_id: str,
    user_id: str,
) -> bool:

    connection = _get_connection()

    try:

        cursor = connection.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (
                conversation_id,
                user_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


def set_conversation_pinned(
    conversation_id: str,
    user_id: str,
    pinned: bool,
) -> dict[str, Any] | None:

    now = _utc_now()

    connection = _get_connection()

    try:

        cursor = connection.execute(
            """
            UPDATE conversations
            SET
                pinned = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (
                1 if pinned else 0,
                now,
                conversation_id,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            return None

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            """,
            (
                conversation_id,
                user_id,
            ),
        ).fetchone()

        return _conversation_from_row(
            row
        )

    finally:

        connection.close()


def get_evidence_locator_cache(
    cache_key: str,
) -> dict[str, Any] | None:

    cache_key = str(
        cache_key or ""
    ).strip()

    if not cache_key:
        return None

    connection = _get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM evidence_source_cache
            WHERE cache_key = ?
            LIMIT 1
            """,
            (
                cache_key,
            ),
        ).fetchone()

        if row is None:
            return None

        try:

            locator = json.loads(
                row["locator_json"]
                or "{}"
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):

            locator = {}

        return {
            "cache_key": row[
                "cache_key"
            ],
            "chunk_id": row[
                "chunk_id"
            ],
            "source_url": row[
                "source_url"
            ],
            "source_title": row[
                "source_title"
            ],
            "source_type": row[
                "source_type"
            ],
            "source_text": row[
                "source_text"
            ],
            "locator": locator,
            "created_at": row[
                "created_at"
            ],
            "updated_at": row[
                "updated_at"
            ],
        }

    finally:

        connection.close()


def save_evidence_locator_cache(
    cache_key: str,
    source_url: str,
    locator: dict[str, Any],
    chunk_id: str | None = None,
    source_title: str | None = None,
    source_type: str | None = None,
    source_text: str | None = None,
) -> dict[str, Any]:

    cache_key = str(
        cache_key or ""
    ).strip()

    source_url = str(
        source_url or ""
    ).strip()

    if not cache_key:
        raise ValueError(
            "cache_key cannot be empty."
        )

    if not source_url:
        raise ValueError(
            "source_url cannot be empty."
        )

    if not isinstance(
        locator,
        dict,
    ):

        locator = {}

    now = _utc_now()

    connection = _get_connection()

    try:

        connection.execute(
            """
            INSERT INTO evidence_source_cache (
                cache_key,
                chunk_id,
                source_url,
                source_title,
                source_type,
                source_text,
                locator_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(cache_key)
            DO UPDATE SET

                chunk_id = excluded.chunk_id,

                source_url = excluded.source_url,

                source_title = excluded.source_title,

                source_type = excluded.source_type,

                source_text = excluded.source_text,

                locator_json = excluded.locator_json,

                updated_at = excluded.updated_at
            """,
            (
                cache_key,
                chunk_id,
                source_url,
                source_title,
                source_type,
                source_text,
                json.dumps(
                    locator,
                    ensure_ascii=False,
                ),
                now,
                now,
            ),
        )

        connection.commit()

        cached = get_evidence_locator_cache(
            cache_key
        )

        return (
            cached
            if cached is not None
            else {
                "cache_key": cache_key,
                "chunk_id": chunk_id,
                "source_url": source_url,
                "source_title": source_title,
                "source_type": source_type,
                "source_text": source_text,
                "locator": locator,
                "created_at": now,
                "updated_at": now,
            }
        )

    finally:

        connection.close()


initialize_database()
