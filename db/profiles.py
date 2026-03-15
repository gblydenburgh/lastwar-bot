from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from db.connection import DatabaseManager


def utc_now() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class SquadColumnSet:
    """Column names for a squad slot."""
    power: str
    squad_type: str


SQUAD_COLUMNS: dict[str, SquadColumnSet] = {
    "A": SquadColumnSet(power="squad_a_power", squad_type="squad_a_type"),
    "B": SquadColumnSet(power="squad_b_power", squad_type="squad_b_type"),
    "C": SquadColumnSet(power="squad_c_power", squad_type="squad_c_type"),
    "D": SquadColumnSet(power="squad_d_power", squad_type="squad_d_type"),
}

ALLOWED_SQUAD_TYPES: set[str] = {"tank", "air", "missile", "mixed"}


class ProfileRepository:
    """
    Data access layer for alliance member profiles.

    Simplified design rules:
    - one profile per Discord user in V1
    - current values only
    - no soft delete
    - no name history
    - no squad history
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_profile(self, profile_data: dict[str, Any]) -> int:
        """
        Create a profile and return its database id.

        Expected keys:
        - discord_user_id
        - discord_display_name
        - ingame_name
        - country_code
        - primary_language_code
        - timezone
        - availability_start_minutes
        - availability_end_minutes
        - squad_a_power
        - squad_a_type
        - optional squad_b_power / squad_b_type
        - optional squad_c_power / squad_c_type
        - optional squad_d_power / squad_d_type
        - optional account_type
        """
        self._validate_profile_payload(profile_data)

        timestamp: str = utc_now()

        with self.db.transaction() as conn:
            result = conn.execute(
                """
                INSERT INTO profiles (
                    discord_user_id,
                    discord_display_name,
                    ingame_name,
                    country_code,
                    primary_language_code,
                    timezone,
                    availability_start_minutes,
                    availability_end_minutes,
                    squad_a_power,
                    squad_a_type,
                    squad_b_power,
                    squad_b_type,
                    squad_c_power,
                    squad_c_type,
                    squad_d_power,
                    squad_d_type,
                    account_type,
                    created_at,
                    last_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_data["discord_user_id"],
                    profile_data.get("discord_display_name"),
                    profile_data["ingame_name"],
                    profile_data["country_code"],
                    profile_data["primary_language_code"],
                    profile_data["timezone"],
                    profile_data["availability_start_minutes"],
                    profile_data["availability_end_minutes"],
                    profile_data["squad_a_power"],
                    profile_data["squad_a_type"].lower(),
                    profile_data.get("squad_b_power"),
                    self._normalize_optional_squad_type(profile_data.get("squad_b_type")),
                    profile_data.get("squad_c_power"),
                    self._normalize_optional_squad_type(profile_data.get("squad_c_type")),
                    profile_data.get("squad_d_power"),
                    self._normalize_optional_squad_type(profile_data.get("squad_d_type")),
                    profile_data.get("account_type", "main"),
                    timestamp,
                    timestamp,
                ),
            )
            return int(result.lastrowid)

    def get_profile_by_id(self, profile_id: int) -> dict[str, Any] | None:
        """Return a single profile by id."""
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM profiles
                WHERE id = ?
                """,
                (profile_id,),
            ).fetchone()

    def get_profile_by_discord_user_id(self, discord_user_id: str) -> dict[str, Any] | None:
        """Return the V1 profile for a Discord user."""
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM profiles
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()

    def get_profile_by_ingame_name(self, ingame_name: str) -> dict[str, Any] | None:
        """Return a single profile by in-game name."""
        with self.db.connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM profiles
                WHERE ingame_name = ?
                """,
                (ingame_name,),
            ).fetchone()

    def list_profiles(self) -> list[dict[str, Any]]:
        """Return all profiles ordered for roster-style display."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM profiles
                ORDER BY ingame_name COLLATE NOCASE
                """
            ).fetchall()
            return list(rows)

    def update_profile(
        self,
        discord_user_id: str,
        updates: dict[str, Any],
    ) -> None:
        """
        Update allowed profile fields for an existing user profile.

        This intentionally supports partial updates only for mutable columns.
        """
        if not updates:
            return

        allowed_fields: set[str] = {
            "discord_display_name",
            "ingame_name",
            "country_code",
            "primary_language_code",
            "timezone",
            "availability_start_minutes",
            "availability_end_minutes",
            "squad_a_power",
            "squad_a_type",
            "squad_b_power",
            "squad_b_type",
            "squad_c_power",
            "squad_c_type",
            "squad_d_power",
            "squad_d_type",
            "account_type",
        }

        invalid_fields: set[str] = set(updates) - allowed_fields
        if invalid_fields:
            invalid_list: str = ", ".join(sorted(invalid_fields))
            raise ValueError(f"Unsupported profile update fields: {invalid_list}")

        normalized_updates: dict[str, Any] = dict(updates)

        for squad_type_field in ("squad_a_type", "squad_b_type", "squad_c_type", "squad_d_type"):
            if squad_type_field in normalized_updates and normalized_updates[squad_type_field] is not None:
                normalized_updates[squad_type_field] = str(normalized_updates[squad_type_field]).lower()
                self._validate_squad_type(normalized_updates[squad_type_field])

        if "availability_start_minutes" in normalized_updates:
            self._validate_minute_value(
                "availability_start_minutes",
                normalized_updates["availability_start_minutes"],
            )

        if "availability_end_minutes" in normalized_updates:
            self._validate_minute_value(
                "availability_end_minutes",
                normalized_updates["availability_end_minutes"],
            )

        assignments: list[str] = []
        values: list[Any] = []

        for field_name, field_value in normalized_updates.items():
            assignments.append(f"{field_name} = ?")
            values.append(field_value)

        assignments.append("last_updated_at = ?")
        values.append(utc_now())
        values.append(discord_user_id)

        sql: str = f"""
            UPDATE profiles
            SET {", ".join(assignments)}
            WHERE discord_user_id = ?
        """

        with self.db.transaction() as conn:
            result = conn.execute(sql, tuple(values))
            if result.rowcount == 0:
                raise ValueError("Profile not found")

    def update_squad(
        self,
        discord_user_id: str,
        squad_slot: str,
        power: int | None,
        squad_type: str | None,
    ) -> None:
        """
        Update a single squad slot for the user's profile.

        Rules:
        - Squad A is required and should not be set to null values.
        - Squads B/C/D are optional and may be cleared by setting both values to None.
        """
        slot: str = squad_slot.upper()
        if slot not in SQUAD_COLUMNS:
            raise ValueError("Squad slot must be one of: A, B, C, D")

        columns: SquadColumnSet = SQUAD_COLUMNS[slot]

        if slot == "A":
            if power is None or squad_type is None:
                raise ValueError("Squad A requires both power and squad_type")
        else:
            if (power is None) != (squad_type is None):
                raise ValueError(f"Squad {slot} requires both power and squad_type, or neither")

        if power is not None and power < 0:
            raise ValueError("Squad power must be 0 or greater")

        normalized_type: str | None = None
        if squad_type is not None:
            normalized_type = squad_type.lower()
            self._validate_squad_type(normalized_type)

        with self.db.transaction() as conn:
            result = conn.execute(
                f"""
                UPDATE profiles
                SET
                    {columns.power} = ?,
                    {columns.squad_type} = ?,
                    last_updated_at = ?
                WHERE discord_user_id = ?
                """,
                (power, normalized_type, utc_now(), discord_user_id),
            )
            if result.rowcount == 0:
                raise ValueError("Profile not found")

    def delete_profile(self, discord_user_id: str) -> None:
        """
        Hard delete a profile.

        This follows the simplified design. No recycle bin, no ghost of bad schema decisions past.
        """
        with self.db.transaction() as conn:
            result = conn.execute(
                """
                DELETE FROM profiles
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            )
            if result.rowcount == 0:
                raise ValueError("Profile not found")

    def profile_exists(self, discord_user_id: str) -> bool:
        """Return True if a profile exists for the Discord user."""
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT 1 AS exists_flag
                FROM profiles
                WHERE discord_user_id = ?
                LIMIT 1
                """,
                (discord_user_id,),
            ).fetchone()
            return bool(row and row["exists_flag"] == 1)

    def _validate_profile_payload(self, profile_data: dict[str, Any]) -> None:
        """Validate required profile fields before insert."""
        required_fields: tuple[str, ...] = (
            "discord_user_id",
            "ingame_name",
            "country_code",
            "primary_language_code",
            "timezone",
            "availability_start_minutes",
            "availability_end_minutes",
            "squad_a_power",
            "squad_a_type",
        )

        missing_fields: list[str] = [field for field in required_fields if field not in profile_data]
        if missing_fields:
            missing: str = ", ".join(missing_fields)
            raise ValueError(f"Missing required profile fields: {missing}")

        self._validate_minute_value("availability_start_minutes", profile_data["availability_start_minutes"])
        self._validate_minute_value("availability_end_minutes", profile_data["availability_end_minutes"])

        if int(profile_data["squad_a_power"]) < 0:
            raise ValueError("squad_a_power must be 0 or greater")

        self._validate_squad_type(str(profile_data["squad_a_type"]).lower())

        for optional_slot in ("b", "c", "d"):
            power_key: str = f"squad_{optional_slot}_power"
            type_key: str = f"squad_{optional_slot}_type"

            has_power: bool = profile_data.get(power_key) is not None
            has_type: bool = profile_data.get(type_key) is not None

            if has_power != has_type:
                raise ValueError(
                    f"{power_key} and {type_key} must both be set or both be None"
                )

            if has_power:
                if int(profile_data[power_key]) < 0:
                    raise ValueError(f"{power_key} must be 0 or greater")
                self._validate_squad_type(str(profile_data[type_key]).lower())

    def _validate_squad_type(self, squad_type: str) -> None:
        """Validate squad type value."""
        if squad_type not in ALLOWED_SQUAD_TYPES:
            allowed: str = ", ".join(sorted(ALLOWED_SQUAD_TYPES))
            raise ValueError(f"Invalid squad type '{squad_type}'. Allowed values: {allowed}")

    def _validate_minute_value(self, field_name: str, value: Any) -> None:
        """Validate minute-of-day values."""
        minute_value: int = int(value)
        if minute_value < 0 or minute_value > 1439:
            raise ValueError(f"{field_name} must be between 0 and 1439")

    def _normalize_optional_squad_type(self, value: Any) -> str | None:
        """Normalize optional squad type values."""
        if value is None:
            return None

        normalized: str = str(value).lower()
        self._validate_squad_type(normalized)
        return normalized