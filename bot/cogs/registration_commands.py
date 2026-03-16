from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import Settings
from bot.services import build_profile_data
from db.repositories import (
    ProfileRepository,
    RegistrationSessionRepository,
    UnregisteredTrackingRepository,
)


def _session_summary(step: str, data: dict[str, object]) -> str:
    keys = ", ".join(sorted(data.keys())) if data else "none yet"
    return f"Current step: {step}\nCollected fields: {keys}"


class RegistrationCommands(commands.Cog):
    register = app_commands.Group(name="register", description="Registration workflow")

    def __init__(self, bot: commands.Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        self.sessions = RegistrationSessionRepository()
        self.profiles = ProfileRepository()
        self.unregistered_tracking = UnregisteredTrackingRepository()

    @register.command(name="start", description="Start or reset your registration session")
    async def start(self, interaction: discord.Interaction) -> None:
        session = self.sessions.create_or_reset(
            interaction.user.id,
            ttl_hours=self.settings.session_ttl_hours,
        )
        await interaction.response.send_message(
            (
                "Registration session started.\n"
                "Next: `/register identity`, then `/register locale`, `/register availability`, "
                "`/register squad` for A-D as needed, and `/register finish`.\n"
                f"{_session_summary(session.step, session.session_data)}"
            ),
            ephemeral=True,
        )

    @register.command(name="status", description="View your in-progress registration session")
    async def status(self, interaction: discord.Interaction) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active registration session. Use `/register start`.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            _session_summary(session.step, session.session_data),
            ephemeral=True,
        )

    @register.command(name="cancel", description="Cancel your current registration session")
    async def cancel(self, interaction: discord.Interaction) -> None:
        self.sessions.delete(interaction.user.id)
        await interaction.response.send_message("Registration session deleted.", ephemeral=True)

    @register.command(name="identity", description="Submit identity details")
    @app_commands.choices(
        account_type=[
            app_commands.Choice(name="main", value="main"),
            app_commands.Choice(name="alt", value="alt"),
        ]
    )
    async def identity(
        self,
        interaction: discord.Interaction,
        ingame_name: str,
        account_type: app_commands.Choice[str],
    ) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active session. Use `/register start` first.",
                ephemeral=True,
            )
            return
        session.session_data.update(
            {
                "ingame_name": ingame_name,
                "account_type": account_type.value,
            }
        )
        self.sessions.save_step(
            interaction.user.id,
            "locale",
            session.session_data,
            self.settings.session_ttl_hours,
        )
        await interaction.response.send_message(
            "Identity saved. Next: `/register locale`.",
            ephemeral=True,
        )

    @register.command(name="locale", description="Submit country, language, and timezone")
    async def locale(
        self,
        interaction: discord.Interaction,
        country_code: str,
        language_code: str,
        timezone: str,
    ) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active session. Use `/register start` first.",
                ephemeral=True,
            )
            return
        session.session_data.update(
            {
                "country_code": country_code.upper(),
                "primary_language_code": language_code.lower(),
                "timezone": timezone,
            }
        )
        self.sessions.save_step(
            interaction.user.id,
            "availability",
            session.session_data,
            self.settings.session_ttl_hours,
        )
        await interaction.response.send_message(
            "Locale saved. Next: `/register availability`.",
            ephemeral=True,
        )

    @register.command(name="availability", description="Submit event availability window")
    async def availability(
        self,
        interaction: discord.Interaction,
        start_minutes: app_commands.Range[int, 0, 1439],
        end_minutes: app_commands.Range[int, 0, 1439],
    ) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active session. Use `/register start` first.",
                ephemeral=True,
            )
            return
        session.session_data.update(
            {
                "availability_start_minutes": start_minutes,
                "availability_end_minutes": end_minutes,
            }
        )
        self.sessions.save_step(
            interaction.user.id,
            "squads",
            session.session_data,
            self.settings.session_ttl_hours,
        )
        await interaction.response.send_message(
            "Availability saved. Next: `/register squad slot:a ...`.",
            ephemeral=True,
        )

    @register.command(name="squad", description="Submit squad power and type for one slot")
    @app_commands.choices(
        slot=[
            app_commands.Choice(name="A", value="a"),
            app_commands.Choice(name="B", value="b"),
            app_commands.Choice(name="C", value="c"),
            app_commands.Choice(name="D", value="d"),
        ],
        squad_type=[
            app_commands.Choice(name="tank", value="tank"),
            app_commands.Choice(name="air", value="air"),
            app_commands.Choice(name="missile", value="missile"),
            app_commands.Choice(name="mixed", value="mixed"),
        ],
    )
    async def squad(
        self,
        interaction: discord.Interaction,
        slot: app_commands.Choice[str],
        power: int | None = None,
        squad_type: app_commands.Choice[str] | None = None,
        clear_slot: bool = False,
    ) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active session. Use `/register start` first.",
                ephemeral=True,
            )
            return

        suffix = slot.value
        power_key = f"squad_{suffix}_power"
        type_key = f"squad_{suffix}_type"

        if clear_slot:
            if suffix == "a":
                await interaction.response.send_message(
                    "Squad A is required and cannot be cleared.",
                    ephemeral=True,
                )
                return
            session.session_data.pop(power_key, None)
            session.session_data.pop(type_key, None)
        else:
            if power is None or squad_type is None:
                await interaction.response.send_message(
                    "Power and squad type are required unless `clear_slot` is true.",
                    ephemeral=True,
                )
                return
            session.session_data[power_key] = power
            session.session_data[type_key] = squad_type.value

        self.sessions.save_step(
            interaction.user.id,
            "review",
            session.session_data,
            self.settings.session_ttl_hours,
        )
        await interaction.response.send_message(
            f"Squad {slot.name} saved. Use `/register finish` when all required data is present.",
            ephemeral=True,
        )

    @register.command(name="finish", description="Finalize registration and create your profile")
    async def finish(self, interaction: discord.Interaction) -> None:
        session = self.sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message(
                "No active session. Use `/register start` first.",
                ephemeral=True,
            )
            return

        try:
            profile = build_profile_data(
                discord_user_id=interaction.user.id,
                discord_display_name=interaction.user.display_name,
                payload=session.session_data,
            )
        except ValueError as exc:
            await interaction.response.send_message(
                f"Registration is incomplete or invalid: {exc}",
                ephemeral=True,
            )
            return

        self.profiles.upsert(profile)
        self.sessions.delete(interaction.user.id)
        self.unregistered_tracking.remove(interaction.user.id)

        if isinstance(interaction.user, discord.Member):
            if self.settings.unregistered_role_id is not None:
                role = interaction.guild.get_role(self.settings.unregistered_role_id) if interaction.guild else None
                if role is not None:
                    await interaction.user.remove_roles(role, reason="Registration completed")
            if self.settings.member_role_id is not None:
                role = interaction.guild.get_role(self.settings.member_role_id) if interaction.guild else None
                if role is not None:
                    await interaction.user.add_roles(role, reason="Registration completed")

        await interaction.response.send_message("Registration completed.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    settings: Settings = bot.settings  # type: ignore[attr-defined]
    await bot.add_cog(RegistrationCommands(bot, settings))
