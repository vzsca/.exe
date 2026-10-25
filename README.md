# `.exe` — Linux-inspired scripting for Discord

`.exe` is a Discord bot project built from scratch. It aims to provide a small, sandboxed scripting language for Discord actions, with two native syntaxes:

- **Standard**: readable and beginner-friendly.
- **Compact**: shorter, symbol-heavy syntax for experienced users.

Both syntaxes must compile to the same internal representation and use the same execution engine, permission checks, limits, and security rules.

## Status

Early foundation. The current prototype supports only sending a text message, using either `send("Hello")` or compact `m("Hello")`. Variables, control flow, Discord administration actions, persistent scripts, event handlers, and `sudo` verification are not implemented yet.

## Security principles

- No `eval`, `exec`, arbitrary Python, OS shell access, or unrestricted file access.
- Scripts can only call explicitly registered actions.
- Owner identity is verified using the configured Discord user ID, not server Administrator permissions.
- Whitelist access does not grant owner privileges.
- Script size, action count, message size, and runtime are limited.
- Script-generated messages do not trigger user or role mentions.
- Secrets belong in `.env`, never in source control.

## Requirements

- Python 3.12 or newer
- A Discord bot application and token

## Setup

1. Clone the repository and enter its folder.
2. Create and activate a virtual environment.
3. Install the project: `python -m pip install -e .`
4. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `OWNER_ID`.
5. In the Discord Developer Portal, enable **Message Content Intent** for the bot.
6. Start it with `python -m exe_bot`.

Run tests with `python -m pip install -r requirements-dev.txt`, then `python -m pytest`.

## Test syntax

- Standard: `!exe send("Hello")`
- Compact: `!exe m("Hello")`

For a multiline script, put the instructions in a fenced code block after `!exe`.

The language is intentionally limited at this stage. Unsupported instructions return a line-specific syntax error instead of being executed as Python.

## Planned command concepts

- `!exe <script>` — run a short script.
- `!exe admin add @user` — owner-only whitelist management.
- `sudo` — additional confirmation for sensitive owner actions.

Command names and syntax are provisional until the language specification is settled.

## Security note

A one-time code sent through Discord DM adds a confirmation step, but it is not independent multi-factor authentication if the Discord account itself is compromised. Sensitive actions must still require strict owner checks and short-lived, single-use challenges.

## License

License not selected yet.
