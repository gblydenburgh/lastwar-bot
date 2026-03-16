# lastwar-bot

Discord bot for managing a single Last War Survival alliance in one Discord server.

## Features

- SQLite-backed profile storage
- Session-based registration workflow
- Join tracking for unregistered members
- Member profile viewing and updating
- Admin reports for roster, power, timezone spread, and unregistered members
- Runtime database stored at `var/lastwar.db`

## Requirements

- Python 3.12+
- `uv`
- A Discord application and bot token

## Install

```bash
uv sync
```

## Configuration

Set these environment variables before running:

- `DISCORD_TOKEN` required
- `DISCORD_GUILD_ID` optional, recommended for guild-scoped slash command sync
- `UNREGISTERED_ROLE_ID` optional
- `MEMBER_ROLE_ID` optional
- `ADMIN_ROLE_ID` optional
- `REGISTRATION_CHANNEL_ID` optional
- `REGISTRATION_SESSION_TTL_HOURS` optional, defaults to `24`

Example:

```bash
export DISCORD_TOKEN="your-bot-token"
export DISCORD_GUILD_ID="123456789012345678"
export UNREGISTERED_ROLE_ID="123456789012345678"
export MEMBER_ROLE_ID="123456789012345678"
export ADMIN_ROLE_ID="123456789012345678"
export REGISTRATION_CHANNEL_ID="123456789012345678"
export REGISTRATION_SESSION_TTL_HOURS="24"
```

## Run The Bot

```bash
uv run python main.py
```

On first run the app creates the SQLite database at `var/lastwar.db` and syncs slash commands.

## Discord Server Setup

### 1. Create the Discord application

1. Open the Discord Developer Portal.
2. Create a new application.
3. Add a bot user to the application.
4. Copy the bot token and set it as `DISCORD_TOKEN`.

### 2. Enable required bot settings

In the bot settings page:

- Enable `Server Members Intent`
- Keep the bot public/private setting however you prefer for your deployment

`Server Members Intent` is required because this bot listens for member joins and applies roles.

### 3. Create the server roles and channel

In your Discord server, create or identify:

- an unregistered role for new members
- a member role for completed registrations
- an admin role for alliance admins
- a registration text channel where new members are directed

Copy the numeric IDs for each role/channel and set the matching environment variables.

To copy IDs in Discord:

1. Open `User Settings > Advanced`
2. Enable `Developer Mode`
3. Right-click the server, role, or channel
4. Click `Copy Server ID`, `Copy Role ID`, or `Copy Channel ID`

### 4. Invite the bot to your server

In the Discord Developer Portal:

1. Open `OAuth2 > URL Generator`
2. Select scopes:
   - `bot`
   - `applications.commands`
3. Select bot permissions:
   - `View Channels`
   - `Send Messages`
   - `Use Slash Commands`
   - `Manage Roles`
   - `Read Message History`
4. Open the generated URL and invite the bot to your target server

The bot's highest role must be above the `UNREGISTERED_ROLE_ID` and `MEMBER_ROLE_ID` roles or Discord will reject role updates.

### 5. Set the guild ID

Set `DISCORD_GUILD_ID` to your server ID if you want slash commands to sync to one server immediately. This is the recommended setup for development and single-server deployment.

If you leave `DISCORD_GUILD_ID` unset, the bot uses global slash command sync, which can take longer to appear.

## First Run Checklist

- Start the bot with `uv run python main.py`
- Confirm the bot appears online in Discord
- Confirm slash commands such as `/register start` and `/profile view` are visible
- Join the server with a test account and verify the unregistered role is applied
- Complete registration and verify the member role replaces the unregistered role

## Operational Notes

- This bot is designed for one Discord server and one alliance
- Profiles are stored as current state only, with no history
- Admin deletion is a hard delete
- Registration sessions expire based on `REGISTRATION_SESSION_TTL_HOURS`
---
