import asyncio
import logging
from datetime import timedelta

import discord
from discord.ext import commands

from cogs.activity import Activity
from utils.functions import fetch_messages
from utils.globals import setup

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(
        level=logging.DEBUG,
        filename="bot.log",
        filemode="a",
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

api_token = setup()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)
    for guild in bot.guilds:
        await fetch_messages(guild)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    await bot.tree.sync()
    for guild in bot.guilds:
        await fetch_messages(guild)
    logger.info("Ready for your commands!")


async def load_cogs():
    await bot.load_extension("cogs.activity")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.whitelist")


async def main():
    # api_token = setup()
    async with bot:
        await load_cogs()
        await bot.start(api_token)


if __name__ == "__main__":
    asyncio.run(main())