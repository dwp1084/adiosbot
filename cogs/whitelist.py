import logging

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from utils.functions import get_whitelist, set_whitelist
from utils.globals import WHITELIST_DIR

wl_dir = WHITELIST_DIR

logger = logging.getLogger(__name__)

async def get_whitelist_str(whitelist, guild):
    whitelist_str = ""
    for wl_id in whitelist:
        try:
            member = await guild.fetch_member(wl_id)
            whitelist_str += f"\n{member}"
        except discord.NotFound:
            # If a user has left the server, don't add their ID
            pass

    return whitelist_str

class WhiteList(commands.GroupCog, name="whitelist"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="show", description="Show the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show(self, interaction: Interaction):
        logger.debug("Command received - /whitelist show")
        guild = interaction.guild
        whitelist = get_whitelist(guild)
        if len(whitelist) > 0:
            whitelist_str = await get_whitelist_str(whitelist, guild)

            await interaction.response.send_message(
                f"**Whitelisted members (will not be kicked out even when inactive):** \n{whitelist_str}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"**No members currently on the whitelist**", ephemeral=True)

    @app_commands.command(name="add", description="Add a user to the whitelist.")
    @app_commands.describe(user="The user to add to the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: Interaction, user: discord.Member):
        name = user.name
        logger.debug(f"Command received - /whitelist add {name}")
        guild = interaction.guild
        existing_members = get_whitelist(guild)
        if user not in guild.members:
            await interaction.response.send_message(f"**User {name} does not exist or is not a member of this server**",
                                                    ephemeral=True)
            return
        if user.id in existing_members:
            await interaction.response.send_message(f"**User {name} is already on the whitelist**", ephemeral=True)
            return
        new_members = existing_members + [user.id]

        set_whitelist(guild, new_members)

        whitelist_str = await get_whitelist_str(new_members, guild)

        await interaction.response.send_message(
            f"**User {name} was added to the whitelist**\nThe whitelist currently contains the following users:\n{whitelist_str}",
            ephemeral=True
        )

    @app_commands.command(name="remove", description="Remove a user from the whitelist.")
    @app_commands.describe(user="The user to remove from the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: Interaction, user: discord.Member):
        name = user.name
        logger.debug(f"Command received - /whitelist remove {name}")
        guild = interaction.guild
        existing_members = get_whitelist(guild)
        if user not in guild.members:
            await interaction.response.send_message(f"**User {name} does not exist or is not a member of this server**",
                                                    ephemeral=True)
            return
        if user.id not in existing_members:
            await interaction.response.send_message(f"**User {name} is not currently on the whitelist**", ephemeral=True)
            return
        existing_members.remove(user.id)

        set_whitelist(guild, existing_members)

        whitelist_str = await get_whitelist_str(existing_members, guild)

        await interaction.response.send_message(
            f"**User {name} was removed from the whitelist**\nThe whitelist currently contains the following users:\n{whitelist_str}",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(WhiteList(bot))