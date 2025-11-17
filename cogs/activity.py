import json
import logging
import random
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from utils.database import db_exec, get_last_active_time
from utils.functions import get_last_message_time, get_whitelist
from utils.globals import working_dir
from utils.syncmanager import sync_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Activity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.change_song.start()

        with open(f'{working_dir}/goodbye_songs.json', 'r', encoding='utf-8') as f:
            self.goodbye_songs = json.load(f)

    @app_commands.command(name="inactive", description="Checks which users have been inactive for n days.")
    @app_commands.describe(n="Number of days of inactivity")
    async def check_inactive(self, interaction: Interaction, n: int = 30):
        if not sync_manager.is_ready(interaction.guild.id):
            await interaction.response.send_message("Message history is still syncing - please try again later.", ephemeral=True)
            return

        logger.debug(f"Command received /inactive {n}")
        guild = interaction.guild

        user_last_message = await get_last_message_time(guild)
        inactive_members = []
        inactive_whitelisted_members = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=n)

        whitelist = get_whitelist(guild)

        for member in guild.members:
            if not member.bot:
                last_message_time = user_last_message.get(member.id)

                logger.debug(f"{member.name} lm {last_message_time} co {cutoff_date}")

                if last_message_time is None or last_message_time < cutoff_date:
                    if member.id not in whitelist:
                        inactive_members.append(member.name)
                    else:
                        inactive_whitelisted_members.append(member.name)

        inactive_members.sort()
        inactive_whitelisted_members.sort()

        response_str = ""

        if inactive_members:
            response_str += f"**{str(len(inactive_members))} inactive members in the last {n} days:**\n" + "\n".join(
                inactive_members)
        else:
            response_str += f"No inactive members found in the last {n} days."

        if inactive_whitelisted_members:
            response_str += f"\n\n(Not including {str(len(inactive_whitelisted_members))} whitelisted members who are inactive)"

        await interaction.response.send_message(response_str, ephemeral=True)

    @app_commands.command(name="last_message", description="Check when you were last active.")
    @app_commands.describe(user="User to check. Defaults to yourself. Only admins can check users other than themselves.")
    async def last_message(self, interaction: Interaction, user: discord.Member = None):
        if not sync_manager.is_ready(interaction.guild.id):
            await interaction.response.send_message("Message history is still syncing - please try again later.", ephemeral=True)
            return

        if type(interaction.user) is not discord.Member:
            logger.error(f"User {interaction.user.name} is not a member")
            await interaction.response.send_message("For some reason, you are not a member.", ephemeral=True)
            return

        self_check = user is None or user == interaction.user

        if (not interaction.user.guild_permissions.administrator
                and not self_check):
            await interaction.response.send_message(
                "Only administrators can check inactivity of users other than themselves.\nPlease try again, but without specifying a user other than yourself.",
                ephemeral=True
            )
            return

        if user is None:
            user = interaction.user

        if user.bot:
            await interaction.response.send_message("Don't worry about the bots, they're spared from my wrath. :upside_down:", ephemeral=True)
            return

        last_active_time = await db_exec(
            get_last_active_time,
            interaction.guild.id,
            user.id
        )

        if last_active_time is None:
            message = \
                "You have no message history that I can see. Send a message if you don't wanna be kicked!" \
                if self_check else \
                f"{user.name} does not have any message history that I can see."

            await interaction.response.send_message(message, ephemeral=True)
            return

        unix_timestamp = datetime.fromisoformat(last_active_time).timestamp()

        message = \
            f"Your last message was sent <t:{int(unix_timestamp)}:R>. Keep messaging if you don't want me kicking you. :wink:" \
            if self_check else \
            f"{user.name} last sent a message <t:{int(unix_timestamp)}:R>."

        await interaction.response.send_message(message, ephemeral=True)

    @tasks.loop(seconds=120)
    async def change_song(self):
        await self.bot.wait_until_ready()
        logger.debug("Changing song status")
        random_song = random.choice(self.goodbye_songs)
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{random_song['title']} by {random_song['artist']}"
        )
        await self.bot.change_presence(activity=activity)

async def setup(bot):
    await bot.add_cog(Activity(bot))