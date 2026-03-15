# Last War Survival Alliance Bot - Design Specification

## Purpose

This Discord bot manages alliance member registration and profile data for a single
Last War Survival alliance within one Discord server.

The bot exists to:

- register alliance members through a guided workflow
- store each member's current in-game profile information
- track unregistered members for reminder workflows
- provide simple admin reporting against current profile data

This design intentionally favors simplicity over cleverness, because cleverness is
how small bots become maintenance projects with feelings.

---

## Design Priorities

1. Simplicity
2. Reliability
3. Minimal operational overhead
4. Clear data ownership
5. Easy local development and deployment

---

## Simplified V1 Scope

This rebuild uses a deliberately reduced design.

### Included

- Python bot built with `discord.py`
- SQLite as the only database
- one alliance per Discord server
- one profile per Discord user in V1
- session-based registration workflow
- current-value profile storage only
- unregistered user tracking for reminders
- admin hard delete of profiles
- dynamic country list from `pycountry`
- dynamic timezone list from `zoneinfo`
- static language list sourced from the game UI
- `account_type` retained for future expansion

### Explicitly Excluded

The system does **not** support the following in V1:

- soft delete
- name history
- squad history
- growth analytics
- multiple profiles per Discord user
- multiple alliances per server
- non-SQLite database backends

---

## Architecture

### Language

- Python 3.11+

### Libraries

- `discord.py`
- `pycountry`
- `zoneinfo` from the Python standard library
- `sqlite3` from the Python standard library

### Database

- SQLite only

### Storage Philosophy

The database stores the **current state only**.

If a user updates their profile, the previous values are replaced.
If an admin deletes a profile, it is physically removed from the database.
No audit trail or historical analytics are stored in V1.

---

## Core Functional Model

### Server Model

- One Discord server maps to one alliance.
- This bot is intended to manage one alliance roster for that server.
- Cross-server or cross-alliance data sharing is out of scope.

### User Model

In V1:

- one Discord user may have at most one profile
- `account_type` remains in the schema for future alt-account support
- only `main` is expected to be used in V1 logic

### Registration Model

Registration is handled through a session-based workflow.

A user starts registration, progresses through steps, and the bot stores in-progress
state in `registration_sessions`. When registration completes successfully:

- a row is created in `profiles`
- the user's session is removed
- the user is removed from `unregistered_tracking`

If the session expires, the user can start again.

### Unregistered Tracking

Users who join but do not complete registration are tracked separately so the bot can:

- know who still needs to register
- send reminder messages on a schedule
- stop reminders once registration is complete

---

## Registration Workflow

### On Member Join

1. Bot detects a new member joining the Discord server.
2. Bot assigns the configured unregistered role.
3. Bot creates or updates a row in `unregistered_tracking`.
4. User is directed to the registration channel.

### Registration Start

1. User starts registration from the registration channel.
2. Bot creates a `registration_sessions` row if one does not already exist.
3. Session state is updated after each completed step.

### Registration Data Collected

The registration workflow collects the following profile fields:

- Discord user ID
- Discord display name
- in-game name
- country code
- primary language code
- timezone
- event availability start minute
- event availability end minute
- squad A power and type
- squad B power and type (optional)
- squad C power and type (optional)
- squad D power and type (optional)
- account type

### Registration Completion

When registration is completed:

1. The profile is inserted into `profiles`.
2. The registration session row is deleted.
3. The unregistered tracking row is deleted.
4. The unregistered role is removed.
5. The member role is added.

---

## Data Sources

### Countries

Country options are generated dynamically from `pycountry`.

Stored value:

- ISO 3166-1 alpha-2 country code

Example:

- `US`
- `GB`
- `DE`

### Timezones

Timezone options are generated dynamically from `zoneinfo`.

Stored value:

- IANA timezone name

Example:

- `America/New_York`
- `Europe/London`
- `Asia/Tokyo`

### Languages

Language options are static and are derived from the game UI, not from `pycountry`.

Stored value:

- application-defined language code string

The exact list should live in application data, not in the database schema.

---

## Data Model

### `profiles`

Stores the current profile for each registered Discord user.

Rules:

- one row per Discord user in V1
- no history tables
- no soft delete fields
- current values only

Fields:

