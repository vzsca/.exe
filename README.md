# `.exe` — Linux-inspired scripting for Discord

`.exe` is a Discord bot project built from scratch. It provides the beginnings of a small, sandboxed scripting language for Discord actions, with two native syntaxes:

- **Standard**: readable and beginner-friendly.
- **Compact**: shorter, symbol-heavy syntax for experienced users.

Both syntaxes compile into the same internal instruction types and use the same execution engine, permissions, limits, and security rules.

## Current prototype

Implemented:
- `send("Hello")` / compact `m("Hello")` to send a message. An optional second argument targets a text channel by exact name or ID, e.g. `send("Hello", "#general")` or `send("Hello", "123456789012345678")`.
- Discord actions: `ban`, `unban`, `kick`, `timeout`, `untimeout`, `create_role`, `delete_role`, `create_category`, `create_channel`, `delete_channel`, `slowmode`, and `clear`.
- `let greeting = "Hello"` / compact `v(greeting, "Hello")` to define a text variable.
- `send(greeting)` / compact `m(greeting)` to use a defined variable.
- `send(f"Salut @Moderateurs")` allows an explicit role mention by exact role name or ID. F-strings only support literal text and defined variables such as `{greeting}`; they do not execute Python expressions. User and `@everyone` mentions remain blocked.
- `repeat 3: send("Hello")` / compact `R(3, m("Hello"))` for bounded repetition.
- `if greeting == "Hello": send("yes")` with an optional following `else: send("no")` line; compact `I(greeting, "Hello", m("yes"))` supports an optional following `E(m("no"))` line for the else branch.
- Owner-ID and SQLite-backed whitelist access checks.
- Owner-only whitelist management: `!exe admin add @user`, `!exe admin remove @user`, and `!exe admin list`.
- SQLite tables for custom scripts, event handlers, and whitelist entries.
- Limits on script size, action count, message size, repeat count/depth, and execution time.
- Create and save named scripts directly in Discord after syntax validation.
- List, run, and delete a user's own saved scripts; saved scripts are revalidated and use the same execution limits as direct scripts.
- Script-generated messages cannot ping users or roles.
- Automated parser and storage tests, plus a GitHub Actions test workflow.

Still to build: richer values and expressions, event-handler commands and execution, and `sudo` verification.

## Syntax examples

Standard:

```text
let greeting = "Hello"
send(greeting)
repeat 3: send(greeting)
if greeting == "Hello": send("Matched")
else: send("Not matched")
```

The `else` must be on the next line immediately after its `if`. Standard `repeat`, `if`, and `else` blocks also support indentation and multiple instructions:

```text
let mode = "safe"
repeat 2:
    send("Starting")
    send("Still running")
if mode == "admin":
    send("Admin mode")
    send("Second admin message")
else:
    send("Safe mode")
```

Nested blocks are supported, and indentation must be consistent. Blocks cannot be empty.

Compact:

```text
v(greeting, "Hello")
m(greeting)
R(3, m(greeting))
I(greeting, "Hello", m("Matched"))
E(m("Not matched"))

Compact one-liner: `v(greeting, "Hello")§m(greeting)§R(3, m(greeting))`

Compact loops and conditions can now contain multiple instructions separated by `§`:

```text
R(2, m("Starting")§create_role("Tester", "#5865F2", "view_channel, send_messages"))
v(mode, "safe")
I(mode, "safe", m("Allowed")§create_category("Safe-zone"))
```

Separators inside a quoted string remain literal text. The loop count and total action budget are still enforced, including for nested loops.
```

For multiple instructions in Discord, send a fenced code block after `!exe`. Semicolons or `§` can also separate top-level instructions on a single line; `§` is the compact syntax separator and behaves like a newline outside quoted text. Inside compact `R(...)` and `I(...)` calls, use `§` to separate the nested instructions.

### Discord action examples

```text
ban("123456789012345678", "Spam")
unban("123456789012345678")
kick("123456789012345678", "Spam")
timeout("123456789012345678", 10)
untimeout("123456789012345678")
create_role("Helpers")
create_role("Moderators", "#5865F2", "view_channel, send_messages, manage_messages, kick_members")
delete_role("123456789012345678")
create_channel("welcome")
create_channel("staff", "Staff")
create_channel("private", "Staff", "@everyone:view_channel=deny, Moderators:view_channel=allow, Moderators:send_messages=allow")
delete_channel("123456789012345678")
slowmode(5)
clear(25)
```

For `create_category`, the category name is required; an optional second argument defines category permission overwrites using comma-separated `target:permission=allow|deny` entries. The category is created directly by the bot, and channels placed inside it inherit its permissions when no custom channel overwrites are supplied. For `create_channel`, the channel name is required. The optional second argument is an existing category name or ID. The optional third argument defines permission overwrites as comma-separated `target:permission=allow|deny` entries. Use `@everyone` or an existing role name/ID as the target, and supported channel permissions such as `view_channel`, `send_messages`, `read_message_history`, `manage_messages`, `connect`, or `speak`. Example: `create_channel("private", "Staff", "@everyone:view_channel=deny, Moderators:view_channel=allow")`. If a category is provided without custom overwrites, the new channel inherits that category's permissions.

For `create_role`, the name is required; color and permissions are optional. Use a six-digit hex color (for example `"#5865F2"`) and a comma-separated permission string (for example `"view_channel, send_messages, manage_messages"`). Supported permissions are `view_channel`, `send_messages`, `read_message_history`, `embed_links`, `attach_files`, `add_reactions`, `use_external_emojis`, `connect`, `speak`, `stream`, `use_voice_activation`, `manage_messages`, `manage_nicknames`, `kick_members`, `ban_members`, `moderate_members`, and `view_audit_log`. High-risk permissions, including `administrator`, are intentionally not supported.

These actions require the matching native Discord permission from both the user running the script and the bot. Role hierarchy is checked for member moderation and role deletion. IDs or exact role/channel names are accepted for deletion; user targets should be Discord IDs. `timeout` duration is 1–40320 minutes, `slowmode` is 0–21600 seconds, and `clear` is limited to 1–100 recent messages. These functions only work in a server. Use them carefully: role/channel deletion and message clearing are destructive.

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
2. On Windows, run `start_bot.bat`; on Linux/macOS, run `chmod +x start_bot.sh && ./start_bot.sh`.
3. The launcher creates `venv`, installs dependencies, and copies `.env.example` to `.env` if needed.
4. In the panel, use `set_token` and `set_owner` to configure the bot. The token is entered with hidden input.
5. In the Discord Developer Portal, enable **Message Content Intent** for the bot.
6. Use `start`, `stop`, `restart`, `status`, or `uptime` in the panel. Logs are available with `logs`.

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
