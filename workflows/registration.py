from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from db.profiles import ProfileRepository
from db.sessions import SessionRepository


REGISTRATION_STEPS: tuple[str, ...] = (
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
    "complete",
)


@dataclass(frozen=True)
class WorkflowState:
    discord_user_id: str
    step: str
    session_data: Dict[str, Any]


class RegistrationWorkflow:
    """Session-driven registration workflow for a single Discord user."""

    def __init__(
        self,
        profiles: ProfileRepository,
        sessions: SessionRepository,
    ) -> None:
        self.profiles = profiles
        self.sessions = sessions

    def start(self, discord_user_id: str) -> WorkflowState:
        """Create or reset a registration session and return its initial state."""
        self.sessions.create_or_replace_session(
            discord_user_id=discord_user_id,
            step="ingame_name",
            session_data={},
        )
        session: dict[str, Any] = self.sessions.get_session(discord_user_id)
        return self._state_from_session(session)

    def get_state(self, discord_user_id: str) -> Optional[WorkflowState]:
        """Return the current registration state, or None if no active session exists."""
        session: Optional[dict[str, Any]] = self.sessions.get_session(discord_user_id)
        if session is None:
            return None
        return self._state_from_session(session)

    def cancel(self, discord_user_id: str) -> None:
        """Delete the active registration session if present."""
        self.sessions.delete_session(discord_user_id)

    def save_step(
        self,
        discord_user_id: str,
        value: Any,
    ) -> WorkflowState:
        """
        Persist input for the current step and advance to the next one.

        Raises:
            ValueError: If no session exists or if the session is already complete.
        """
        session: Optional[dict[str, Any]] = self.sessions.get_session(discord_user_id)
        if session is None:
            raise ValueError("Registration session not found.")

        current_step: str = str(session["step"])
        if current_step == "complete":
            raise ValueError("Registration session is already complete.")

        session_data: dict[str, Any] = dict(session["session_data_json"])
        session_data[current_step] = value

        next_step: str = self._next_step_after(current_step, session_data)

        self.sessions.update_session(
            discord_user_id=discord_user_id,
            step=next_step,
            session_data=session_data,
        )

        updated: dict[str, Any] = self.sessions.get_session(discord_user_id)
        return self._state_from_session(updated)

    def finalize_registration(
        self,
        discord_user_id: str,
        discord_display_name: str,
    ) -> int:
        """
        Convert the completed session into a persisted profile.

        Returns:
            int: The created profile ID.

        Raises:
            ValueError: If session is missing or incomplete.
        """
        session: Optional[dict[str, Any]] = self.sessions.get_session(discord_user_id)
        if session is None:
            raise ValueError("Registration session not found.")

        step: str = str(session["step"])
        session_data: dict[str, Any] = dict(session["session_data_json"])

        if step != "complete":
            raise ValueError("Registration session is not complete.")

        self._validate_required_fields(session_data)

        profile_data: dict[str, Any] = {
            "discord_user_id": discord_user_id,
            "discord_display_name": discord_display_name,
            "ingame_name": session_data["ingame_name"],
            "country_code": session_data["country_code"],
            "primary_language_code": session_data["primary_language_code"],
            "timezone": session_data["timezone"],
            "availability_start_minutes": session_data["availability_start_minutes"],
            "availability_end_minutes": session_data["availability_end_minutes"],
            "squad_a_power": session_data["squad_a_power"],
            "squad_a_type": session_data["squad_a_type"],
            "squad_b_power": session_data.get("squad_b_power"),
            "squad_b_type": session_data.get("squad_b_type"),
            "squad_c_power": session_data.get("squad_c_power"),
            "squad_c_type": session_data.get("squad_c_type"),
            "squad_d_power": session_data.get("squad_d_power"),
            "squad_d_type": session_data.get("squad_d_type"),
            "account_type": "main",
        }

        profile_id: int = self.profiles.create_profile(profile_data)

        self.sessions.remove_unregistered_user(discord_user_id)
        self.sessions.delete_session(discord_user_id)

        return profile_id

    def _next_step_after(
        self,
        current_step: str,
        session_data: dict[str, Any],
    ) -> str:
        """Determine the next registration step."""
        if current_step == "squad_a_type":
            return "squad_b_power"

        if current_step == "squad_b_power":
            if session_data.get("squad_b_power") in (None, 0, ""):
                session_data["squad_b_power"] = None
                session_data["squad_b_type"] = None
                session_data["squad_c_power"] = None
                session_data["squad_c_type"] = None
                session_data["squad_d_power"] = None
                session_data["squad_d_type"] = None
                return "complete"
            return "squad_b_type"

        if current_step == "squad_b_type":
            return "squad_c_power"

        if current_step == "squad_c_power":
            if session_data.get("squad_c_power") in (None, 0, ""):
                session_data["squad_c_power"] = None
                session_data["squad_c_type"] = None
                session_data["squad_d_power"] = None
                session_data["squad_d_type"] = None
                return "complete"
            return "squad_c_type"

        if current_step == "squad_c_type":
            return "squad_d_power"

        if current_step == "squad_d_power":
            if session_data.get("squad_d_power") in (None, 0, ""):
                session_data["squad_d_power"] = None
                session_data["squad_d_type"] = None
                return "complete"
            return "squad_d_type"

        if current_step == "squad_d_type":
            return "complete"

        try:
            index: int = REGISTRATION_STEPS.index(current_step)
        except ValueError as exc:
            raise ValueError(f"Unknown workflow step: {current_step}") from exc

        return REGISTRATION_STEPS[index + 1]

    def _validate_required_fields(self, session_data: dict[str, Any]) -> None:
        """Validate required fields for final persistence."""
        required_fields: tuple[str, ...] = (
            "ingame_name",
            "country_code",
            "primary_language_code",
            "timezone",
            "availability_start_minutes",
            "availability_end_minutes",
            "squad_a_power",
            "squad_a_type",
        )

        missing: list[str] = [
            field_name
            for field_name in required_fields
            if session_data.get(field_name) in (None, "")
        ]
        if missing:
            raise ValueError(
                f"Registration session is incomplete. Missing fields: {', '.join(missing)}"
            )

    def _state_from_session(self, session: dict[str, Any]) -> WorkflowState:
        """Convert a raw session row into a typed workflow state."""
        return WorkflowState(
            discord_user_id=str(session["discord_user_id"]),
            step=str(session["step"]),
            session_data=dict(session["session_data_json"]),
        )