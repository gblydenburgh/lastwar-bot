from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from db.connection import DatabaseManager


DEFAULT_SESSION_TTL_HOURS: int = 3


def utc_now() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_utc_timestamp(timestamp: str) -> datetime:
    """Parse an ISO 8601 timestamp string."""
    return datetime.fromisoformat(timestamp)


class SessionRepository:
    """
    Data access layer for:
    - registration_sessions
    - unregistered_tracking
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Registration sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        discord_user_id: str,
        step: str = "start",
        session_data: dict[str, Any] | None = None,
        ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
    ) -> None:
        """
        Create or replace a registration session for a Discord user.
        """
        now: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        expires_at: datetime = now + timedelta(hours=ttl_hours)
        payload: dict[str, Any] = session_data or {}

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO registration_sessions (
                    discord_user_id,
                    session_data_json,
                    step,
                    created_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    discord_user_id,
                    json.dumps(payload, separators=(",", ":"), sort_keys=True),
                    step,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def get_session(self, discord_user_id: str) -> dict[str, Any] | None:
        """
        Return a registration session if it exists and has not expired.

        Expired sessions are deleted automatically.
        """
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM registration_sessions
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

        if row is None:
            return None

        if self._is_expired(row["expires_at"]):
            self.delete_session(discord_user_id)
            return None

        hydrated: dict[str, Any] = dict(row)
        hydrated["session_data_json"] = json.loads(hydrated["session_data_json"])
        return hydrated

    def update_session(
        self,
        discord_user_id: str,
        *,
        step: str | None = None,
        session_data: dict[str, Any] | None = None,
        extend_ttl_hours: int | None = None,
    ) -> None:
        """
        Update session step, merge session data, and optionally extend expiry.
        """
        current_session: dict[str, Any] | None = self.get_session(discord_user_id)
        if current_session is None:
            raise ValueError("Session not found")

        merged_data: dict[str, Any] = dict(current_session["session_data_json"])
        if session_data:
            merged_data.update(session_data)

        new_step: str = step if step is not None else str(current_session["step"])
        new_expires_at: str = str(current_session["expires_at"])

        if extend_ttl_hours is not None:
            new_expires_at = (
                datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=extend_ttl_hours)
            ).isoformat()

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE registration_sessions
                SET
                    session_data_json = ?,
                    step = ?,
                    expires_at = ?
                WHERE discord_user_id = ?
                """,
                (
                    json.dumps(merged_data, separators=(",", ":"), sort_keys=True),
                    new_step,
                    new_expires_at,
                    discord_user_id,
                ),
            )

    def set_session_step(self, discord_user_id: str, step: str) -> None:
        """Update only the current registration step."""
        self.update_session(discord_user_id, step=step)

    def merge_session_data(self, discord_user_id: str, session_data: dict[str, Any]) -> None:
        """Merge values into existing session JSON data."""
        self.update_session(discord_user_id, session_data=session_data)

    def delete_session(self, discord_user_id: str) -> None:
        """Delete a registration session."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM registration_sessions
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            )

    def delete_expired_sessions(self) -> int:
        """Delete all expired registration sessions and return the number removed."""
        now: str = utc_now()

        with self.db.transaction() as conn:
            rows = conn.execute(
                """
                SELECT discord_user_id
                FROM registration_sessions
                WHERE expires_at <= ?
                """,
                (now,),
            ).fetchall()

            conn.execute(
                """
                DELETE FROM registration_sessions
                WHERE expires_at <= ?
                """,
                (now,),
            )

        return len(rows)

    # ------------------------------------------------------------------
    # Unregistered tracking
    # ------------------------------------------------------------------

    def add_unregistered_user(self, discord_user_id: str) -> None:
        """
        Add a user to unregistered reminder tracking.

        Existing rows are preserved so reminder counters do not reset accidentally.
        """
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO unregistered_tracking (
                    discord_user_id,
                    joined_at,
                    last_reminder_at,
                    reminder_count
                )
                VALUES (?, ?, NULL, 0)
                """,
                (discord_user_id, utc_now()),
            )

    def get_unregistered_user(self, discord_user_id: str) -> dict[str, Any] | None:
        """Return a single unregistered tracking row."""
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM unregistered_tracking
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

    def list_unregistered_users(self) -> list[dict[str, Any]]:
        """Return all users currently tracked for reminders."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM unregistered_tracking
                ORDER BY joined_at ASC
                """
            ).fetchall()
            return list(rows)

    def increment_reminder(self, discord_user_id: str) -> None:
        """Increment reminder count and stamp the last reminder time."""
        with self.db.transaction() as conn:
            result = conn.execute(
                """
                UPDATE unregistered_tracking
                SET
                    last_reminder_at = ?,
                    reminder_count = reminder_count + 1
                WHERE discord_user_id = ?
                """,
                (utc_now(), discord_user_id),
            )
            if result.rowcount == 0:
                raise ValueError("Unregistered tracking row not found")

    def remove_unregistered_user(self, discord_user_id: str) -> None:
        """Remove a user from unregistered reminder tracking."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                DELETE FROM unregistered_tracking
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_expired(self, expires_at: str) -> bool:
        """Return True if the supplied expiry timestamp is in the past."""
        return parse_utc_timestamp(expires_at) <= datetime.now(timezone.utc)