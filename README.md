# `.exe` — Linux-inspired scripting for Discord

`.exe` is a Discord bot project built from scratch. It aims to provide a small, sandboxed scripting language for Discord actions, with two native syntaxes:

- **Standard**: readable and beginner-friendly.
- **Compact**: shorter, symbol-heavy syntax for experienced users.

Both syntaxes must compile to the same internal representation and use the same execution engine, permission checks, limits, and security rules.

## Status

Early foundation. The first milestone is a safe interpreter core; Discord actions, persistent custom commands, event handlers, and `sudo` verification will be added incrementally.

## Principles

- No `eval`, `exec`, arbitrary Python, OS shell access, or unrestricted file access.
- Scripts can only call explicitly registered actions.
- Owner identity is verified using the configured Discord user ID, not server Administrator permissions.
- Whitelist access does not grant owner privileges.
- Runtime, loop, and action limits protect the bot and server.
- Secrets belong in `.env`, never in source control.

## Requirements

- Python 3.12 or newer
- A Discord bot application and token

## Setup

1. Clone this repository.
2. Create and activate a virtual environment.
3. Install dependencies with `python -m pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in the values.
5. Start with `python -m exe_bot` from the `src` directory, or install the project in editable mode once packaging is added.

## Planned command concepts

- `!exe <script>` — run a short script.
- `!exe admin add @user` — owner-only whitelist management.
- `sudo` — additional confirmation for sensitive owner actions.

Command names and syntax are provisional until the first language specification is settled.

## Security note

A one-time code sent through Discord DM adds a confirmation step, but it is not independent multi-factor authentication if the Discord account itself is compromised. Sensitive actions must still require strict owner checks and short-lived, single-use challenges.

## License

License not selected yet.