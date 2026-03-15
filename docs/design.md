# Last War Survival Alliance Bot — Design Specification

## Purpose

This Discord bot manages alliance member profiles for the mobile game
"Last War Survival".

The bot enforces registration for Discord members and stores the basic
information needed for alliance coordination.

Design priorities:

- simplicity
- reliability
- minimal operational overhead


## Architecture

Language: Python

Libraries:

- discord.py
- pycountry
- Python zoneinfo (standard library)

Database: SQLite


### Project Structure

bot/
  main.py
  cogs/           # slash command handlers
  ui/             # Discord views, dropdowns, modals

db/
  connection.py   # database initialization
  profiles.py     # profile repository
  sessions.py     # registration session storage

workflows/
  registration.py # onboarding state machine

data/
  dynamic_lookups.py
  languages.py

services/
  reports.py


## Registration Workflow

When a Discord user joins the server:

1. Bot assigns the "unregistered" role.
2. The user must complete registration.
3. Registration is initiated from the #registration channel.

Registration collects:

- in-game name
- country
- primary language
- timezone
- event availability window
- squad power levels

After registration:

- profile is stored
- unregistered role removed
- member role added


## Data Model

Profiles store **current values only**.

The system does NOT track:

- historical squad power
- growth analytics
- deleted profile history


### profiles table

id  
discord_user_id  
discord_display_name  
ingame_name  
country_code  
primary_language_code  
timezone  
availability_start_minutes  
availability_end_minutes  
squad_a_power  
squad_a_type  
squad_b_power  
squad_b_type  
squad_c_power  
squad_c_type  
squad_d_power  
squad_d_type  
account_type  
created_at  
last_updated_at


### registration_sessions table

discord_user_id  
session_data_json  
step  
created_at  
expires_at


### unregistered_tracking table

discord_user_id  
joined_at  
last_reminder_at  
reminder_count


## Squad Model

Squads:

A — required  
B — optional  
C — optional  
D — optional

Each squad stores:

- power (integer)
- type

Allowed squad types:

- tank
- air
- missile
- mixed


## Reminder Policy

Unregistered members receive reminders at:

- 0 hours
- 12 hours
- 24 hours
- 48 hours
- weekly for up to 30 days


## Dynamic Data

Country list is sourced from pycountry.

Timezone list is sourced from Python zoneinfo.

Languages are a static list derived from the game UI.


## Commands

Member commands

/profile view  
/profile update_squad  

Admin commands

/admin delete_profile  
/admin report roster  
/admin report squad_power  


## Security Rules

Members may modify only their own profile.

Admin commands require the alliance-admin role.

Profile responses default to ephemeral messages.


## Reporting

Reports available to admins:

- alliance roster
- squad power rankings
- timezone distribution

Reports may be exported to CSV.


## Future Expansion

The schema includes account_type to allow future support
for alternate accounts.

Only one main account per Discord user will be supported.