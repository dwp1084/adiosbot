# Load existing messages from disk
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from time import perf_counter

import discord

from utils.database import db_exec, add_timestamp, get_last_active_times, remove_user, \
    get_limit, add_sync_progress, finish_sync
from utils.globals import WHITELIST_DIR
from utils.syncmanager import sync_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

wl_dir = WHITELIST_DIR

# Get the last message timestamp for each user
async def get_last_message_time(guild):
    last_active = await db_exec(
        get_last_active_times,
        guild.id
    )

    user_last_messages = {}

    for row in last_active:
        user_id = row["user_id"]
        if guild.get_member(int(user_id)) is not None:
            user_last_messages[int(user_id)] = datetime.fromisoformat(
                row["timestamp"]
            )
        else:
            logger.debug(f"User {user_id} no longer guild member, deleting reference")
            await db_exec(
                remove_user,
                guild.id,
                user_id
            )

    return user_last_messages


# Fetch and save messages from a specific channel, only fetching new ones
async def fetch_new_messages(channel, earliest):
    logger.debug(f"Fetching messages from {channel.name}")
    current_utc_time = datetime.now(timezone.utc)
    limit = current_utc_time - timedelta(days=60)

    # Go back a maximum of 60 days in history per channel
    if earliest is not None and earliest > limit:
        limit = earliest

    async for msg in channel.history(limit=None, oldest_first=True, after=limit):
        if msg.author.bot:
            continue

        await db_exec(
            add_timestamp,
            msg.guild.id,
            msg.author.id,
            msg.author.name,
            msg.created_at
        )


# Fetch and save messages from all channels
async def fetch_messages(guild):
    timestamp_str = await db_exec(
        get_limit,
        guild.id
    )
    timestamp = datetime.fromisoformat(timestamp_str) \
        if timestamp_str is not None else None

    limit = datetime.now(timezone.utc) - timedelta(days=60)
    if timestamp is not None and timestamp > limit:
        limit = timestamp

    logger.debug(f"Beginning timestamp bound in {guild.name}: {limit}")

    await db_exec(add_sync_progress, guild.id, limit)

    start = perf_counter()
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_message_history:
            await fetch_new_messages(channel, limit)

    await db_exec(finish_sync, guild.id)

    end = perf_counter()

    logger.info(f"Sync for {guild.name} complete! Time taken {int((end-start)//60):02d}:{(end-start)%60:05.2f}")
    sync_manager.set_ready(guild.id)


def get_whitelist(guild: discord.Guild):
    global wl_dir
    if wl_dir is None:
        from utils.globals import WHITELIST_DIR
        wl_dir = WHITELIST_DIR

    guild_wl_path = os.path.join(wl_dir, f"{guild.id}.json")

    if os.path.exists(guild_wl_path):
        with open(guild_wl_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []

def set_whitelist(guild: discord.Guild, whitelist):
    global wl_dir
    if wl_dir is None:
        from utils.globals import WHITELIST_DIR
        wl_dir = WHITELIST_DIR

    guild_wl_path = os.path.join(wl_dir, f"{guild.id}.json")

    with open(guild_wl_path, 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=4)