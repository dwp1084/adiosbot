import json
import logging

from discord import app_commands, Interaction
from discord.ext import commands

from utils.functions import get_whitelist
from utils.globals import WHITELIST_PATH

wl_path = WHITELIST_PATH

logger = logging.getLogger(__name__)

class WhiteList(commands.GroupCog, name="whitelist"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="show", description="Show the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show(self, interaction: Interaction):
        logger.debug("Command received - /whitelist show")
        whitelist = get_whitelist()
        if len(whitelist) > 0:
            whitelist = "\n".join(whitelist)
            await interaction.response.send_message(f"**Whitelisted members (will not be kicked out even when inactive):** \n" + whitelist, ephemeral=True)
        else:
            await interaction.response.send_message(f"**No members currently on the whitelist** \n" + whitelist, ephemeral=True)

    @app_commands.command(name="add", description="Add a user to the whitelist.")
    @app_commands.describe(name="The username to add to the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: Interaction, name: str):
        logger.debug(f"Command received - /whitelist add {name}")
        guild = interaction.guild
        existing_members = get_whitelist()
        if name not in [member.name for member in guild.members]:
            await interaction.response.send_message(f"**User {name} does not exist or is not a member of this server**", ephemeral=True)
            return
        if name in existing_members:
            await interaction.response.send_message(f"**User {name} is already on the whitelist**", ephemeral=True)
            return
        new_members = existing_members + [name]

        global wl_path
        if wl_path is None:
            from utils.globals import WHITELIST_PATH
            wl_path = WHITELIST_PATH

        with open(wl_path, 'w', encoding='utf-8') as f:
            json.dump(new_members, f, ensure_ascii=False, indent=4)

        await interaction.response.send_message(
            f"**User {name} was added to the whitelist**\nThe whitelist currently contains the following users:\n" + "\n".join(
                new_members),
            ephemeral=True
        )

    @app_commands.command(name="remove", description="Remove a user from the whitelist.")
    @app_commands.describe(name="The username to remove from the whitelist.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: Interaction, name: str):
        logger.debug(f"Command received - /whitelist remove {name}")
        guild = interaction.guild
        existing_members = get_whitelist()
        if name not in [member.name for member in guild.members]:
            await interaction.response.send_message(f"**User {name} does not exist or is not a member of this server**", ephemeral=True)
            return
        if name not in existing_members:
            await interaction.response.send_message(f"**User {name} is not currently on the whitelist**", ephemeral=True)
            return
        existing_members.remove(name)

        global wl_path
        if wl_path is None:
            from utils.globals import WHITELIST_PATH
            wl_path = WHITELIST_PATH

        with open(wl_path, 'w', encoding='utf-8') as f:
            json.dump(existing_members, f, ensure_ascii=False, indent=4)

        await interaction.response.send_message(f"**User {name} was removed from the whitelist**\nThe whitelist currently contains the following users:\n" + "\n".join(
                existing_members), ephemeral=True)

async def setup(bot):
    await bot.add_cog(WhiteList(bot))