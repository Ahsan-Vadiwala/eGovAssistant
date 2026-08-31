
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .models import GrievanceState, GrievanceStage


DEFAULT_STATE_DB_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "data" / "egovassist.db"
)

STATE_DB_PATH = Path(
    os.getenv(
        "EGOVASSIST_GRIEVANCE_DB_PATH",
        str(DEFAULT_STATE_DB_PATH),
    )
)


def _get_connection() -> sqlite3.Connection:
    STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(STATE_DB_PATH), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_grievance_state_table() -> None:
    """Initialize the grievance state table in the database."""
    connection = _get_connection()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS grievance_states (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_grievance_states_user
            ON grievance_states (user_id);
            """
        )
        connection.commit()
    finally:
        connection.close()


def save_grievance_state(state: GrievanceState) -> None:
    """Save grievance state to database."""
    state.updated_at = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()

    connection = _get_connection()
    try:
        connection.execute(
            """
            INSERT INTO grievance_states (
                conversation_id, user_id, state_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                user_id = excluded.user_id,
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (
                state.conversation_id,
                state.user_id,
                json.dumps(state.to_dict(), ensure_ascii=False),
                state.created_at,
                state.updated_at,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def load_grievance_state(conversation_id: str) -> GrievanceState | None:
    """Load grievance state from database."""
    connection = _get_connection()
    try:
        row = connection.execute(
            "SELECT state_json FROM grievance_states WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()

        if row is None:
            return None

        data = json.loads(row["state_json"])
        return GrievanceState.from_dict(data)
    finally:
        connection.close()


def delete_grievance_state(conversation_id: str) -> bool:
    """Delete grievance state from database."""
    connection = _get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM grievance_states WHERE conversation_id = ?",
            (conversation_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def get_user_grievance_states(user_id: str) -> list[GrievanceState]:
    """Get all grievance states for a user."""
    connection = _get_connection()
    try:
        rows = connection.execute(
            "SELECT state_json FROM grievance_states WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()

        return [GrievanceState.from_dict(json.loads(row["state_json"])) for row in rows]
    finally:
        connection.close()


initialize_grievance_state_table()