- `profile_id`
- `discord_user_id`
- `discord_display_name`
- `ingame_name`
- `account_type`
- `country_code`
- `primary_language_code`
- `timezone`
- `availability_start_minutes`
- `availability_end_minutes`
- `squad_a_power`
- `squad_a_type`
- `squad_b_power`
- `squad_b_type`
- `squad_c_power`
- `squad_c_type`
- `squad_d_power`
- `squad_d_type`
- `created_at`
- `updated_at`

### `registration_sessions`

Stores in-progress registration workflow state.

Fields:

- `discord_user_id`
- `step`
- `session_data_json`
- `created_at`
- `expires_at`

Notes:

- one active session per Discord user
- JSON payload stores incomplete workflow data until final submission

### `unregistered_tracking`

Tracks members who joined but have not completed registration.

Fields:

- `discord_user_id`
- `joined_at`
- `last_reminder_at`
- `reminder_count`

---

## Squad Model

The bot stores up to four squads per profile.

### Slots

- Squad A: required
- Squad B: optional
- Squad C: optional
- Squad D: optional

### Per-Squad Fields

Each squad stores:

- power
- type

### Allowed Squad Types

Canonical stored values:

- `tank`
- `air`
- `missile`
- `mixed`

### Validation Rules

- Squad A must always have both power and type.
- For squads B, C, and D:
  - both fields may be null
  - if power is set, type must be set
  - if type is set, power must be set

---

## Availability Model

Availability is stored as minutes-from-midnight integers.

Fields:

- `availability_start_minutes`
- `availability_end_minutes`

Rules:

- valid range is `0` through `1439`
- interpretation is relative to the user's stored timezone
- overnight windows are allowed
- the application layer is responsible for interpreting ranges

Example:

- `480` = 08:00
- `1320` = 22:00

---

## Hard Delete Policy

Admin profile deletion uses hard delete.

That means:

- the row is removed from `profiles`
- no tombstone record is kept
- no soft delete marker exists
- no history is retained in V1

This is intentional.

---

## Reminder Policy

Unregistered members receive reminders according to application logic.

Suggested schedule:

- at join / immediately as needed
- 12 hours
- 24 hours
- 48 hours
- weekly up to 30 days

The database only stores the minimum reminder state needed:

- when the user joined
- when the last reminder was sent
- how many reminders have been sent

The reminder schedule itself belongs in application logic, not schema design.

---

## Commands

### Member Commands

- `/profile view`
- `/profile update`
- `/register`

### Admin Commands

- `/admin delete_profile`
- `/admin report roster`
- `/admin report squad_power`
- `/admin report timezone_distribution`
- `/admin report unregistered`

Final command naming may vary during implementation, but the data model supports these use cases.

---

## Security Rules

- Members may view and update only their own profile.
- Admin actions require the configured alliance admin role.
- Profile responses should default to ephemeral where appropriate.
- Registration session data is temporary and should be discarded on completion or expiry.

---

## Reporting

V1 reporting is based only on current stored profile data.

Supported report categories:

- alliance roster
- squad power rankings
- timezone distribution
- unregistered member tracking

Reports may be rendered in Discord and optionally exported to CSV.

No growth or history reporting exists in V1 because we are not pretending a tiny SQLite bot is Snowflake.

---

## Database Constraints Summary

### Profiles

- one profile per Discord user
- `discord_user_id` must be unique
- `ingame_name` must be unique
- `account_type` allowed values:
  - `main`
  - `alt`
- `availability_start_minutes` and `availability_end_minutes` must be between `0` and `1439`
- squad type values limited to:
  - `tank`
  - `air`
  - `missile`
  - `mixed`

### Registration Sessions

- one active session per Discord user
- expired sessions are cleaned up by application logic

### Unregistered Tracking

- one tracking row per Discord user
- row is removed once registration completes or the user leaves, depending on bot policy

---

## Future Expansion

The design intentionally leaves room for later additions without implementing them now.

Potential future expansions:

- multiple profiles per Discord user
- true alt-account support using `account_type`
- audit history
- change history for names and squads
- analytics and growth tracking
- multiple alliances or multi-server support
- external database support

These are not part of V1 and should not shape current implementation beyond preserving sensible field names such as `account_type`.