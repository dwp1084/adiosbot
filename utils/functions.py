# Load existing messages from disk
import json
import logging
import os
from datetime import datetime

import discord

from utils.globals import MESSAGE_LOG_DIR, WHITELIST_DIR

logger = logging.getLogger(__name__)
log_dir = MESSAGE_LOG_DIR
wl_dir = WHITELIST_DIR

def load_existing_messages(channel_id):
    global log_dir
    if log_dir is None:
        from utils.globals import MESSAGE_LOG_DIR
        log_dir = MESSAGE_LOG_DIR

    file_path = f"{log_dir}/{channel_id}.json"
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Fetch and save messages from a specific channel, only fetching new ones
async def fetch_new_messages(channel):
    existing_messages = load_existing_messages(channel.id)

    # Find the timestamp of the last saved message
    last_saved_time = None
    if existing_messages:
        last_saved_time = max(
            datetime.fromisoformat(msg['timestamp']) for msg in existing_messages
        )

    # Fetch only messages newer than the last saved one
    new_messages = []
    async for message in channel.history(limit=10000, after=last_saved_time):
        new_messages.append({
            'timestamp': message.created_at.isoformat(),
            'author': message.author.id
        })

    newest_messages_by_author = {}

    # Iterate through both existing and new messages to keep the latest per author
    for msg in existing_messages + new_messages:
        author_id = msg['author']
        msg_timestamp = datetime.fromisoformat(msg['timestamp'])

        # Keep only the latest message for each author
        if ((author_id not in newest_messages_by_author)
                or (msg_timestamp > datetime.fromisoformat(
                    newest_messages_by_author[author_id]['timestamp']
                ))):
            newest_messages_by_author[author_id] = msg

    # Convert dictionary values back to a list of messages
    all_messages = list(newest_messages_by_author.values())

    # Sort the messages by timestamp in reverse (newest first)
    sorted_new_messages = sorted(
        all_messages,
        key=lambda x: datetime.fromisoformat(x["timestamp"]),
        reverse=True
    )

    global log_dir
    if log_dir is None:
        from utils.globals import MESSAGE_LOG_DIR
        log_dir = MESSAGE_LOG_DIR

    # Save the updated list back to disk
    with open(
            f"{log_dir}/{channel.id}.json",
            'w',
            encoding='utf-8'
    ) as f:
        json.dump(sorted_new_messages, f, ensure_ascii=False, indent=4)

    if new_messages:
        logger.info(f"Fetched {len(new_messages)} new messages from {channel.name}")


# Fetch and save messages from all channels
async def fetch_messages(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_message_history:
            await fetch_new_messages(channel)

# Get the last message timestamp for each user
def get_last_message_time(guild):
    global log_dir
    if log_dir is None:
        from utils.globals import MESSAGE_LOG_DIR
        log_dir = MESSAGE_LOG_DIR

    user_last_message = {}
    for channel_file in os.listdir(log_dir):
        with open(f"{log_dir}/{channel_file}", 'r', encoding='utf-8') as f:
            messages = json.load(f)
            for msg in messages:
                user = msg['author']
                timestamp = datetime.fromisoformat(msg['timestamp'])
                if user not in user_last_message or user_last_message[user] < timestamp:
                    user_last_message[user] = timestamp
    return user_last_message

def remove_member_messages(member, guild):
    global log_dir
    if log_dir is None:
        from utils.globals import MESSAGE_LOG_DIR
        log_dir = MESSAGE_LOG_DIR

    for channel_file in os.listdir(log_dir):
        messages = []
        with open(f"{log_dir}/{channel_file}", 'r', encoding='utf-8') as f:
            messages += [ msg for msg in json.load(f) if msg['author'] != member.id]
        with open(f"{log_dir}/{channel_file}", 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
    return

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