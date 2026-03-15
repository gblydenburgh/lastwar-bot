from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator, Optional


SCHEMA_SQL: str = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,

    discord_user_id TEXT NOT NULL,
    discord_display_name TEXT,

    ingame_name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'main'
        CHECK (account_type IN ('main', 'alt')),

    country_code TEXT NOT NULL,
    primary_language_code TEXT NOT NULL,
    secondary_language_code TEXT,

    timezone TEXT NOT NULL,

    availability_start_min INTEGER NOT NULL
        CHECK (availability_start_min >= 0 AND availability_start_min <= 1439),
    availability_end_min INTEGER NOT NULL
        CHECK (availability_end_min >= 0 AND availability_end_min <= 1439),

    squad_a_power INTEGER NOT NULL CHECK (squad_a_power >= 0),
    squad_a_type TEXT NOT NULL
        CHECK (squad_a_type IN ('Tank', 'Air', 'Missile', 'Mixed')),

    squad_b_power INTEGER CHECK (squad_b_power >= 0),
    squad_b_type TEXT
        CHECK (squad_b_type IN ('Tank', 'Air', 'Missile', 'Mixed')),

    squad_c_power INTEGER CHECK (squad_c_power >= 0),
    squad_c_type TEXT
        CHECK (squad_c_type IN ('Tank', 'Air', 'Missile', 'Mixed')),

    squad_d_power INTEGER CHECK (squad_d_power >= 0),
    squad_d_type TEXT
        CHECK (squad_d_type IN ('Tank', 'Air', 'Missile', 'Mixed')),

    created_at TEXT NOT NULL,
    last_squad_update_at TEXT NOT NULL,
    deleted_at TEXT,

    CHECK (
        secondary_language_code IS NULL
        OR secondary_language_code <> primary_language_code
    ),

    CHECK (
        squad_b_power IS NULL OR squad_b_type IS NOT NULL
    ),
    CHECK (
        squad_c_power IS NULL OR squad_c_type IS NOT NULL
    ),
    CHECK (
        squad_d_power IS NULL OR squad_d_type IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS name_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    old_name TEXT NOT NULL,
    changed_at TEXT NOT NULL,

    FOREIGN KEY (profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS squad_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    squad_slot TEXT NOT NULL
        CHECK (squad_slot IN ('A', 'B', 'C', 'D')),

    old_power INTEGER CHECK (old_power >= 0),
    new_power INTEGER CHECK (new_power >= 0),

    old_type TEXT
        CHECK (old_type IN ('Tank', 'Air', 'Missile', 'Mixed')),
    new_type TEXT
        CHECK (new_type IN ('Tank', 'Air', 'Missile', 'Mixed')),

    changed_at TEXT NOT NULL,

    FOREIGN KEY (profile_id)
        REFERENCES profiles(profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registration_sessions (
    discord_user_id TEXT PRIMARY KEY,
    current_step TEXT NOT NULL,
    session_data_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unregistered_tracking (
    discord_user_id TEXT PRIMARY KEY,
    joined_at TEXT NOT NULL,
    last_reminder_at TEXT,
    reminder_count INTEGER NOT NULL DEFAULT 0 CHECK (reminder_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_profiles_discord_user_id
    ON profiles(discord_user_id);

CREATE INDEX IF NOT EXISTS idx_profiles_deleted_at
    ON profiles(deleted_at);

CREATE INDEX IF NOT EXISTS idx_profiles_account_type
    ON profiles(account_type);

CREATE INDEX IF NOT EXISTS idx_profiles_last_squad_update_at
    ON profiles(last_squad_update_at);

CREATE INDEX IF NOT EXISTS idx_name_history_profile_id
    ON name_history(profile_id);

CREATE INDEX IF NOT EXISTS idx_squad_history_profile_id
    ON squad_history(profile_id);

CREATE INDEX IF NOT EXISTS idx_squad_history_changed_at
    ON squad_history(changed_at);
"""


def dict_row_factory(cursor: sqlite3.Cursor, row: tuple[object, ...]) -> dict[str, object]:
    """
    Return rows as plain dictionaries instead of sqlite3.Row objects.

    This is often easier to debug and serialize.
    """
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


class DatabaseManager:
    """
    Small SQLite wrapper for initializing and accessing the bot database.

    This class is intentionally thin. It does not try to be an ORM because
    life is short and ORMs in small bots are often a self-inflicted injury.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path: Path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        """
        Open a SQLite connection with the settings required by this bot.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        connection: sqlite3.Connection = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None,  # explicit transaction control
        )
        connection.row_factory = dict_row_factory
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute("PRAGMA synchronous = NORMAL;")
        return connection

    def initialize(self) -> None:
        """
        Create all required tables and indexes if they do not already exist.
        """
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Open a connection and wrap operations in an explicit transaction.

        Usage:
            with db.transaction() as conn:
                conn.execute(...)
                conn.execute(...)

        If any exception occurs, the transaction is rolled back automatically.
        """
        connection: sqlite3.Connection = self._connect()
        try:
            connection.execute("BEGIN;")
            yield connection
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise
        finally:
            connection.close()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Open a read/write connection without forcing a transaction block.

        Useful for simple read operations.
        """
        connection: sqlite3.Connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def health_check(self) -> bool:
        """
        Run a trivial query to verify the database is reachable.
        """
        with self.connection() as connection:
            result: Optional[dict[str, object]] = connection.execute(
                "SELECT 1 AS ok;"
            ).fetchone()
        return bool(result and result.get("ok") == 1)


if __name__ == "__main__":
    # Example usage for local testing.
    database = DatabaseManager("/opt/lastwar-bot/data/lastwar_bot.db")
    database.initialize()

    if database.health_check():
        print(f"Database initialized successfully at: {database.db_path}")
    else:
        print("Database health check failed.")
