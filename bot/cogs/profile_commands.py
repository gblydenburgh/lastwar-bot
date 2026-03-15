from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from db.connection import DatabaseManager
from db.profiles import ProfileRepository
from db.sessions import SessionRepository
from workflows.registration import RegistrationWorkflow


class ProfileCommands(commands.Cog):
    """
    Discord command layer for profile management.
    """

    def __init__(self, bot: commands.Bot, db: DatabaseManager) -> None:
        self.bot = bot
        self.db = db

        self.profiles = ProfileRepository(db)
        self.sessions = SessionRepository(db)
        self.workflow = RegistrationWorkflow(self.profiles, self.sessions)

    # ---------------------------------------------------------
    # REGISTER
    # ---------------------------------------------------------

    @app_commands.command(name="register", description="Start profile registration")
    async def register(self, interaction: discord.Interaction) -> None:

        user_id = str(interaction.user.id)

        existing = self.profiles.get_profiles_by_discord_user(user_id)

        if existing:
            await interaction.response.send_message(
                "You already have a registered profile.",
                ephemeral=True,
            )
            return

        self.workflow.start(user_id)

        await interaction.response.send_message(
            "Registration started.\n\nEnter your **in-game name**.",
            ephemeral=True,
        )

    # ---------------------------------------------------------
    # VIEW PROFILE
    # ---------------------------------------------------------

    @app_commands.command(name="view", description="View a player's profile")
    async def view(
        self,
        interaction: discord.Interaction,
        ingame_name: str,
    ) -> None:

        profile = self.profiles.get_profile_by_ingame_name(ingame_name)

        if not profile:
            await interaction.response.send_message(
                "Profile not found.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{profile['ingame_name']} Profile",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="Country",
            value=profile["country_code"],
        )

        embed.add_field(
            name="Timezone",
            value=profile["timezone"],
        )

        embed.add_field(
            name="Squad A",
            value=f"{profile['squad_a_power']} ({profile['squad_a_type']})",
            inline=False,
        )

        if profile["squad_b_power"]:
            embed.add_field(
                name="Squad B",
                value=f"{profile['squad_b_power']} ({profile['squad_b_type']})",
                inline=False,
            )

        if profile["squad_c_power"]:
            embed.add_field(
                name="Squad C",
                value=f"{profile['squad_c_power']} ({profile['squad_c_type']})",
                inline=False,
            )

        if profile["squad_d_power"]:
            embed.add_field(
                name="Squad D",
                value=f"{profile['squad_d_power']} ({profile['squad_d_type']})",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # ---------------------------------------------------------
    # UPDATE SQUAD
    # ---------------------------------------------------------

    @app_commands.command(name="update_squad", description="Update squad power")
    async def update_squad(
        self,
        interaction: discord.Interaction,
        squad: str,
        power: int,
        squad_type: str,
    ) -> None:

        user_id = str(interaction.user.id)

        profiles = self.profiles.get_profiles_by_discord_user(user_id)

        if not profiles:
            await interaction.response.send_message(
                "You do not have a registered profile.",
                ephemeral=True,
            )
            return

        profile = profiles[0]  # v1 assumption

        self.profiles.update_squad(
            profile_id=profile["profile_id"],
            squad_slot=squad,
            new_power=power,
            new_type=squad_type,
        )

        await interaction.response.send_message(
            f"Squad {squad} updated.",
            ephemeral=True,
        )

    # ---------------------------------------------------------
    # ADMIN DELETE
    # ---------------------------------------------------------

    @app_commands.command(name="delete_profile", description="Delete a profile")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_profile(
        self,
        interaction: discord.Interaction,
        ingame_name: str,
        reason: str,
    ) -> None:

        profile = self.profiles.get_profile_by_ingame_name(ingame_name)

        if not profile:
            await interaction.response.send_message(
                "Profile not found.",
                ephemeral=True,
            )
            return

        self.profiles.soft_delete(profile["profile_id"])

        await interaction.response.send_message(
            f"Profile **{ingame_name}** deleted.\nReason: {reason}",
            ephemeral=True,
        )

    # ---------------------------------------------------------
    # ADMIN RESTORE
    # ---------------------------------------------------------

    @app_commands.command(name="restore_profile", description="Restore a profile")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore_profile(
        self,
        interaction: discord.Interaction,
        ingame_name: str,
    ) -> None:

        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT profile_id
                FROM profiles
                WHERE ingame_name = ?
                AND deleted_at IS NOT NULL
                """,
                (ingame_name,),
            ).fetchone()

        if not row:
            await interaction.response.send_message(
                "No deleted profile found.",
                ephemeral=True,
            )
            return

        self.profiles.restore(row["profile_id"])

        await interaction.response.send_message(
            f"Profile **{ingame_name}** restored.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    db = DatabaseManager("data/lastwar.db")
    await bot.add_cog(ProfileCommands(bot, db))
