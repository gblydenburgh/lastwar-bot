from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import json

from db.connection import DatabaseManager


def utc_now() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(ts: str) -> datetime:
    """Convert ISO string back to datetime."""
    return datetime.fromisoformat(ts)


class SessionRepository:
    """
    Handles registration sessions and unregistered tracking.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Registration Sessions
    # ---------------------------------------------------------

    def create_session(self, discord_user_id: str) -> None:
        """Start a new registration session."""

        now = utc_now()
        expires = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(
            microsecond=0
        ).isoformat()

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO registration_sessions (
                    discord_user_id,
                    current_step,
                    session_data_json,
                    started_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    discord_user_id,
                    "start",
                    "{}",
                    now,
                    expires,
                ),
            )

    def get_session(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch session if it exists and is not expired."""

        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM registration_sessions
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

        if not row:
            return None

        if parse_time(row["expires_at"]) < datetime.now(timezone.utc):
            self.delete_session(discord_user_id)
            return None

        row["session_data_json"] = json.loads(row["session_data_json"])
        return row

    def update_session_data(
        self,
        discord_user_id: str,
        step: str,
        data: Dict[str, Any],
    ) -> None:
        """Update session JSON and current step."""

        with self.db.transaction() as conn:

            row = conn.execute(
                """
                SELECT session_data_json
                FROM registration_sessions
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

            if not row:
                raise ValueError("Session not found")

            existing = json.loads(row["session_data_json"])
            existing.update(data)

            conn.execute(
                """
                UPDATE registration_sessions
                SET current_step = ?,
                    session_data_json = ?
                WHERE discord_user_id = ?
                """,
                (
                    step,
                    json.dumps(existing),
                    discord_user_id,
                ),
            )

    def delete_session(self, discord_user_id: str) -> None:
        """Delete a completed or abandoned session."""

        with self.db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM registration_sessions
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            )

    # ---------------------------------------------------------
    # Unregistered Tracking
    # ---------------------------------------------------------

    def add_unregistered_user(self, discord_user_id: str) -> None:
        """Add user to reminder tracking."""

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO unregistered_tracking (
                    discord_user_id,
                    joined_at,
                    last_reminder_at,
                    reminder_count
                )
                VALUES (?, ?, NULL, 0)
                """,
                (
                    discord_user_id,
                    utc_now(),
                ),
            )

    def remove_unregistered_user(self, discord_user_id: str) -> None:
        """Remove user from reminder tracking."""

        with self.db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM unregistered_tracking
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            )

    def update_reminder(self, discord_user_id: str) -> None:
        """Update reminder timestamp and increment counter."""

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE unregistered_tracking
                SET last_reminder_at = ?,
                    reminder_count = reminder_count + 1
                WHERE discord_user_id = ?
                """,
                (
                    utc_now(),
                    discord_user_id,
                ),
            )

    def get_unregistered_users(self) -> List[Dict[str, Any]]:
        """Return all users awaiting registration."""

        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM unregistered_tracking
                """
            ).fetchall()

        return list(rows)
