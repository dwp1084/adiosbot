import logging
import os
from logging import Logger

import pytz
from dotenv import load_dotenv

# Make these names available elsewhere
working_dir: str | None = None
MESSAGE_LOG_DIR: str | None = None
WHITELIST_PATH: str | None = None
utc = pytz.UTC


def setup() -> str:
    global working_dir, MESSAGE_LOG_DIR, WHITELIST_PATH

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

    MESSAGE_LOG_DIR = working_dir + "/message_logs"
    if not os.path.exists(MESSAGE_LOG_DIR):
        os.makedirs(MESSAGE_LOG_DIR)
    WHITELIST_PATH = working_dir + "/whitelist.json"

    logger.info(MESSAGE_LOG_DIR)
    logger.info(WHITELIST_PATH)
    logger.info(working_dir)

    return api_token