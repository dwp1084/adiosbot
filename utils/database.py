import asyncio
import logging
import queue
import sqlite3
import threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Database:
    def __init__(self):
        self.tasks = queue.Queue()
        self.conn = sqlite3.connect(
            "activity.db",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row
        self.running = True

        # Run setup query, then close, so it can be opened in worker thread.
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS last_message (
                guild_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                uname       TEXT NOT NULL,
                timestamp   DATETIME NOT NULL,
                PRIMARY KEY(guild_id, user_id)
            );
            
            CREATE TABLE IF NOT EXISTS sync_progress (
                guild_id    TEXT PRIMARY KEY NOT NULL,
                timestamp   DATETIME NOT NULL,
                synced      BOOLEAN NOT NULL
            );
        """)

        self.conn.commit()
        self.conn.close()

        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        self.conn = sqlite3.connect(
            "activity.db",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row
        while self.running:
            func, args, kwargs, result_queue = self.tasks.get()
            try:
                cursor = self.conn.cursor()
                logger.debug(f"Running db function {func.__name__} with args {args}")
                value, written = func(cursor, *args, **kwargs)
                if written:
                    self.conn.commit()
                result_queue.put((True, value))
            except Exception as e:
                result_queue.put((False, e))

    def submit(self, func, *args, **kwargs):
        result_queue = queue.Queue()
        self.tasks.put((func, args, kwargs, result_queue))
        ok, value = result_queue.get()
        if ok:
            return value
        else:
            logger.error(f"Uncaught exception in database function.")
            raise value

    def close(self):
        self.running = False
        self.conn.close()

_database = Database()

async def db_exec(func, *args, **kwargs):
    """
    Async wrapper for database connection. Submits a database function to run in
    the database thread, then returns the result
    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    loop = asyncio.get_running_loop()
    logger.debug("Submitting function...")
    return await loop.run_in_executor(
        None,
        lambda: _database.submit(func, *args, **kwargs)
    )

# Database functions - don't use these directly. Instead, pass these through
# db_exec, which will pass the arguments along to the database connection in its
# own separate thread.
# The first argument should be a sqlite cursor, which is provided by the
# connection. All other arguments should be passed in by the user.

# All these functions have 2 return values - the first is the actual return
# value from the database (or None). The second indicates if the function
# wrote anything to the database, determining if there are changes to be
# committed.

def add_timestamp(cursor:sqlite3.Cursor, guild_id, user_id, uname, timestamp):
    add_timestamp_sql = """
    INSERT INTO last_message(guild_id, user_id, uname, timestamp)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(guild_id, user_id)
    DO UPDATE SET
        timestamp = excluded.timestamp
    WHERE excluded.timestamp > last_message.timestamp;
    """

    cursor.execute(add_timestamp_sql, (guild_id, user_id, uname, timestamp))
    return None, True

def add_sync_progress(cursor: sqlite3.Cursor, guild_id, timestamp):
    add_sync_progress_sql = """
    INSERT INTO sync_progress(guild_id, timestamp, synced)
    VALUES (?, ?, FALSE)
    ON CONFLICT (guild_id)
    DO UPDATE SET
        timestamp = excluded.timestamp,
        synced = excluded.synced
    WHERE excluded.timestamp > sync_progress.timestamp;
    """

    cursor.execute(add_sync_progress_sql, (guild_id, timestamp))
    return None, True

def finish_sync(cursor: sqlite3.Cursor, guild_id):
    finish_sync_sql = """
    INSERT INTO sync_progress(guild_id, timestamp, synced)
    VALUES (?, datetime('now'), TRUE)
    ON CONFLICT (guild_id)
    DO UPDATE SET
        synced = excluded.synced
    WHERE excluded.timestamp > sync_progress.timestamp;
    """

    cursor.execute(finish_sync_sql, (guild_id,))
    return None, True

def get_last_active_time(cursor: sqlite3.Cursor, guild_id, user_id):
    get_last_active_time_sql = """
    SELECT timestamp FROM last_message
    WHERE guild_id = ? AND user_id = ?;
    """

    cursor.execute(get_last_active_time_sql, (guild_id, user_id))
    results = cursor.fetchone()
    results = results[0] if results is not None else None
    return results, False

def get_last_active_times(cursor: sqlite3.Cursor, guild_id):
    get_last_active_times_sql = """
    SELECT user_id, timestamp FROM last_message WHERE guild_id = ?;
    """

    cursor.execute(get_last_active_times_sql, (guild_id,))
    return cursor.fetchall(), False

def get_last_stored_timestamp(cursor: sqlite3.Cursor, guild_id):
    get_last_stored_timestamp_sql = """
    SELECT timestamp FROM last_message
    WHERE guild_id = ?
    ORDER BY timestamp DESC;
    """

    cursor.execute(get_last_stored_timestamp_sql, (guild_id,))
    results = cursor.fetchone()
    results = results[0] if results is not None else None
    return results, False

def get_limit(cursor: sqlite3.Cursor, guild_id):
    """
    Gets the intended limit from the database based both on sync data and latest timestamp.

    If the bot were to stop during a sync, the sync data stores the last synced timestamp, which will be used as a limit
    for the next sync. Otherwise, if the bot finished syncing, it uses the latest timestamp from any message it has
    stored.

    If no data exists yet for the guild, this would return None, which allows the program to set its own limit.

    :param cursor: SQLite connection cursor
    :param guild_id: ID of the guild
    :return: The sync message timestamp limit, or None if no data is found for the guild.
    """
    get_sync_data_sql = """
    SELECT timestamp, synced FROM sync_progress WHERE guild_id = ?;
    """

    get_last_stored_timestamp_sql = """
    SELECT timestamp FROM last_message
    WHERE guild_id = ?
    ORDER BY timestamp DESC;
    """

    cursor.execute(get_sync_data_sql, (guild_id,))
    results = cursor.fetchone()
    if results is not None:
        last_sync_success = results["synced"]
        if not last_sync_success:
            logger.debug("Last sync failed, using sync time timestamp.")
            return results["timestamp"], False

    logger.debug("No results found or last sync success - using latest message timestamp.")
    cursor.execute(get_last_stored_timestamp_sql, (guild_id,))
    results = cursor.fetchone()
    results = results[0] if results is not None else None
    return results, False


def remove_user(cursor: sqlite3.Cursor, guild_id, user_id):
    remove_user_sql = """
    DELETE FROM last_message WHERE guild_id = ? AND user_id = ?;
    """

    cursor.execute(remove_user_sql, (guild_id, user_id))
    return None, True