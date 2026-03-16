from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from bot.config import Settings
from db.connection import init_db
from db.schema import SCHEMA_SQL


class LastWarBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings

    async def setup_hook(self) -> None:
        init_db(SCHEMA_SQL)
        await self.load_extension("bot.cogs.member_events")
        await self.load_extension("bot.cogs.registration_commands")
        await self.load_extension("bot.cogs.profile_commands")
        await self.load_extension("bot.cogs.admin_commands")

        if self.settings.guild_id is not None:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    bot = LastWarBot(settings)
    asyncio.run(bot.start(settings.discord_token))
