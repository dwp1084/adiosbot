import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SyncManager:
    def __init__(self):
        self._ready = {}
        self._syncing = True

        self.lock = asyncio.Lock()

    def add_guilds(self, guilds):
        self._syncing = True
        for guild in guilds:
            self._ready[guild.id] = False

    def is_ready(self, guild_id):
        return self._ready.get(guild_id, False)

    def set_ready(self, guild_id):
        logger.debug(f"{guild_id} is ready for commands.")
        self._ready[guild_id] = True

    def is_syncing(self):
        return self._syncing

    def finish_syncing(self):
        self._syncing = False

    def remove_guild(self, guild_id):
        self._ready.pop(guild_id)

sync_manager = SyncManager()