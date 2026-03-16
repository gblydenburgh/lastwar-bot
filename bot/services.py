from __future__ import annotations

from dataclasses import asdict
from typing import Any

from data.lookups import ACCOUNT_TYPES, SQUAD_TYPES, country_codes, language_codes, timezone_choices
from db.repositories import ProfileData


REQUIRED_SESSION_FIELDS = {
    "ingame_name",
    "account_type",
    "country_code",
    "primary_language_code",
    "timezone",
    "availability_start_minutes",
    "availability_end_minutes",
    "squad_a_power",
    "squad_a_type",
}


def validate_minutes(value: int) -> int:
    if not 0 <= value <= 1439:
        raise ValueError("Availability minutes must be between 0 and 1439.")
    return value


def validate_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if normalized.get("account_type") not in ACCOUNT_TYPES:
        raise ValueError("Account type must be one of: main, alt.")
    if normalized.get("country_code") not in country_codes():
        raise ValueError("Country code must be a valid ISO 3166-1 alpha-2 code.")
    if normalized.get("primary_language_code") not in language_codes():
        raise ValueError("Language code is not supported by this app.")
    if normalized.get("timezone") not in set(timezone_choices()):
        raise ValueError("Timezone must be a valid IANA timezone.")

    normalized["availability_start_minutes"] = validate_minutes(
        int(normalized["availability_start_minutes"])
    )
    normalized["availability_end_minutes"] = validate_minutes(
        int(normalized["availability_end_minutes"])
    )

    for slot in ("a", "b", "c", "d"):
        power_key = f"squad_{slot}_power"
        type_key = f"squad_{slot}_type"
        power = normalized.get(power_key)
        squad_type = normalized.get(type_key)

        if slot == "a":
            if power is None or squad_type is None:
                raise ValueError("Squad A requires both power and type.")
        elif (power is None) != (squad_type is None):
            raise ValueError(f"Squad {slot.upper()} must have both power and type or neither.")

        if power is not None:
            power = int(power)
            if power < 0:
                raise ValueError(f"Squad {slot.upper()} power must be zero or greater.")
            normalized[power_key] = power

        if squad_type is not None and squad_type not in SQUAD_TYPES:
            raise ValueError(f"Squad {slot.upper()} type must be one of: {', '.join(SQUAD_TYPES)}.")

    missing = REQUIRED_SESSION_FIELDS - normalized.keys()
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}.")

    return normalized


def build_profile_data(
    *,
    discord_user_id: int,
    discord_display_name: str,
    payload: dict[str, Any],
) -> ProfileData:
    normalized = validate_profile_payload(payload)
    return ProfileData(
        discord_user_id=discord_user_id,
        discord_display_name=discord_display_name,
        ingame_name=normalized["ingame_name"],
        account_type=normalized["account_type"],
        country_code=normalized["country_code"],
        primary_language_code=normalized["primary_language_code"],
        timezone=normalized["timezone"],
        availability_start_minutes=normalized["availability_start_minutes"],
        availability_end_minutes=normalized["availability_end_minutes"],
        squad_a_power=normalized["squad_a_power"],
        squad_a_type=normalized["squad_a_type"],
        squad_b_power=normalized.get("squad_b_power"),
        squad_b_type=normalized.get("squad_b_type"),
        squad_c_power=normalized.get("squad_c_power"),
        squad_c_type=normalized.get("squad_c_type"),
        squad_d_power=normalized.get("squad_d_power"),
        squad_d_type=normalized.get("squad_d_type"),
    )


def profile_row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def merge_profile_update(existing: Any, updates: dict[str, Any]) -> dict[str, Any]:
    payload = asdict(
        ProfileData(
            discord_user_id=existing["discord_user_id"],
            discord_display_name=updates.get("discord_display_name", existing["discord_display_name"]),
            ingame_name=updates.get("ingame_name", existing["ingame_name"]),
            account_type=updates.get("account_type", existing["account_type"]),
            country_code=updates.get("country_code", existing["country_code"]),
            primary_language_code=updates.get(
                "primary_language_code", existing["primary_language_code"]
            ),
            timezone=updates.get("timezone", existing["timezone"]),
            availability_start_minutes=updates.get(
                "availability_start_minutes", existing["availability_start_minutes"]
            ),
            availability_end_minutes=updates.get(
                "availability_end_minutes", existing["availability_end_minutes"]
            ),
            squad_a_power=updates.get("squad_a_power", existing["squad_a_power"]),
            squad_a_type=updates.get("squad_a_type", existing["squad_a_type"]),
            squad_b_power=updates.get("squad_b_power", existing["squad_b_power"]),
            squad_b_type=updates.get("squad_b_type", existing["squad_b_type"]),
            squad_c_power=updates.get("squad_c_power", existing["squad_c_power"]),
            squad_c_type=updates.get("squad_c_type", existing["squad_c_type"]),
            squad_d_power=updates.get("squad_d_power", existing["squad_d_power"]),
            squad_d_type=updates.get("squad_d_type", existing["squad_d_type"]),
        )
    )
    payload.pop("discord_user_id", None)
    return payload
