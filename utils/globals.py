import logging
import os

from dotenv import load_dotenv

# Make these names available elsewhere
working_dir: str | None = None
MESSAGE_LOG_DIR: str | None = None
WHITELIST_DIR: str | None = None


def setup() -> str:
    global working_dir, MESSAGE_LOG_DIR, WHITELIST_DIR

    logger = logging.getLogger(__name__)

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

    MESSAGE_LOG_DIR = os.path.join(working_dir, "message_logs")
    if not os.path.exists(MESSAGE_LOG_DIR):
        os.makedirs(MESSAGE_LOG_DIR)
    WHITELIST_DIR = os.path.join(working_dir, "whitelists")
    if not os.path.exists(WHITELIST_DIR):
        os.makedirs(WHITELIST_DIR)

    logger.debug(MESSAGE_LOG_DIR)
    logger.debug(WHITELIST_DIR)
    logger.debug(working_dir)

    return api_token