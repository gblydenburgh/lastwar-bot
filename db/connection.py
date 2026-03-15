from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


SCHEMA_SQL: str = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL UNIQUE,
    discord_display_name TEXT,
    ingame_name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'main'
        CHECK (account_type IN ('main', 'alt')),
    country_code TEXT NOT NULL,
    primary_language_code TEXT NOT NULL,
    timezone TEXT NOT NULL,
    availability_start_minutes INTEGER NOT NULL
        CHECK (availability_start_minutes >= 0 AND availability_start_minutes <= 1439),
    availability_end_minutes INTEGER NOT NULL
        CHECK (availability_end_minutes >= 0 AND availability_end_minutes <= 1439),
    squad_a_power INTEGER NOT NULL
        CHECK (squad_a_power >= 0),
    squad_a_type TEXT NOT NULL
        CHECK (squad_a_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_b_power INTEGER
        CHECK (squad_b_power IS NULL OR squad_b_power >= 0),
    squad_b_type TEXT
        CHECK (squad_b_type IS NULL OR squad_b_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_c_power INTEGER
        CHECK (squad_c_power IS NULL OR squad_c_power >= 0),
    squad_c_type TEXT
        CHECK (squad_c_type IS NULL OR squad_c_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_d_power INTEGER
        CHECK (squad_d_power IS NULL OR squad_d_power >= 0),
    squad_d_type TEXT
        CHECK (squad_d_type IS NULL OR squad_d_type IN ('tank', 'air', 'missile', 'mixed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK (
        (squad_b_power IS NULL AND squad_b_type IS NULL) OR
        (squad_b_power IS NOT NULL AND squad_b_type IS NOT NULL)
    ),
    CHECK (
        (squad_c_power IS NULL AND squad_c_type IS NULL) OR
        (squad_c_power IS NOT NULL AND squad_c_type IS NOT NULL)
    ),
    CHECK (
        (squad_d_power IS NULL AND squad_d_type IS NULL) OR
        (squad_d_power IS NOT NULL AND squad_d_type IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS registration_sessions (
    discord_user_id TEXT PRIMARY KEY,
    step TEXT NOT NULL,
    session_data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unregistered_tracking (
    discord_user_id TEXT PRIMARY KEY,
    joined_at TEXT NOT NULL,
    last_reminder_at TEXT,
    reminder_count INTEGER NOT NULL DEFAULT 0
        CHECK (reminder_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_profiles_ingame_name
    ON profiles(ingame_name);

CREATE INDEX IF NOT EXISTS idx_profiles_country_code
    ON profiles(country_code);

CREATE INDEX IF NOT EXISTS idx_profiles_primary_language_code
    ON profiles(primary_language_code);

CREATE INDEX IF NOT EXISTS idx_profiles_timezone
    ON profiles(timezone);

CREATE INDEX IF NOT EXISTS idx_profiles_account_type
    ON profiles(account_type);

CREATE INDEX IF NOT EXISTS idx_registration_sessions_expires_at
    ON registration_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_unregistered_tracking_joined_at
    ON unregistered_tracking(joined_at);

CREATE INDEX IF NOT EXISTS idx_unregistered_tracking_last_reminder_at
    ON unregistered_tracking(last_reminder_at);
"""


def dict_row_factory(
    cursor: sqlite3.Cursor,
    row: tuple[object, ...],
) -> dict[str, object]:
    """Return rows as plain dictionaries."""
    return {
        column[0]: row[index]
        for index, column in enumerate(cursor.description)
    }


class DatabaseManager:
    """
    Minimal SQLite database wrapper for the bot.

    This stays intentionally thin. Small bots do not need an ORM and,
    frankly, humanity has suffered enough.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path: Path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        """Open a configured SQLite connection."""
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
        """Create required tables and indexes."""
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a connection wrapped in an explicit transaction."""
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
        """Open a connection without forcing a transaction block."""
        connection: sqlite3.Connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def health_check(self) -> bool:
        """Verify the database is reachable."""
        with self.connection() as connection:
            result: Optional[dict[str, object]] = connection.execute(
                "SELECT 1 AS ok;"
            ).fetchone()
            return bool(result and result.get("ok") == 1)


if __name__ == "__main__":
    database: DatabaseManager = DatabaseManager(
        "/opt/lastwar-bot/data/lastwar_bot.db"
    )
    database.initialize()

    if database.health_check():
        print(f"Database initialized successfully at: {database.db_path}")
    else:
        print("Database health check failed.")