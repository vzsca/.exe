# .exe — Discord scripting bot

.exe is a Python Discord bot with a small, allowlisted scripting language for sending messages and performing server-management actions. **It is not Python**: scripts cannot execute arbitrary Python code.

## 🌐 Official Discord servers

- [0x00.exe | Official Server](https://discord.gg/XCWKSnFMcU) — community, support, and development for `.exe`.
- [Noscape | Official Group](https://discord.gg/7VvdbZn224) — the collective behind `.exe` and its other projects.

## Features

- Typed variables, safe expressions, dictionaries, bounded loops, and if/else blocks.
- Message sending, including supported role mentions in f-strings.
- Moderation and channel/role management guarded by Discord permissions and role hierarchy.
- Per-user saved scripts and an owner-managed execution whitelist.
- SQLite persistence and configurable script time/action limits.
- Windows and Linux startup scripts, plus an optional cross-platform terminal control panel.

## Example

    var greeting.str = "Hello";
    var count.int = 3;
    var config.dict = {"mode": "safe", "retries": 2};
    var mode.str = config["mode"];

    if (count == 3) {
        @send(mode);
    } else {
        @send("Not enough");
    }

    repeat(2) {
        @send("Done");
    }

Every instruction must end with a semicolon. Block braces do not need a trailing semicolon. See [docu.md](docu.md) for the complete reference to supported syntax and native actions.

## Requirements

- Python 3.12 or newer
- A Discord bot application and token
- A bot invitation with only the permissions it needs

Enable **Message Content Intent** in the Discord Developer Portal. **Server Members Intent** is disabled by default; set `ENABLE_MEMBERS_INTENT=true` in `.env` and enable the privileged intent in the Developer Portal only if you need `@guilds_members()`. The bot also needs the relevant Discord permissions for any moderation or management actions you run.

## Installation

Clone the repository and create a virtual environment:

    git clone https://github.com/vzsca/.exe.git
    cd .exe
    python -m venv venv

Activate it:

    # Linux / macOS
    source venv/bin/activate

    # Windows PowerShell
    venv\Scripts\Activate.ps1

Install the project and development dependencies:

    python -m pip install --upgrade pip
    python -m pip install -e .
    python -m pip install -r requirements-dev.txt

Copy .env.example to .env and configure these values:

- DISCORD_TOKEN: your bot token from the Discord Developer Portal.
- OWNER_ID: your numeric Discord user ID.
- DATABASE_PATH (optional): SQLite database path; defaults to data/exe.sqlite3.
- SCRIPT_TIMEOUT_SECONDS (optional): script/input timeout, greater than 0 and at most 300 seconds.
- MAX_SCRIPT_ACTIONS (optional): action budget, from 1 to 1000.

Never commit .env or share your bot token.

## Run the bot

From the repository root, with the virtual environment activated:

    python -m exe_bot

On Windows, start_bot.bat can set up and start the bot. On Linux, use ./start_bot.sh (make it executable first if necessary). The optional control panel can be started with:

    python panel.py

## Discord commands

All commands use the ! prefix.

| Command | Purpose |
|---|---|
| !exe &lt;script&gt; | Validate and run a script immediately. |
| !exe create &lt;name&gt; :: &lt;script&gt; | Validate and save a named script without running it. |
| !exe list | List your saved scripts. |
| !exe run &lt;name&gt; | Run one of your saved scripts. |
| !exe delete &lt;name&gt; | Delete one of your saved scripts. |
| !exe admin add @user | Add a user to the execution whitelist (owner only). |
| !exe admin remove @user | Remove a user from the execution whitelist (owner only). |
| !exe admin list | List whitelisted user IDs (owner only). |
| !help_exe | Show the built-in language help. |

The configured owner can always run scripts. Other users must be on the whitelist. Saved scripts are scoped to the Discord user who created them.

## Tests

    python -m pytest -q

GitHub Actions runs tests on pushes and pull requests. The tests use mocked Discord objects and do not replace testing the bot in a private test server before granting it permissions.

## Documentation and policies

- [Language reference](docu.md)
- [Repository audit and code/documentation comparison](AUDIT.md)
- [Privacy policy template](PRIVACY_POLICY.md)
- [Terms of use template](TERMS_OF_USE.md)
- [MIT license](LICENSE)

The privacy policy and terms are templates. Operators must review and adapt them to their deployment and applicable law.

## Security notes

The parser evaluates expressions through an explicit AST allowlist and rejects arbitrary Python calls and attribute access. Discord actions can still make real changes: review scripts before running them, grant the bot minimum required permissions, and test destructive actions in a private server first. Report security issues privately to the repository owner rather than publishing exploit details in an issue.
