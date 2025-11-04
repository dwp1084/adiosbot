import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from utils.functions import get_last_message_time, get_whitelist, remove_member_messages
from utils.globals import utc

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick_inactive", description="Kick inactive users")
    @app_commands.describe(n="Threshold for inactivity in number of days. Default is 30 days.")
    @app_commands.checks.has_permissions(administrator=True)
    async def kick_inactive(self, interaction: Interaction, n: int = 30):
        logger.debug(f"Command received - /kick_inactive {n}")
        await interaction.response.send_message(f"Kicking members who haven't sent a message in the last {n} days...")
        guild = interaction.guild

        user_last_message = get_last_message_time(guild)
        inactive_members = []
        inactive_whitelisted_members = []
        cutoff_date = datetime.now() - timedelta(days=n)

        whitelist = get_whitelist(guild)

        for member in guild.members:
            if not member.bot:
                last_message_time = user_last_message.get(member.id)
                if last_message_time is None or last_message_time < utc.localize(cutoff_date):
                    if member.name not in whitelist:
                        inactive_members.append(member.name)
                        remove_member_messages(member, guild)
                        try:
                            await member.kick(reason=f"Inactive in {guild.name} for {n} days")
                            await interaction.followup.send(f"**Kicked {member.name} for inactivity**")
                        except:
                            logger.error(f'Error kicking {member.name}')
                    else:
                        inactive_whitelisted_members.append(member.name)

        inactive_members.sort()
        inactive_whitelisted_members.sort()
        if inactive_members:
            await interaction.followup.send(f"**Kicked {str(len(inactive_members))} members which were inactive in the last {n} days**\n" + "\n".join(
                    inactive_members))
        else:
            await interaction.followup.send(f"No inactive members found in the last {n} days.")
        if inactive_whitelisted_members:
            await interaction.followup.send(f"**Did not kick {str(len(inactive_whitelisted_members))} whitelisted inactive members:**\n" + "\n".join(
                    inactive_whitelisted_members))

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