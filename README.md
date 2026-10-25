# `.exe` — Linux-inspired scripting for Discord

`.exe` is a Discord bot project built from scratch. It provides the beginnings of a small, sandboxed scripting language for Discord actions, with two native syntaxes:

- **Standard**: readable and beginner-friendly.
- **Compact**: shorter, symbol-heavy syntax for experienced users.

Both syntaxes compile into the same internal instruction types and use the same execution engine, permissions, limits, and security rules.

## Current prototype

Implemented:
- `send("Hello")` / compact `m("Hello")` to send a message.
- `let greeting = "Hello"` / compact `v(greeting, "Hello")` to define a text variable.
- `send(greeting)` / compact `m(greeting)` to use a defined variable.
- `repeat 3: send("Hello")` / compact `R(3, m("Hello"))` for bounded repetition.
- Owner-ID and whitelist access checks.
- Limits on script size, action count, message size, repeat count/depth, and execution time.
- Script-generated messages cannot ping users or roles.
- Automated parser tests and a GitHub Actions test workflow.

Still to build: conditionals, richer values and expressions, Discord administration actions, custom commands/events saved in SQLite, owner-only whitelist management commands, and `sudo` verification.

## Syntax examples

Standard:

```text
let greeting = "Hello"
send(greeting)
repeat 3: send(greeting)
```

Compact:

```text
v(greeting, "Hello")
m(greeting)
R(3, m(greeting))
```

For multiple instructions in Discord, send a fenced code block after `!exe`. Semicolons can also separate instructions on a single line.

## Security principles

- No `eval`, `exec`, arbitrary Python, OS shell access, or unrestricted file access.
- Scripts can only call explicitly registered language instructions/actions.
- Owner identity is verified using `OWNER_ID`, not server Administrator permissions.
- Whitelist access does not grant owner privileges.
- Secrets belong in `.env`, never in source control.
- Script execution has configured time and action limits.

## Requirements and setup

- Python 3.12 or newer
- A Discord bot application and token

1. Clone the repository and enter its folder.
2. Create and activate a virtual environment.
3. Install the project: `python -m pip install -e .`
4. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `OWNER_ID`.
5. In the Discord Developer Portal, enable **Message Content Intent** for the bot.
6. Start it with `python -m exe_bot`.

Run tests with `python -m pip install -r requirements-dev.txt`, then `python -m pytest`.

## Planned command concepts

- `!exe <script>` — run a script.
- `!exe admin add @user` — owner-only whitelist management.
- `sudo` — additional confirmation for sensitive owner actions.

Command names and syntax are provisional until the language specification is settled.

## Security note

A one-time code sent through Discord DM adds a confirmation step, but it is not independent multi-factor authentication if the Discord account itself is compromised. Sensitive actions must still require strict owner checks and short-lived, single-use challenges.

## License

License not selected yet.
