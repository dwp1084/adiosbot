import discord
from discord.ext import commands, tasks
import os
import logging
import json
import random
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

utc=pytz.UTC

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    filemode="a",
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

load_dotenv()

# Folder to store message logs

api_token = os.getenv('DISCORD_BOT_TOKEN')

if api_token is None:
    logger.error("Error: DISCORD_BOT_TOKEN is not set")
    exit(1)

working_dir = os.getenv('WORKING_DIR')

if working_dir is None or not os.path.exists(working_dir):
    logger.warning("WORKING_DIR not set or invalid, defaulting to script directory.")
    working_dir = os.getcwd()

if not os.path.exists(working_dir):
    os.makedirs(working_dir)

MESSAGE_LOG_DIR = working_dir + "/message_logs"
if not os.path.exists(MESSAGE_LOG_DIR):
    os.makedirs(MESSAGE_LOG_DIR)
WHITELIST_PATH = working_dir + "/whitelist.json"


# Load existing messages from disk
def load_existing_messages(channel_id):
    file_path = f"{MESSAGE_LOG_DIR}/{channel_id}.json"
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

    # Save the updated list back to disk
    with open(
            f"{MESSAGE_LOG_DIR}/{channel.id}.json",
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
    user_last_message = {}
    for channel_file in os.listdir(MESSAGE_LOG_DIR):
        with open(f"{MESSAGE_LOG_DIR}/{channel_file}", 'r', encoding='utf-8') as f:
            messages = json.load(f)
            for msg in messages:
                user = msg['author']
                timestamp = datetime.fromisoformat(msg['timestamp'])
                if user not in user_last_message or user_last_message[user] < timestamp:
                    user_last_message[user] = timestamp
    return user_last_message

def remove_member_messages(member, guild):
    for channel_file in os.listdir(MESSAGE_LOG_DIR):
        messages = []
        with open(f"{MESSAGE_LOG_DIR}/{channel_file}", 'r', encoding='utf-8') as f:
            messages += [ msg for msg in json.load(f) if msg['author'] != member.id]
        with open(f"{MESSAGE_LOG_DIR}/{channel_file}", 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
    return

def get_whitelist():
    if os.path.exists(WHITELIST_PATH):
        with open(WHITELIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []


@bot.hybrid_group(fallback="show")
@commands.has_permissions(administrator=True)
async def whitelist(ctx, name):
    whitelist = get_whitelist()
    if len(whitelist) > 0:
        whitelist = "\n".join(whitelist)
        await ctx.send(f"**Whitelisted members (will not be kicked out even when inactive):** \n" + whitelist)
    else:
        await ctx.send(f"**No members currently on the whitelist** \n" + whitelist)


@whitelist.command()
@commands.has_permissions(administrator=True)
async def add(ctx, name):
    guild = ctx.guild
    existing_members = get_whitelist()
    if name not in [member.name for member in guild.members]:
        await ctx.send(f"**User {name} does not exist or is not a member of this server**")
        return
    if name in existing_members:
        await ctx.send(f"**User {name} is already on the whitelist**")
        return
    new_members = existing_members + [name]
    with open(WHITELIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_members, f, ensure_ascii=False, indent=4)
    await ctx.send(f"**User {name} was added to the whitelist**\nThe whitelist currently contains the following users:\n" + "\n".join(new_members))


@whitelist.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, name):
    guild = ctx.guild
    existing_members = get_whitelist()
    if name not in [member.name for member in guild.members]:
        await ctx.send(f"**User {name} does not exist or is not a member of this server**")
        return
    if name not in existing_members:
        await ctx.send(f"**User {name} is not currently on the whitelist**")
        return
    existing_members.remove(name)
    with open(WHITELIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing_members, f, ensure_ascii=False, indent=4)
    await ctx.send(f"**User {name} was removed from the whitelist**\nThe whitelist currently contains the following users:\n" + "\n".join(existing_members))


@bot.command(name='ban')
async def ban_user(ctx, username: str):
    member = ctx.message.author
    user = ctx.guild.get_member_named(username)
    if member.guild_permissions.administrator:
        if username == member.name:
            await ctx.send("**Can't timeout yourself!**")
        else:
            await user.timeout(timedelta(minutes=1), reason="For reasons")
            await ctx.send(f"**User {username} was timed out for 1 minute**")
    else:
        await member.timeout(timedelta(minutes=1), reason="Why did you think that would work? You fool. You buffoon.")

# Check for inactive members
@bot.command(name='inactive')
async def check_inactive(ctx, n: int):
    await ctx.send(f"Checking for members who haven't sent a message in the last {n} days...")
    guild = ctx.guild

    user_last_message = get_last_message_time(guild)
    inactive_members = []
    inactive_whitelisted_members = []
    cutoff_date = datetime.now() - timedelta(days=n)

    whitelist = get_whitelist()

    for member in guild.members:
        if not member.bot:
            last_message_time = user_last_message.get(member.id)
            if last_message_time is None or last_message_time < utc.localize(cutoff_date):
                if member.name not in whitelist:
                    inactive_members.append(member.name)
                else:
                    inactive_whitelisted_members.append(member.name)

    inactive_members.sort()
    inactive_whitelisted_members.sort()
    if inactive_members:
        await ctx.send(f"**{str(len(inactive_members))} inactive members in the last {n} days:**\n" + "\n".join(inactive_members))
    else:
        await ctx.send(f"No inactive members found in the last {n} days.")
    if inactive_whitelisted_members:
        await ctx.send(f"**{str(len(inactive_whitelisted_members))} whitelisted inactive members:**\n" + "\n".join(inactive_whitelisted_members))

# Check for inactive members
@bot.command(name='kick_inactive')
@commands.has_permissions(administrator=True)
async def kick_inactive(ctx, n: int):
    await ctx.send(f"Kicking members who haven't sent a message in the last {n} days...")
    guild = ctx.guild

    user_last_message = get_last_message_time(guild)
    inactive_members = []
    inactive_whitelisted_members = []
    cutoff_date = datetime.now() - timedelta(days=n)

    whitelist = get_whitelist()

    for member in guild.members:
        if not member.bot:
            last_message_time = user_last_message.get(member.id)
            if last_message_time is None or last_message_time < utc.localize(cutoff_date):
                if member.name not in whitelist:
                    inactive_members.append(member.name)
                    remove_member_messages(member, guild)
                    try:
                        await member.kick(reason=f"Inactive in {guild.name} for {n} days")
                        await ctx.send(f"**Kicked {member.name} for inactivity**")
                    except:
                        logger.error(f'Error kicking {member.name}')
                else:
                    inactive_whitelisted_members.append(member.name)

    inactive_members.sort()
    inactive_whitelisted_members.sort()
    if inactive_members:
        await ctx.send(f"**Kicked {str(len(inactive_members))} members which were inactive in the last {n} days**\n" + "\n".join(inactive_members))
    else:
        await ctx.send(f"No inactive members found in the last {n} days.")
    if inactive_whitelisted_members:
        await ctx.send(f"**Did not kick {str(len(inactive_whitelisted_members))} whitelisted inactive members:**\n" + "\n".join(inactive_whitelisted_members))


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)
    for guild in bot.guilds:
        await fetch_messages(guild)


with open(f'{working_dir}/goodbye_songs.json', 'r', encoding='utf-8') as f:
    goodbye_songs = json.load(f)

@tasks.loop(seconds=120)
async def change_song():
    random_song = random.choice(goodbye_songs)
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{random_song['title']} by {random_song['artist']}"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        await fetch_messages(guild)
    logger.info("Ready for your commands!")
    change_song.start()

# Run the bot
bot.run(api_token)
