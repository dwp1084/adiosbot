import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from utils.database import db_exec, remove_user
from utils.functions import get_last_message_time, get_whitelist
from utils.syncmanager import sync_manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick_inactive", description="Kick inactive users")
    @app_commands.describe(n="Threshold for inactivity in number of days. Default is 30 days.")
    @app_commands.checks.has_permissions(administrator=True)
    async def kick_inactive(self, interaction: Interaction, n: int = 30):
        if not sync_manager.is_ready(interaction.guild.id):
            await interaction.response.send_message("Message history is still syncing - please try again later.")
            return

        logger.debug(f"Command received - /kick_inactive {n}")
        await interaction.response.send_message(f"Kicking members who haven't sent a message in the last {n} days...")
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
                        try:
                            await member.kick(reason=f"Inactive in {guild.name} for {n} days")
                            logger.info(f"Kicked {member.name} in {guild.name} for inactivity.")
                            await db_exec(
                                remove_user,
                                guild.id,
                                member.id
                            )
                        except Exception as e:
                            logger.error(f'Error kicking {member.name}: {str(e)}')
                    else:
                        inactive_whitelisted_members.append(member.name)

        inactive_members.sort()
        inactive_whitelisted_members.sort()

        response_str = ""

        if inactive_members:
            response_str += f"**Kicked {str(len(inactive_members))} members which were inactive in the last {n} days**\n" + "\n".join(
                    inactive_members)
        else:
            response_str += f"No inactive members found in the last {n} days."

        if inactive_whitelisted_members:
            response_str += f"\n\n({str(len(inactive_whitelisted_members))} whitelisted members spared)"

        await interaction.followup.send(response_str)

    @app_commands.command(name="ban", description='"Bans" a user :3')
    @app_commands.describe(user="The user to ban")
    async def ban_user(self, interaction: Interaction, user: discord.Member):
        logger.debug(f"Command received - /ban {user}")
        author = interaction.user
        if author.guild_permissions.administrator:
            if user == author:
                await interaction.response.send_message("**Can't timeout yourself!**")
            else:
                await user.timeout(timedelta(minutes=1), reason="For reasons")
                await interaction.response.send_message(f"**User {user.name} was timed out for 1 minute**")
        else:
            await author.timeout(timedelta(minutes=1), reason="Why did you think that would work? You fool. You buffoon.")
            await interaction.response.send_message(f"**Why did you think that would work? You fool. You buffoon.**")

async def setup(bot):
    await bot.add_cog(Moderation(bot))