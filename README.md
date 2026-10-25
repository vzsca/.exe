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
- Owner-ID and SQLite-backed whitelist access checks.
- Owner-only whitelist management: `!exe admin add @user`, `!exe admin remove @user`, and `!exe admin list`.
- SQLite tables for custom scripts, event handlers, and whitelist entries.
- Limits on script size, action count, message size, repeat count/depth, and execution time.
- Create and save named scripts directly in Discord after syntax validation.
- List, run, and delete a user's own saved scripts; saved scripts are revalidated and use the same execution limits as direct scripts.
- Script-generated messages cannot ping users or roles.
- Automated parser and storage tests, plus a GitHub Actions test workflow.

Still to build: conditionals, richer values and expressions, Discord administration actions, event-handler commands and execution, and `sudo` verification.

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
- Whitelist membership grants permission to run scripts, not owner privileges.
- Whitelist changes are persisted in SQLite and are only available to the configured owner.
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

The SQLite file is created automatically at `DATABASE_PATH` (default: `data/exe.sqlite3`).

Run tests with `python -m pip install -r requirements-dev.txt`, then `python -m pytest`.

## Discord commands

Only the configured owner and whitelisted users can use script commands.

- `!exe <script>` — run a script immediately.
- `!exe create <name> :: <script>` — validate and save a named script without running it.
- `!exe list` — list your saved scripts.
- `!exe run <name>` — run one of your saved scripts.
- `!exe delete <name>` — delete one of your saved scripts.
- `!help_exe` — show command and syntax help.
- `!exe admin add @user`, `!exe admin remove @user`, `!exe admin list` — owner-only whitelist management.

Example: `!exe create hello :: let greeting = "Hello"; send(greeting)`.

Each saved script is private to the Discord user who created it; the commands do not let users run or delete another user's scripts.
 
## Security note

A one-time code sent through Discord DM adds a confirmation step, but it is not independent multi-factor authentication if the Discord account itself is compromised. Sensitive actions must still require strict owner checks and short-lived, single-use challenges.

## License

License not selected yet.
