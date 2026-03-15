from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from db.profiles import ProfileRepository
from db.sessions import SessionRepository


class RegistrationWorkflow:
    """
    Handles the step-by-step registration process.
    """

    def __init__(
        self,
        profiles: ProfileRepository,
        sessions: SessionRepository,
    ) -> None:
        self.profiles = profiles
        self.sessions = sessions

    # ---------------------------------------------------------
    # Start Registration
    # ---------------------------------------------------------

    def start(self, discord_user_id: str) -> None:
        """
        Begin a registration session.
        """
        self.sessions.create_session(discord_user_id)

    # ---------------------------------------------------------
    # Get Current Step
    # ---------------------------------------------------------

    def get_current_step(self, discord_user_id: str) -> Optional[str]:

        session = self.sessions.get_session(discord_user_id)

        if not session:
            return None

        return session["current_step"]

    # ---------------------------------------------------------
    # Store Step Data
    # ---------------------------------------------------------

    def store_step_data(
        self,
        discord_user_id: str,
        step: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Save user input and move workflow to next step.
        """

        self.sessions.update_session_data(
            discord_user_id=discord_user_id,
            step=step,
            data=data,
        )

    # ---------------------------------------------------------
    # Finalize Registration
    # ---------------------------------------------------------

    def finalize_registration(
        self,
        discord_user_id: str,
        discord_display_name: str,
    ) -> int:
        """
        Convert session JSON into a profile row.
        """

        session = self.sessions.get_session(discord_user_id)

        if not session:
            raise ValueError("Registration session not found")

        data: Dict[str, Any] = session["session_data_json"]

        profile_data = {
            "discord_user_id": discord_user_id,
            "discord_display_name": discord_display_name,
            "ingame_name": data["ingame_name"],
            "account_type": data.get("account_type", "main"),
            "country_code": data["country_code"],
            "primary_language_code": data["primary_language_code"],
            "secondary_language_code": data.get("secondary_language_code"),
            "timezone": data["timezone"],
            "availability_start_min": data["availability_start_min"],
            "availability_end_min": data["availability_end_min"],
            "squad_a_power": data["squad_a_power"],
            "squad_a_type": data["squad_a_type"],
            "squad_b_power": data.get("squad_b_power"),
            "squad_b_type": data.get("squad_b_type"),
            "squad_c_power": data.get("squad_c_power"),
            "squad_c_type": data.get("squad_c_type"),
            "squad_d_power": data.get("squad_d_power"),
            "squad_d_type": data.get("squad_d_type"),
        }

        profile_id = self.profiles.create_profile(profile_data)

        # remove from reminder tracking
        self.sessions.remove_unregistered_user(discord_user_id)

        # destroy session
        self.sessions.delete_session(discord_user_id)

        return profile_id
