"""Discord integration for the .exe scripting engine."""

import asyncio
import logging
import re

import discord
from discord.ext import commands

from .config import Settings
from .language import ScriptError, SendMessage, expand_actions, parse_script
from .permissions import is_owner, may_run_scripts
from .storage import Database, StorageError

log = logging.getLogger(__name__)
_USER_ID = re.compile(r"^(?:<@!?(\d+)>|(\d+))$")


class ExeBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.settings = settings
        self.db = Database(settings.database_path)

    async def setup_hook(self) -> None:
        log.info(".exe scripting bot is starting")


def build_bot(settings: Settings) -> ExeBot:
    bot = ExeBot(settings)

    @bot.event
    async def on_ready() -> None:
        log.info("Connected as %s (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")

    @bot.command(name="exe")
    async def exe_command(ctx: commands.Context, *, script: str = "") -> None:
        """Run a script or use owner-only admin subcommands."""
        cleaned = script.strip()

        # Owner-only access management is handled before the script whitelist check.
        if cleaned.lower().startswith("admin"):
            if not is_owner(ctx.author.id, settings):
                await ctx.reply(
                    "Access denied: only the configured owner can manage the whitelist.",
                    mention_author=False,
                )
                return

            if cleaned.lower() == "admin list":
                ids = bot.db.list_whitelist()
                if not ids:
                    response = "Whitelist is empty."
                else:
                    visible = ids[:50]
                    response = "Whitelisted user IDs: " + ", ".join(map(str, visible))
                    if len(ids) > len(visible):
                        response += f" (and {len(ids) - len(visible)} more)"
                await ctx.reply(response, mention_author=False)
                return

            match = re.fullmatch(r"admin\s+(add|remove)\s+(\S+)", cleaned, flags=re.IGNORECASE)
            if match:
                operation, raw_user_id = match.groups()
                id_match = _USER_ID.fullmatch(raw_user_id)
                if id_match is None:
                    await ctx.reply(
                        "Usage: !exe admin add @user or !exe admin remove @user.",
                        mention_author=False,
                    )
                    return
                target_id = int(id_match.group(1) or id_match.group(2))
                try:
                    if operation.lower() == "add":
                        changed = bot.db.add_whitelist(target_id, ctx.author.id)
                        response = (
                            f"User ID {target_id} added to the whitelist."
                            if changed
                            else f"User ID {target_id} is already whitelisted."
                        )
                    else:
                        changed = bot.db.remove_whitelist(target_id)
                        response = (
                            f"User ID {target_id} removed from the whitelist."
                            if changed
                            else f"User ID {target_id} was not in the whitelist."
                        )
                except StorageError as exc:
                    response = str(exc)
                await ctx.reply(response, mention_author=False)
                return

            await ctx.reply(
                "Owner commands: !exe admin add @user, !exe admin remove @user, !exe admin list.",
                mention_author=False,
            )
            return

        if not may_run_scripts(ctx.author.id, settings, bot.db.list_whitelist()):
            await ctx.reply(
                "Access denied: you are not allowed to run .exe scripts.",
                mention_author=False,
            )
            return

        if cleaned.startswith(chr(96) * 3) and cleaned.endswith(chr(96) * 3):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1])

        try:
            instructions = parse_script(cleaned, max_actions=settings.max_script_actions)
            actions = expand_actions(instructions)
        except ScriptError as exc:
            await ctx.reply(f"Syntax error: {exc}", mention_author=False)
            return

        async def execute_actions() -> None:
            for action in actions:
                if isinstance(action, SendMessage):
                    # Script-generated messages never ping users or roles.
                    await ctx.channel.send(
                        action.text,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )

        try:
            await asyncio.wait_for(execute_actions(), timeout=settings.script_timeout_seconds)
            await ctx.message.add_reaction("✅")
        except TimeoutError:
            await ctx.reply("Script stopped: execution time limit reached.", mention_author=False)
        except discord.Forbidden:
            await ctx.reply("I do not have permission to perform that action here.", mention_author=False)
        except discord.HTTPException:
            await ctx.reply("Discord rejected an action in this script.", mention_author=False)

    @bot.command(name="help_exe")
    async def help_exe(ctx: commands.Context) -> None:
        await ctx.reply(
            'Standard: !exe let greeting = "Hello"; send(greeting)\n'
            'Compact: !exe v(greeting, "Hello"); m(greeting)\n'
            'Repeat: repeat 3: send(greeting) or R(3, m(greeting))\n'
            "Owner whitelist: !exe admin add @user, remove @user, list.",
            mention_author=False,
        )

    return bot


async def run_bot(settings: Settings) -> None:
    bot = build_bot(settings)
    try:
        await bot.start(settings.token)
    finally:
        await bot.close()
