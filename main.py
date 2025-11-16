import asyncio
import logging

import discord
from discord.ext import commands

from utils.database import db_exec, add_timestamp
from utils.functions import fetch_messages
from utils.globals import setup
from utils.syncmanager import sync_manager

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

api_token = setup()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    guild_id = message.guild.id
    author_id = message.author.id
    author_name = message.author.name
    timestamp = message.created_at

    logger.debug("Received message")

    await db_exec(
        add_timestamp,
        guild_id,
        author_id,
        author_name,
        timestamp
    )

@bot.event
async def on_guild_join(guild):
    logger.info("Joined new guild - starting sync")
    async with sync_manager.lock:
        sync_manager.add_guilds((guild,))
        await fetch_messages(guild)
        sync_manager.finish_syncing()

@bot.event
async def on_guild_remove(guild):
    logger.info(f"Left guild {guild.name}")
    async with sync_manager.lock:
        sync_manager.remove_guild(guild.id)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    await bot.tree.sync()
    logger.info("Starting message sync")
    async with sync_manager.lock:
        sync_manager.add_guilds(bot.guilds)
        for guild in bot.guilds:
            await fetch_messages(guild)
            await asyncio.sleep(0.25)
        sync_manager.finish_syncing()
    logger.info("Ready for your commands!")


async def load_cogs():
    await bot.load_extension("cogs.activity")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.whitelist")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(api_token)


if __name__ == "__main__":
    asyncio.run(main())