SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id INTEGER NOT NULL UNIQUE,
    discord_display_name TEXT NOT NULL,
    ingame_name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL CHECK (account_type IN ('main', 'alt')),
    country_code TEXT NOT NULL,
    primary_language_code TEXT NOT NULL,
    timezone TEXT NOT NULL,
    availability_start_minutes INTEGER NOT NULL CHECK (availability_start_minutes BETWEEN 0 AND 1439),
    availability_end_minutes INTEGER NOT NULL CHECK (availability_end_minutes BETWEEN 0 AND 1439),
    squad_a_power INTEGER NOT NULL CHECK (squad_a_power >= 0),
    squad_a_type TEXT NOT NULL CHECK (squad_a_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_b_power INTEGER CHECK (squad_b_power IS NULL OR squad_b_power >= 0),
    squad_b_type TEXT CHECK (squad_b_type IS NULL OR squad_b_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_c_power INTEGER CHECK (squad_c_power IS NULL OR squad_c_power >= 0),
    squad_c_type TEXT CHECK (squad_c_type IS NULL OR squad_c_type IN ('tank', 'air', 'missile', 'mixed')),
    squad_d_power INTEGER CHECK (squad_d_power IS NULL OR squad_d_power >= 0),
    squad_d_type TEXT CHECK (squad_d_type IS NULL OR squad_d_type IN ('tank', 'air', 'missile', 'mixed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((squad_b_power IS NULL AND squad_b_type IS NULL) OR (squad_b_power IS NOT NULL AND squad_b_type IS NOT NULL)),
    CHECK ((squad_c_power IS NULL AND squad_c_type IS NULL) OR (squad_c_power IS NOT NULL AND squad_c_type IS NOT NULL)),
    CHECK ((squad_d_power IS NULL AND squad_d_type IS NULL) OR (squad_d_power IS NOT NULL AND squad_d_type IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS registration_sessions (
    discord_user_id INTEGER PRIMARY KEY,
    step TEXT NOT NULL,
    session_data_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unregistered_tracking (
    discord_user_id INTEGER PRIMARY KEY,
    joined_at TEXT NOT NULL,
    last_reminder_at TEXT,
    reminder_count INTEGER NOT NULL DEFAULT 0 CHECK (reminder_count >= 0)
);
"""
