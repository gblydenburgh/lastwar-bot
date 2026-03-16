from __future__ import annotations

from dataclasses import dataclass
import os


def _optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


@dataclass(slots=True)
class Settings:
    discord_token: str
    guild_id: int | None
    unregistered_role_id: int | None
    member_role_id: int | None
    admin_role_id: int | None
    registration_channel_id: int | None
    session_ttl_hours: int = 24

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required")

        return cls(
            discord_token=token,
            guild_id=_optional_int(os.getenv("DISCORD_GUILD_ID")),
            unregistered_role_id=_optional_int(os.getenv("UNREGISTERED_ROLE_ID")),
            member_role_id=_optional_int(os.getenv("MEMBER_ROLE_ID")),
            admin_role_id=_optional_int(os.getenv("ADMIN_ROLE_ID")),
            registration_channel_id=_optional_int(os.getenv("REGISTRATION_CHANNEL_ID")),
            session_ttl_hours=int(os.getenv("REGISTRATION_SESSION_TTL_HOURS", "24")),
        )
