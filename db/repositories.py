from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
import sqlite3
from typing import Any

from db.connection import get_connection


@dataclass(slots=True)
class SquadData:
    power: int | None
    squad_type: str | None


@dataclass(slots=True)
class ProfileData:
    discord_user_id: int
    discord_display_name: str
    ingame_name: str
    account_type: str
    country_code: str
    primary_language_code: str
    timezone: str
    availability_start_minutes: int
    availability_end_minutes: int
    squad_a_power: int
    squad_a_type: str
    squad_b_power: int | None = None
    squad_b_type: str | None = None
    squad_c_power: int | None = None
    squad_c_type: str | None = None
    squad_d_power: int | None = None
    squad_d_type: str | None = None


@dataclass(slots=True)
class RegistrationSession:
    discord_user_id: int
    step: str
    session_data: dict[str, Any]
    created_at: str
    expires_at: str


def utcnow() -> datetime:
    return datetime.now(UTC)


def _iso_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


class ProfileRepository:
    def get_by_user_id(self, discord_user_id: int) -> sqlite3.Row | None:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM profiles WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()

    def upsert(self, profile: ProfileData) -> None:
        payload = asdict(profile)
        columns = ", ".join(payload)
        placeholders = ", ".join("?" for _ in payload)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in payload
            if column != "discord_user_id"
        )
        with get_connection() as conn:
            conn.execute(
                f"""
                INSERT INTO profiles ({columns})
                VALUES ({placeholders})
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    {updates},
                    updated_at = CURRENT_TIMESTAMP
                """,
                tuple(payload.values()),
            )

    def delete(self, discord_user_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM profiles WHERE discord_user_id = ?",
                (discord_user_id,),
            )
            return cursor.rowcount > 0

    def list_roster(self) -> list[sqlite3.Row]:
        with get_connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM profiles
                ORDER BY ingame_name COLLATE NOCASE
                """
            ).fetchall()

    def squad_power_rankings(self) -> list[sqlite3.Row]:
        with get_connection() as conn:
            return conn.execute(
                """
                SELECT
                    discord_user_id,
                    ingame_name,
                    COALESCE(squad_a_power, 0) + COALESCE(squad_b_power, 0) +
                    COALESCE(squad_c_power, 0) + COALESCE(squad_d_power, 0) AS total_power
                FROM profiles
                ORDER BY total_power DESC, ingame_name COLLATE NOCASE
                """
            ).fetchall()

    def timezone_distribution(self) -> list[sqlite3.Row]:
        with get_connection() as conn:
            return conn.execute(
                """
                SELECT timezone, COUNT(*) AS member_count
                FROM profiles
                GROUP BY timezone
                ORDER BY member_count DESC, timezone
                """
            ).fetchall()


class RegistrationSessionRepository:
    def cleanup_expired(self) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM registration_sessions WHERE expires_at <= ?",
                (_iso_timestamp(utcnow()),),
            )
            return cursor.rowcount

    def get(self, discord_user_id: int) -> RegistrationSession | None:
        self.cleanup_expired()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM registration_sessions WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()
        if row is None:
            return None
        return RegistrationSession(
            discord_user_id=row["discord_user_id"],
            step=row["step"],
            session_data=json.loads(row["session_data_json"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    def create_or_reset(self, discord_user_id: int, ttl_hours: int) -> RegistrationSession:
        now = utcnow()
        expires_at = now + timedelta(hours=ttl_hours)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO registration_sessions (discord_user_id, step, session_data_json, created_at, expires_at)
                VALUES (?, 'identity', '{}', ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    step = 'identity',
                    session_data_json = '{}',
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (discord_user_id, _iso_timestamp(now), _iso_timestamp(expires_at)),
            )
        return self.get(discord_user_id)  # type: ignore[return-value]

    def save_step(
        self,
        discord_user_id: int,
        step: str,
        session_data: dict[str, Any],
        ttl_hours: int,
    ) -> None:
        expires_at = utcnow() + timedelta(hours=ttl_hours)
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE registration_sessions
                SET step = ?, session_data_json = ?, expires_at = ?
                WHERE discord_user_id = ?
                """,
                (
                    step,
                    json.dumps(session_data, sort_keys=True),
                    _iso_timestamp(expires_at),
                    discord_user_id,
                ),
            )

    def delete(self, discord_user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM registration_sessions WHERE discord_user_id = ?",
                (discord_user_id,),
            )


class UnregisteredTrackingRepository:
    def track_join(self, discord_user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO unregistered_tracking (discord_user_id, joined_at, last_reminder_at, reminder_count)
                VALUES (?, ?, NULL, 0)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    joined_at = excluded.joined_at
                """,
                (discord_user_id, _iso_timestamp(utcnow())),
            )

    def mark_reminder_sent(self, discord_user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE unregistered_tracking
                SET last_reminder_at = ?, reminder_count = reminder_count + 1
                WHERE discord_user_id = ?
                """,
                (_iso_timestamp(utcnow()), discord_user_id),
            )

    def remove(self, discord_user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM unregistered_tracking WHERE discord_user_id = ?",
                (discord_user_id,),
            )

    def list_all(self) -> list[sqlite3.Row]:
        with get_connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM unregistered_tracking
                ORDER BY joined_at ASC
                """
            ).fetchall()
