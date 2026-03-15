import discord
from discord.ext import commands

TOKEN = "YOUR_DISCORD_TOKEN"

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()


async def load_cogs():
    await bot.load_extension("bot.cogs.profile_commands")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


import asyncio
asyncio.run(main())
