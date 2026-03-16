from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.services import build_profile_data, merge_profile_update
from db.repositories import ProfileRepository


def _format_profile(row: dict) -> str:
    return "\n".join(
        [
            f"In-game name: {row['ingame_name']}",
            f"Account type: {row['account_type']}",
            f"Country: {row['country_code']}",
            f"Language: {row['primary_language_code']}",
            f"Timezone: {row['timezone']}",
            f"Availability: {row['availability_start_minutes']} - {row['availability_end_minutes']}",
            f"Squad A: {row['squad_a_power']} / {row['squad_a_type']}",
            f"Squad B: {row['squad_b_power'] or '-'} / {row['squad_b_type'] or '-'}",
            f"Squad C: {row['squad_c_power'] or '-'} / {row['squad_c_type'] or '-'}",
            f"Squad D: {row['squad_d_power'] or '-'} / {row['squad_d_type'] or '-'}",
        ]
    )


class ProfileCommands(commands.Cog):
    profile = app_commands.Group(name="profile", description="Profile commands")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.profiles = ProfileRepository()

    @profile.command(name="view", description="View your stored profile")
    async def view(self, interaction: discord.Interaction) -> None:
        row = self.profiles.get_by_user_id(interaction.user.id)
        if row is None:
            await interaction.response.send_message(
                "No profile found. Use `/register start` to create one.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(_format_profile(row), ephemeral=True)

    @profile.command(name="update", description="Update your current profile")
    @app_commands.choices(
        account_type=[
            app_commands.Choice(name="main", value="main"),
            app_commands.Choice(name="alt", value="alt"),
        ],
        squad_a_type=[
            app_commands.Choice(name="tank", value="tank"),
            app_commands.Choice(name="air", value="air"),
            app_commands.Choice(name="missile", value="missile"),
            app_commands.Choice(name="mixed", value="mixed"),
        ],
        squad_b_type=[
            app_commands.Choice(name="tank", value="tank"),
            app_commands.Choice(name="air", value="air"),
            app_commands.Choice(name="missile", value="missile"),
            app_commands.Choice(name="mixed", value="mixed"),
        ],
        squad_c_type=[
            app_commands.Choice(name="tank", value="tank"),
            app_commands.Choice(name="air", value="air"),
            app_commands.Choice(name="missile", value="missile"),
            app_commands.Choice(name="mixed", value="mixed"),
        ],
        squad_d_type=[
            app_commands.Choice(name="tank", value="tank"),
            app_commands.Choice(name="air", value="air"),
            app_commands.Choice(name="missile", value="missile"),
            app_commands.Choice(name="mixed", value="mixed"),
        ],
    )
    async def update(
        self,
        interaction: discord.Interaction,
        ingame_name: str | None = None,
        country_code: str | None = None,
        language_code: str | None = None,
        timezone: str | None = None,
        availability_start_minutes: app_commands.Range[int, 0, 1439] | None = None,
        availability_end_minutes: app_commands.Range[int, 0, 1439] | None = None,
        account_type: app_commands.Choice[str] | None = None,
        squad_a_power: int | None = None,
        squad_a_type: app_commands.Choice[str] | None = None,
        squad_b_power: int | None = None,
        squad_b_type: app_commands.Choice[str] | None = None,
        squad_c_power: int | None = None,
        squad_c_type: app_commands.Choice[str] | None = None,
        squad_d_power: int | None = None,
        squad_d_type: app_commands.Choice[str] | None = None,
    ) -> None:
        row = self.profiles.get_by_user_id(interaction.user.id)
        if row is None:
            await interaction.response.send_message(
                "No profile found. Use `/register start` to create one.",
                ephemeral=True,
            )
            return

        updates = {
            "discord_display_name": interaction.user.display_name,
            "ingame_name": ingame_name,
            "country_code": country_code,
            "primary_language_code": language_code,
            "timezone": timezone,
            "availability_start_minutes": availability_start_minutes,
            "availability_end_minutes": availability_end_minutes,
            "account_type": account_type.value if account_type else None,
            "squad_a_power": squad_a_power,
            "squad_a_type": squad_a_type.value if squad_a_type else None,
            "squad_b_power": squad_b_power,
            "squad_b_type": squad_b_type.value if squad_b_type else None,
            "squad_c_power": squad_c_power,
            "squad_c_type": squad_c_type.value if squad_c_type else None,
            "squad_d_power": squad_d_power,
            "squad_d_type": squad_d_type.value if squad_d_type else None,
        }
        updates = {key: value for key, value in updates.items() if value is not None}

        try:
            merged = merge_profile_update(row, updates)
            profile = build_profile_data(
                discord_user_id=interaction.user.id,
                discord_display_name=interaction.user.display_name,
                payload=merged,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self.profiles.upsert(profile)
        await interaction.response.send_message("Profile updated.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCommands(bot))
