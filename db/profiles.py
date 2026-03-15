from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from db.connection import DatabaseManager


def utc_now() -> str:
    """Return current UTC timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ProfileRepository:
    """
    Data access layer for profiles.

    Handles:
    - profile creation
    - squad updates
    - profile lookup
    - soft delete
    - restore
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Creation
    # ---------------------------------------------------------

    def create_profile(self, data: Dict[str, Any]) -> int:
        """
        Insert a new profile.

        Returns the new profile_id.
        """

        timestamp = utc_now()

        with self.db.transaction() as conn:

            # purge soft-deleted profile with same name
            existing = conn.execute(
                """
                SELECT profile_id
                FROM profiles
                WHERE ingame_name = ?
                  AND deleted_at IS NOT NULL
                """,
                (data["ingame_name"],),
            ).fetchone()

            if existing:
                conn.execute(
                    "DELETE FROM profiles WHERE profile_id = ?",
                    (existing["profile_id"],),
                )

            result = conn.execute(
                """
                INSERT INTO profiles (
                    discord_user_id,
                    discord_display_name,
                    ingame_name,
                    account_type,
                    country_code,
                    primary_language_code,
                    secondary_language_code,
                    timezone,
                    availability_start_min,
                    availability_end_min,
                    squad_a_power,
                    squad_a_type,
                    squad_b_power,
                    squad_b_type,
                    squad_c_power,
                    squad_c_type,
                    squad_d_power,
                    squad_d_type,
                    created_at,
                    last_squad_update_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["discord_user_id"],
                    data["discord_display_name"],
                    data["ingame_name"],
                    data.get("account_type", "main"),
                    data["country_code"],
                    data["primary_language_code"],
                    data.get("secondary_language_code"),
                    data["timezone"],
                    data["availability_start_min"],
                    data["availability_end_min"],
                    data["squad_a_power"],
                    data["squad_a_type"],
                    data.get("squad_b_power"),
                    data.get("squad_b_type"),
                    data.get("squad_c_power"),
                    data.get("squad_c_type"),
                    data.get("squad_d_power"),
                    data.get("squad_d_type"),
                    timestamp,
                    timestamp,
                ),
            )

        return int(result.lastrowid)

    # ---------------------------------------------------------
    # Lookups
    # ---------------------------------------------------------

    def get_profile_by_ingame_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM profiles
                WHERE ingame_name = ?
                  AND deleted_at IS NULL
                """,
                (name,),
            ).fetchone()

    def get_profiles_by_discord_user(self, discord_user_id: str) -> List[Dict[str, Any]]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM profiles
                WHERE discord_user_id = ?
                  AND deleted_at IS NULL
                ORDER BY account_type, ingame_name
                """,
                (discord_user_id,),
            ).fetchall()

        return list(rows)

    # ---------------------------------------------------------
    # Squad Updates
    # ---------------------------------------------------------

    def update_squad(
        self,
        profile_id: int,
        squad_slot: str,
        new_power: int,
        new_type: str,
    ) -> None:

        column_power = f"squad_{squad_slot.lower()}_power"
        column_type = f"squad_{squad_slot.lower()}_type"

        with self.db.transaction() as conn:

            profile = conn.execute(
                "SELECT * FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()

            if not profile:
                raise ValueError("Profile not found")

            old_power = profile[column_power]
            old_type = profile[column_type]

            conn.execute(
                f"""
                UPDATE profiles
                SET {column_power} = ?,
                    {column_type} = ?,
                    last_squad_update_at = ?
                WHERE profile_id = ?
                """,
                (
                    new_power,
                    new_type,
                    utc_now(),
                    profile_id,
                ),
            )

            conn.execute(
                """
                INSERT INTO squad_history (
                    profile_id,
                    squad_slot,
                    old_power,
                    new_power,
                    old_type,
                    new_type,
                    changed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    squad_slot,
                    old_power,
                    new_power,
                    old_type,
                    new_type,
                    utc_now(),
                ),
            )

    # ---------------------------------------------------------
    # Name Change
    # ---------------------------------------------------------

    def update_ingame_name(self, profile_id: int, new_name: str) -> None:

        with self.db.transaction() as conn:

            profile = conn.execute(
                "SELECT ingame_name FROM profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()

            if not profile:
                raise ValueError("Profile not found")

            old_name = profile["ingame_name"]

            conn.execute(
                "UPDATE profiles SET ingame_name = ? WHERE profile_id = ?",
                (new_name, profile_id),
            )

            conn.execute(
                """
                INSERT INTO name_history (
                    profile_id,
                    old_name,
                    changed_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    profile_id,
                    old_name,
                    utc_now(),
                ),
            )

    # ---------------------------------------------------------
    # Soft Delete
    # ---------------------------------------------------------

    def soft_delete(self, profile_id: int) -> None:

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE profiles
                SET deleted_at = ?
                WHERE profile_id = ?
                """,
                (
                    utc_now(),
                    profile_id,
                ),
            )

    # ---------------------------------------------------------
    # Restore
    # ---------------------------------------------------------

    def restore(self, profile_id: int) -> None:

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE profiles
                SET deleted_at = NULL
                WHERE profile_id = ?
                """,
                (profile_id,),
            )
