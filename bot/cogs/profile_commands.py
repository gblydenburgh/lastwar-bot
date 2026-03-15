from __future__ import annotations

from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands

from db.connection import DatabaseManager
from db.profiles import ProfileRepository
from db.sessions import SessionRepository
from workflows.registration import RegistrationWorkflow, WorkflowState


ALLOWED_SQUAD_TYPES: tuple[str, ...] = ("tank", "air", "missile", "mixed")


class InGameNameModal(discord.ui.Modal, title="Last War Registration"):
    ingame_name: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="In-game name",
        placeholder="Enter your exact in-game name",
        min_length=1,
        max_length=64,
        required=True,
    )

    def __init__(self, cog: "ProfileCommands") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        user_id: str = str(interaction.user.id)

        try:
            state: WorkflowState = self.cog.workflow.save_step(
                discord_user_id=user_id,
                value=str(self.ingame_name.value).strip(),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await interaction.response.send_message(
            self.cog.render_next_prompt(state),
            ephemeral=True,
        )


class ProfileCommands(commands.Cog):
    """Discord command layer for registration and profile management."""

    def __init__(self, bot: commands.Bot, db: DatabaseManager) -> None:
        self.bot = bot
        self.db = db
        self.profiles = ProfileRepository(db)
        self.sessions = SessionRepository(db)
        self.workflow = RegistrationWorkflow(self.profiles, self.sessions)

    @app_commands.command(name="register", description="Start profile registration")
    async def register(self, interaction: discord.Interaction) -> None:
        user_id: str = str(interaction.user.id)

        existing: Optional[dict[str, Any]] = self.profiles.get_profile_by_discord_user(
            user_id
        )
        if existing is not None:
            await interaction.response.send_message(
                "You already have a registered profile.",
                ephemeral=True,
            )
            return

        self.workflow.start(user_id)
        await interaction.response.send_modal(InGameNameModal(self))

    @app_commands.command(
        name="registration_status",
        description="Show your current registration step",
    )
    async def registration_status(self, interaction: discord.Interaction) -> None:
        user_id: str = str(interaction.user.id)
        state: Optional[WorkflowState] = self.workflow.get_state(user_id)

        if state is None:
            await interaction.response.send_message(
                "No active registration session found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            self.render_next_prompt(state),
            ephemeral=True,
        )

    @app_commands.command(
        name="registration_cancel",
        description="Cancel your active registration session",
    )
    async def registration_cancel(self, interaction: discord.Interaction) -> None:
        user_id: str = str(interaction.user.id)
        self.workflow.cancel(user_id)

        await interaction.response.send_message(
            "Your registration session was cancelled.",
            ephemeral=True,
        )

    @app_commands.command(
        name="registration_input",
        description="Continue registration by submitting the value for the current step",
    )
    async def registration_input(
        self,
        interaction: discord.Interaction,
        value: str,
    ) -> None:
        user_id: str = str(interaction.user.id)
        state: Optional[WorkflowState] = self.workflow.get_state(user_id)

        if state is None:
            await interaction.response.send_message(
                "No active registration session found. Use /register first.",
                ephemeral=True,
            )
            return

        try:
            normalized_value: Any = self.normalize_input(state.step, value)
            updated_state: WorkflowState = self.workflow.save_step(
                discord_user_id=user_id,
                value=normalized_value,
            )
        except ValueError as exc:
            await interaction.response.send_message(
                f"Invalid input: {exc}",
                ephemeral=True,
            )
            return

        if updated_state.step == "complete":
            try:
                profile_id: int = self.workflow.finalize_registration(
                    discord_user_id=user_id,
                    discord_display_name=interaction.user.display_name,
                )
            except ValueError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return

            await interaction.response.send_message(
                f"Registration complete. Profile created with ID {profile_id}.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            self.render_next_prompt(updated_state),
            ephemeral=True,
        )

    @app_commands.command(name="profile_view", description="View your registered profile")
    async def profile_view(self, interaction: discord.Interaction) -> None:
        user_id: str = str(interaction.user.id)
        profile: Optional[dict[str, Any]] = self.profiles.get_profile_by_discord_user(
            user_id
        )

        if profile is None:
            await interaction.response.send_message(
                "You do not have a registered profile.",
                ephemeral=True,
            )
            return

        embed: discord.Embed = discord.Embed(
            title=f"{profile['ingame_name']} Profile",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Country", value=str(profile["country_code"]), inline=True)
        embed.add_field(
            name="Language",
            value=str(profile["primary_language_code"]),
            inline=True,
        )
        embed.add_field(name="Timezone", value=str(profile["timezone"]), inline=True)
        embed.add_field(
            name="Availability",
            value=(
                f"{profile['availability_start_minutes']} to "
                f"{profile['availability_end_minutes']} minutes"
            ),
            inline=False,
        )
        embed.add_field(
            name="Squad A",
            value=f"{profile['squad_a_power']} ({profile['squad_a_type']})",
            inline=False,
        )

        for squad_slot in ("b", "c", "d"):
            power_key: str = f"squad_{squad_slot}_power"
            type_key: str = f"squad_{squad_slot}_type"
            if profile.get(power_key) is not None:
                embed.add_field(
                    name=f"Squad {squad_slot.upper()}",
                    value=f"{profile[power_key]} ({profile[type_key]})",
                    inline=False,
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="profile_update_squad",
        description="Update one of your squad power/type values",
    )
    @app_commands.describe(
        squad="Which squad to update: A, B, C, or D",
        power="Squad power",
        squad_type="tank, air, missile, or mixed",
    )
    async def profile_update_squad(
        self,
        interaction: discord.Interaction,
        squad: str,
        power: int,
        squad_type: str,
    ) -> None:
        user_id: str = str(interaction.user.id)
        profile: Optional[dict[str, Any]] = self.profiles.get_profile_by_discord_user(
            user_id
        )

        if profile is None:
            await interaction.response.send_message(
                "You do not have a registered profile.",
                ephemeral=True,
            )
            return

        squad_normalized: str = squad.strip().upper()
        squad_type_normalized: str = squad_type.strip().lower()

        if squad_normalized not in {"A", "B", "C", "D"}:
            await interaction.response.send_message(
                "Squad must be A, B, C, or D.",
                ephemeral=True,
            )
            return

        if power < 0:
            await interaction.response.send_message(
                "Power must be zero or greater.",
                ephemeral=True,
            )
            return

        if squad_type_normalized not in ALLOWED_SQUAD_TYPES:
            await interaction.response.send_message(
                "Squad type must be tank, air, missile, or mixed.",
                ephemeral=True,
            )
            return

        self.profiles.update_squad(
            profile_id=int(profile["id"]),
            squad_slot=squad_normalized,
            new_power=power,
            new_type=squad_type_normalized,
        )

        await interaction.response.send_message(
            f"Squad {squad_normalized} updated.",
            ephemeral=True,
        )

    @app_commands.command(
        name="admin_delete_profile",
        description="Hard delete a profile by in-game name",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_delete_profile(
        self,
        interaction: discord.Interaction,
        ingame_name: str,
    ) -> None:
        profile: Optional[dict[str, Any]] = self.profiles.get_profile_by_ingame_name(
            ingame_name.strip()
        )

        if profile is None:
            await interaction.response.send_message(
                "Profile not found.",
                ephemeral=True,
            )
            return

        self.profiles.delete_profile(int(profile["id"]))

        await interaction.response.send_message(
            f"Profile '{ingame_name}' was permanently deleted.",
            ephemeral=True,
        )

    def normalize_input(self, step: str, value: str) -> Any:
        """Normalize slash command input based on the active registration step."""
        cleaned: str = value.strip()

        if step in {
            "availability_start_minutes",
            "availability_end_minutes",
            "squad_a_power",
            "squad_b_power",
            "squad_c_power",
            "squad_d_power",
        }:
            try:
                parsed: int = int(cleaned)
            except ValueError as exc:
                raise ValueError("Expected a whole number.") from exc

            if parsed < 0:
                raise ValueError("Value must be zero or greater.")

            if step.startswith("availability_") and parsed > 1439:
                raise ValueError("Availability minutes must be between 0 and 1439.")

            return parsed

        if step in {"squad_a_type", "squad_b_type", "squad_c_type", "squad_d_type"}:
            normalized: str = cleaned.lower()
            if normalized not in ALLOWED_SQUAD_TYPES:
                raise ValueError("Expected tank, air, missile, or mixed.")
            return normalized

        if step in {"country_code", "primary_language_code"}:
            return cleaned.upper()

        return cleaned

    def render_next_prompt(self, state: WorkflowState) -> str:
        """Return the user-facing prompt for the next workflow step."""
        prompts: dict[str, str] = {
            "ingame_name": "Enter your in-game name.",
            "country_code": "Enter your country code, for example: US",
            "primary_language_code": "Enter your primary language code from the game UI list.",
            "timezone": "Enter your timezone, for example: America/New_York",
            "availability_start_minutes": "Enter your event availability start in minutes after midnight.",
            "availability_end_minutes": "Enter your event availability end in minutes after midnight.",
            "squad_a_power": "Enter Squad A power.",
            "squad_a_type": "Enter Squad A type: tank, air, missile, or mixed.",
            "squad_b_power": "Enter Squad B power, or 0 if not used.",
            "squad_b_type": "Enter Squad B type: tank, air, missile, or mixed.",
            "squad_c_power": "Enter Squad C power, or 0 if not used.",
            "squad_c_type": "Enter Squad C type: tank, air, missile, or mixed.",
            "squad_d_power": "Enter Squad D power, or 0 if not used.",
            "squad_d_type": "Enter Squad D type: tank, air, missile, or mixed.",
            "complete": "Registration is complete.",
        }

        current_prompt: str = prompts.get(state.step, f"Current step: {state.step}")
        return (
            f"Current registration step: `{state.step}`\n"
            f"{current_prompt}\n\n"
            "Use `/registration_input value:<your value>` to continue."
        )


async def setup(bot: commands.Bot) -> None:
    db: DatabaseManager = DatabaseManager("data/lastwar.db")
    db.initialize()
    await bot.add_cog(ProfileCommands(bot, db))