from __future__ import annotations

import discord
from discord.ext import commands

from bot.config import Settings
from db.repositories import UnregisteredTrackingRepository


class MemberEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        self.unregistered_tracking = UnregisteredTrackingRepository()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self.unregistered_tracking.track_join(member.id)

        if self.settings.unregistered_role_id is not None:
            role = member.guild.get_role(self.settings.unregistered_role_id)
            if role is not None:
                await member.add_roles(role, reason="New member awaiting registration")

        if self.settings.registration_channel_id is None:
            return

        channel = member.guild.get_channel(self.settings.registration_channel_id)
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            await channel.send(
                f"{member.mention} welcome. Use `/register start` to begin alliance registration."
            )


async def setup(bot: commands.Bot) -> None:
    settings: Settings = bot.settings  # type: ignore[attr-defined]
    await bot.add_cog(MemberEvents(bot, settings))
