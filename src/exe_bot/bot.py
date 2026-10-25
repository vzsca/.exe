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
_CREATE_RE = re.compile(r"^create\s+([A-Za-z][A-Za-z0-9_-]{0,31})\s*::\s*(.+)$", re.IGNORECASE | re.DOTALL)
_NAME_COMMAND_RE = re.compile(r"^(run|delete)\s+([A-Za-z][A-Za-z0-9_-]{0,31})$", re.IGNORECASE)


def _strip_fence(source: str) -> str:
    cleaned = source.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return cleaned


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

    async def run_source(ctx: commands.Context, source: str) -> bool:
        try:
            instructions = parse_script(source, max_actions=settings.max_script_actions)
            actions = expand_actions(instructions)
        except ScriptError as exc:
            await ctx.reply(f"Syntax error: {exc}", mention_author=False)
            return False

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
            return True
        except TimeoutError:
            await ctx.reply("Script stopped: execution time limit reached.", mention_author=False)
        except discord.Forbidden:
            await ctx.reply("I do not have permission to perform that action here.", mention_author=False)
        except discord.HTTPException:
            await ctx.reply("Discord rejected an action in this script.", mention_author=False)
        return False

    @bot.command(name="exe")
    async def exe_command(ctx: commands.Context, *, script: str = "") -> None:
        """Run a script or use script-storage / owner-only admin commands."""
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
                "Access denied: you are not allowed to use .exe scripts.",
                mention_author=False,
            )
            return

        # Creation stores a validated script; it does not execute it.
        create_match = _CREATE_RE.fullmatch(cleaned)
        if create_match:
            name, source = create_match.groups()
            source = _strip_fence(source)
            try:
                parse_script(source, max_actions=settings.max_script_actions)
                bot.db.save_script(ctx.author.id, name, source)
            except (ScriptError, StorageError) as exc:
                await ctx.reply(f"Could not create script: {exc}", mention_author=False)
                return
            await ctx.reply(
                f"Script `{name}` created and saved. Use `!exe run {name}` to execute it.",
                mention_author=False,
            )
            return

        # List saved scripts owned by the caller.
        if cleaned.lower() == "list":
            names = bot.db.list_scripts(ctx.author.id)
            if not names:
                response = 'You have no saved scripts. Create one with !exe create hello :: send("Hello").'
            else:
                visible = names[:50]
                response = "Your saved scripts: " + ", ".join(f"`{name}`" for name in visible)
                if len(names) > len(visible):
                    response += f" (and {len(names) - len(visible)} more)"
            await ctx.reply(response, mention_author=False)
            return

        # Saved scripts are scoped to the caller's Discord ID.
        name_match = _NAME_COMMAND_RE.fullmatch(cleaned)
        if name_match:
            operation, name = name_match.groups()
            operation = operation.lower()
            try:
                if operation == "run":
                    source = bot.db.get_script(ctx.author.id, name)
                    if source is None:
                        await ctx.reply(
                            f"No saved script named `{name}` belongs to your account.",
                            mention_author=False,
                        )
                        return
                    await run_source(ctx, source)
                else:
                    deleted = bot.db.delete_script(ctx.author.id, name)
                    response = (
                        f"Script `{name}` deleted." if deleted
                        else f"No saved script named `{name}` belongs to your account."
                    )
                    await ctx.reply(response, mention_author=False)
            except StorageError as exc:
                await ctx.reply(str(exc), mention_author=False)
            return

        # A plain !exe message runs the source directly.
        await run_source(ctx, _strip_fence(cleaned))

    @bot.command(name="help_exe")
    async def help_exe(ctx: commands.Context) -> None:
        await ctx.reply(
            'Run: !exe send("Hello")\n'
            'Create and save: !exe create greeting :: send("Hello")\n'
            'List scripts: !exe list\n'
            'Run / delete saved: !exe run greeting / !exe delete greeting\n'
            'Standard: let greeting = "Hello"; send(greeting)\n'
            'Compact: v(greeting, "Hello"); m(greeting)\n'
            'Condition: if greeting == "Hello": send("yes") or I(greeting, "Hello", m("yes"))\n'
            'Repeat: repeat 3: send(greeting) or R(3, m(greeting))\n'
            'Owner whitelist: !exe admin add @user, !exe admin remove @user, !exe admin list.',
            mention_author=False,
        )

    return bot


async def run_bot(settings: Settings) -> None:
    bot = build_bot(settings)
    try:
        await bot.start(settings.token)
    finally:
        await bot.close()
