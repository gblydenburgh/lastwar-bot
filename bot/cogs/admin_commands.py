from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import Settings
from db.repositories import ProfileRepository, UnregisteredTrackingRepository


class AdminCommands(commands.Cog):
    admin = app_commands.Group(name="admin", description="Alliance admin commands")
    report = app_commands.Group(name="report", description="Admin reporting commands", parent=admin)

    def __init__(self, bot: commands.Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        self.profiles = ProfileRepository()
        self.unregistered = UnregisteredTrackingRepository()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.settings.admin_role_id is None:
            return True
        if not isinstance(interaction.user, discord.Member):
            return False
        role_ids = {role.id for role in interaction.user.roles}
        if self.settings.admin_role_id in role_ids:
            return True
        await interaction.response.send_message("Admin role required.", ephemeral=True)
        return False

    @admin.command(name="delete_profile", description="Hard-delete a profile by Discord user")
    async def delete_profile(self, interaction: discord.Interaction, member: discord.Member) -> None:
        deleted = self.profiles.delete(member.id)
        if deleted:
            await interaction.response.send_message(
                f"Deleted profile for {member.mention}.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message("Profile not found.", ephemeral=True)

    @report.command(name="roster", description="Show the current alliance roster")
    async def roster(self, interaction: discord.Interaction) -> None:
        rows = self.profiles.list_roster()
        if not rows:
            await interaction.response.send_message("No registered profiles.", ephemeral=True)
            return
        lines = [
            f"{row['ingame_name']} | {row['country_code']} | {row['primary_language_code']} | {row['timezone']}"
            for row in rows
        ]
        await interaction.response.send_message("\n".join(lines[:40]), ephemeral=True)

    @report.command(name="squad_power", description="Show total squad power rankings")
    async def squad_power(self, interaction: discord.Interaction) -> None:
        rows = self.profiles.squad_power_rankings()
        if not rows:
            await interaction.response.send_message("No registered profiles.", ephemeral=True)
            return
        lines = [f"{index}. {row['ingame_name']} - {row['total_power']}" for index, row in enumerate(rows, start=1)]
        await interaction.response.send_message("\n".join(lines[:40]), ephemeral=True)

    @report.command(name="timezone_distribution", description="Show timezone counts")
    async def timezone_distribution(self, interaction: discord.Interaction) -> None:
        rows = self.profiles.timezone_distribution()
        if not rows:
            await interaction.response.send_message("No registered profiles.", ephemeral=True)
            return
        lines = [f"{row['timezone']}: {row['member_count']}" for row in rows]
        await interaction.response.send_message("\n".join(lines[:40]), ephemeral=True)

    @report.command(name="unregistered", description="Show users still awaiting registration")
    async def unregistered_report(self, interaction: discord.Interaction) -> None:
        rows = self.unregistered.list_all()
        if not rows:
            await interaction.response.send_message("No unregistered members tracked.", ephemeral=True)
            return
        now = datetime.now(UTC)
        lines = []
        for row in rows[:40]:
            joined = datetime.fromisoformat(row["joined_at"])
            age_hours = int((now - joined).total_seconds() // 3600)
            lines.append(
                f"<@{row['discord_user_id']}> | joined {age_hours}h ago | reminders {row['reminder_count']}"
            )
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    settings: Settings = bot.settings  # type: ignore[attr-defined]
    await bot.add_cog(AdminCommands(bot, settings))
