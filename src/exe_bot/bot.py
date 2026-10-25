"""Discord integration for the .exe scripting engine."""

import asyncio
import logging

import discord
from discord.ext import commands

from .config import Settings
from .language import ScriptError, SendMessage, expand_actions, parse_script
from .permissions import may_run_scripts

log = logging.getLogger(__name__)


class ExeBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.settings = settings

    async def setup_hook(self) -> None:
        log.info(".exe scripting bot is starting")


def build_bot(settings: Settings) -> ExeBot:
    bot = ExeBot(settings)

    @bot.event
    async def on_ready() -> None:
        log.info("Connected as %s (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")

    @bot.command(name="exe")
    async def exe_command(ctx: commands.Context, *, script: str = "") -> None:
        """Run a short .exe script. Use a code block for multiple lines."""
        if not may_run_scripts(ctx.author.id, settings):
            await ctx.reply("Access denied: you are not allowed to run `.exe` scripts.", mention_author=False)
            return

        cleaned = script.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1])

        try:
            instructions = parse_script(cleaned, max_actions=settings.max_script_actions)
            actions = expand_actions(instructions)
        except ScriptError as exc:
            await ctx.reply(f"`Syntax error:` {exc}", mention_author=False)
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
            'Standard: `!exe let greeting = "Hello"; send(greeting)`\n'
            'Compact: `!exe v(greeting, "Hello"); m(greeting)`\n'
            'Repeat: `repeat 3: send(greeting)` or `R(3, m(greeting))`\n'
            "Both forms use the same safe instruction engine.",
            mention_author=False,
        )

    return bot


async def run_bot(settings: Settings) -> None:
    bot = build_bot(settings)
    try:
        await bot.start(settings.token)
    finally:
        await bot.close()
