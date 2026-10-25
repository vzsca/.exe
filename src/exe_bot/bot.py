"""Discord integration for the .exe scripting engine."""

import asyncio
import logging
from datetime import timedelta
import re
import time

import discord
from discord.ext import commands

from .config import Settings
from .language import DiscordAction, InputVariable, ScriptError, SendMessage, expand_actions, parse_script
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

    async def execute_discord_action(ctx: commands.Context, action: DiscordAction) -> str | None:
        """Run one explicitly supported Discord action after checking native permissions."""
        if ctx.guild is None:
            raise ScriptError("Discord administration functions only work inside a server.")
        guild = ctx.guild
        actor = ctx.author
        if not isinstance(actor, discord.Member):
            raise ScriptError("Could not verify your server permissions.")
        bot_member = guild.me
        if bot_member is None:
            raise ScriptError("Could not verify the bot's server permissions.")

        name, args = action.name, action.arguments
        permission_by_action = {
            "ban": "ban_members", "unban": "ban_members",
            "kick": "kick_members", "timeout": "moderate_members",
            "untimeout": "moderate_members", "create_role": "manage_roles",
            "delete_role": "manage_roles", "create_category": "manage_channels", "create_channel": "manage_channels",
            "delete_channel": "manage_channels", "slowmode": "manage_channels",
            "clear": "manage_messages",
        }
        required = permission_by_action[name]
        # Discord administrators implicitly have every guild permission. Check the
        # administrator flag explicitly as a safeguard against permission-flag quirks.
        actor_permissions = actor.guild_permissions
        bot_permissions = bot_member.guild_permissions
        if not (actor_permissions.administrator or getattr(actor_permissions, required, False)):
            raise ScriptError(f"You need the Discord '{required.replace('_', ' ').title()}' permission.")
        if not (bot_permissions.administrator or getattr(bot_permissions, required, False)):
            raise ScriptError(f"The bot needs the Discord '{required.replace('_', ' ').title()}' permission.")

        def target_id(raw: str | int) -> int:
            match = _USER_ID.fullmatch(str(raw))
            if match is None:
                raise ScriptError("Use a Discord ID or member mention for this target.")
            return int(match.group(1) or match.group(2))

        reason = str(args[1]) if len(args) > 1 else f".exe script by {actor} ({actor.id})"
        if name in {"ban", "unban", "kick", "timeout", "untimeout"}:
            user_id = target_id(args[0])
            member = guild.get_member(user_id)
            if member is None and name != "unban":
                # Members intent/cache may be unavailable, even when the user is
                # visibly in the server. Fetch the member directly before refusing.
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    member = None
                except discord.Forbidden as exc:
                    raise ScriptError("Could not look up that member; check the bot's server access.") from exc
            if name == "unban":
                try:
                    user = await bot.fetch_user(user_id)
                    await guild.unban(user, reason=reason)
                except discord.NotFound as exc:
                    raise ScriptError("That user is not banned or could not be found.") from exc
                return
            if member is None:
                if name == "ban":
                    try:
                        user = await bot.fetch_user(user_id)
                    except discord.NotFound as exc:
                        raise ScriptError("Could not find that Discord user.") from exc
                    await guild.ban(user, reason=reason, delete_message_seconds=0)
                    return
                raise ScriptError("That member is not currently in this server.")
            if member.id == actor.id or member.id == bot_member.id:
                raise ScriptError("You cannot target yourself or the bot.")
            if guild.owner_id != actor.id and member.top_role >= actor.top_role:
                raise ScriptError("Discord role hierarchy prevents you from targeting that member.")
            if member.top_role >= bot_member.top_role:
                raise ScriptError("The bot's role must be higher than the target member's role.")
            if name == "ban":
                await guild.ban(member, reason=reason, delete_message_seconds=0)
            elif name == "kick":
                await member.kick(reason=reason)
            elif name == "timeout":
                minutes = args[1]
                if not isinstance(minutes, int) or not 1 <= minutes <= 40320:
                    raise ScriptError("timeout duration must be an integer from 1 to 40320 minutes.")
                await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=f".exe by {actor.id}")
            else:
                await member.timeout(None, reason=f".exe by {actor.id}")
            return

        if name == "create_role":
            role_name = str(args[0]).strip()
            if not role_name or len(role_name) > 100:
                raise ScriptError("Role name must contain 1 to 100 characters.")

            role_color = discord.Color.default()
            if len(args) >= 2:
                raw_color = str(args[1]).strip()
                if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", raw_color):
                    raise ScriptError('Role color must be a hex color like "#5865F2".')
                role_color = discord.Color(int(raw_color.removeprefix("#"), 16))

            # Keep role permissions explicit and limited; do not allow administrator.
            allowed_role_permissions = {
                "view_channel", "send_messages", "read_message_history",
                "embed_links", "attach_files", "add_reactions", "use_external_emojis",
                "connect", "speak", "stream", "use_voice_activation",
                "manage_messages", "manage_nicknames", "kick_members", "ban_members",
                "moderate_members", "view_audit_log",
            }
            role_permissions = discord.Permissions.none()
            if len(args) >= 3:
                raw_permissions = str(args[2]).strip()
                if raw_permissions:
                    requested = [permission.strip().lower() for permission in raw_permissions.split(",")]
                    if any(not permission for permission in requested):
                        raise ScriptError("Separate role permissions with commas, without empty entries.")
                    unsupported = sorted(set(requested) - allowed_role_permissions)
                    if unsupported:
                        raise ScriptError(
                            "Unsupported role permission(s): " + ", ".join(unsupported)
                            + ". 'administrator' and other high-risk permissions are not allowed."
                        )
                    for permission in set(requested):
                        setattr(role_permissions, permission, True)

            created_role = await guild.create_role(
                name=role_name,
                colour=role_color,
                permissions=role_permissions,
                reason=f".exe by {actor.id}",
            )
            # Return the immutable ID so duplicate role names cannot resolve to an older role.
            return f"@{created_role.id}"
        elif name == "delete_role":
            raw = str(args[0])
            role = guild.get_role(int(raw)) if raw.isdigit() else discord.utils.get(guild.roles, name=raw)
            if role is None:
                raise ScriptError("Could not find that role by ID or exact name.")
            if role.is_default() or role >= bot_member.top_role or (guild.owner_id != actor.id and role >= actor.top_role):
                raise ScriptError("Discord role hierarchy prevents deleting that role.")
            await role.delete(reason=f".exe by {actor.id}")
        elif name == "create_category":
            category_name = str(args[0]).strip()
            if not category_name or len(category_name) > 100:
                raise ScriptError("Category name must contain 1 to 100 characters.")

            overwrites = {}
            if len(args) >= 2 and str(args[1]).strip():
                allowed_channel_permissions = {
                    "view_channel", "send_messages", "read_message_history",
                    "embed_links", "attach_files", "add_reactions", "use_external_emojis",
                    "manage_messages", "manage_channels", "connect", "speak", "stream",
                    "use_voice_activation", "send_messages_in_threads",
                    "create_public_threads", "create_private_threads", "send_polls",
                }
                # Format: "@everyone:view_channel=deny, Moderators:view_channel=allow"
                for entry in str(args[1]).split(","):
                    entry = entry.strip()
                    match = re.fullmatch(r"(.+?):([a-z_]+)=(allow|deny)", entry, re.IGNORECASE)
                    if not match:
                        raise ScriptError(
                            'Category permissions use "role:permission=allow|deny", '
                            'for example "@everyone:view_channel=deny".'
                        )
                    target_name, permission, decision = match.groups()
                    target_name = target_name.strip()
                    permission = permission.lower()
                    decision = decision.lower()
                    if permission not in allowed_channel_permissions:
                        raise ScriptError(f"Unsupported category permission: {permission}.")
                    if target_name == "@everyone":
                        target = guild.default_role
                    elif target_name.isdigit():
                        target = guild.get_role(int(target_name))
                    else:
                        target = discord.utils.get(guild.roles, name=target_name)
                    if target is None:
                        raise ScriptError(f"Could not find category permission target role: {target_name}.")
                    overwrite = overwrites.setdefault(target, discord.PermissionOverwrite())
                    setattr(overwrite, permission, decision == "allow")

            await guild.create_category(
                category_name,
                overwrites=overwrites,
                reason=f".exe by {actor.id}",
            )
        elif name == "create_channel":
            channel_name = str(args[0]).strip()
            if not channel_name or len(channel_name) > 100:
                raise ScriptError("Channel name must contain 1 to 100 characters.")

            category = None
            if len(args) >= 2 and str(args[1]).strip():
                raw_category = str(args[1]).strip()
                category = guild.get_channel(int(raw_category)) if raw_category.isdigit() else discord.utils.get(
                    guild.categories, name=raw_category
                )
                if not isinstance(category, discord.CategoryChannel):
                    raise ScriptError("Category must be an existing category ID or exact name.")

            overwrites = {}
            if len(args) >= 3 and str(args[2]).strip():
                allowed_channel_permissions = {
                    "view_channel", "send_messages", "read_message_history",
                    "embed_links", "attach_files", "add_reactions", "use_external_emojis",
                    "manage_messages", "manage_channels",
                    "connect", "speak", "stream", "use_voice_activation",
                    "send_messages_in_threads", "create_public_threads",
                    "create_private_threads", "send_polls",
                }
                # Format: "@everyone:view_channel=deny, Moderators:send_messages=allow"
                # Entries target @everyone or an existing role by exact name / ID.
                for entry in str(args[2]).split(","):
                    entry = entry.strip()
                    match = re.fullmatch(r"(.+?):([a-z_]+)=(allow|deny)", entry, re.IGNORECASE)
                    if not match:
                        raise ScriptError(
                            'Channel permissions use "role:permission=allow|deny", '
                            'for example "@everyone:view_channel=deny".'
                        )
                    target_name, permission, decision = match.groups()
                    target_name = target_name.strip()
                    permission = permission.lower()
                    decision = decision.lower()
                    if permission not in allowed_channel_permissions:
                        raise ScriptError(f"Unsupported channel permission: {permission}.")
                    if target_name == "@everyone":
                        target = guild.default_role
                    elif target_name.isdigit():
                        target = guild.get_role(int(target_name))
                    else:
                        target = discord.utils.get(guild.roles, name=target_name)
                    if target is None:
                        raise ScriptError(f"Could not find channel permission target role: {target_name}.")
                    overwrite = overwrites.setdefault(target, discord.PermissionOverwrite())
                    setattr(overwrite, permission, decision == "allow")

            # discord.py does not accept sync_permissions on create_text_channel.
            # Copy the category overwrites when none were explicitly supplied so the
            # new channel inherits the category access rules.
            if category is not None and not overwrites:
                overwrites = category.overwrites

            await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites or None,
                reason=f".exe by {actor.id}",
            )
        elif name == "delete_channel":
            raw = str(args[0])
            channel = guild.get_channel(int(raw)) if raw.isdigit() else discord.utils.get(guild.text_channels, name=raw)
            if channel is None:
                raise ScriptError("Could not find that channel by ID or exact name.")
            await channel.delete(reason=f".exe by {actor.id}")
        elif name == "slowmode":
            seconds = args[0]
            if not isinstance(seconds, int) or not 0 <= seconds <= 21600:
                raise ScriptError("slowmode must be an integer from 0 to 21600 seconds.")
            if not isinstance(ctx.channel, discord.TextChannel):
                raise ScriptError("slowmode only works in a text channel.")
            await ctx.channel.edit(slowmode_delay=seconds, reason=f".exe by {actor.id}")
        elif name == "clear":
            count = args[0]
            if not isinstance(count, int) or not 1 <= count <= 100:
                raise ScriptError("clear accepts an integer from 1 to 100.")
            if not isinstance(ctx.channel, discord.TextChannel):
                raise ScriptError("clear only works in a text channel.")
            await ctx.channel.purge(limit=count, reason=f".exe by {actor.id}")

    async def run_source(ctx: commands.Context, source: str) -> bool:
        try:
            instructions = parse_script(source, max_actions=settings.max_script_actions)
            actions = expand_actions(instructions)
        except ScriptError as exc:
            await ctx.reply(f"Syntax error: {exc}", mention_author=False)
            return False

        current_action = {"index": 0, "name": "not started"}
        runtime_variables: dict[str, str] = {}
        log.info(".exe script parsed: %d actions (channel=%s actor=%s timeout=%ss)",
                 len(actions), ctx.channel.id, ctx.author.id, settings.script_timeout_seconds)

        async def execute_actions() -> None:
            for index, action in enumerate(actions, start=1):
                action_name = "input" if isinstance(action, InputVariable) else ("send" if isinstance(action, SendMessage) else action.name)
                current_action.update(index=index, name=action_name)
                started = time.monotonic()
                log.info(".exe action %d/%d starting: %s (channel=%s actor=%s)",
                         index, len(actions), action_name, ctx.channel.id, ctx.author.id)
                try:
                    if isinstance(action, InputVariable):
                        await ctx.channel.send(action.question)
                        def check(message: discord.Message) -> bool:
                            return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id and not message.author.bot
                        try:
                            answer = await bot.wait_for("message", check=check, timeout=settings.script_timeout_seconds)
                        except asyncio.TimeoutError as exc:
                            raise ScriptError(f"Input '{action.name}' timed out while waiting for your reply.") from exc
                        if len(answer.content) > 1800:
                            raise ScriptError("Input response is too long (maximum 1800 characters).")
                        # User input is plain text and must never trigger role pings.
                        runtime_variables[action.name] = answer.content.replace("@", "@\u200b")
                    elif isinstance(action, SendMessage):
                        target = ctx.channel
                        if action.channel is not None:
                            if ctx.guild is None:
                                raise ScriptError("Target-channel sends only work inside a server.")
                            raw_target = action.channel.removeprefix("#")
                            target = (ctx.guild.get_channel(int(raw_target)) if raw_target.isdigit()
                                      else discord.utils.get(ctx.guild.text_channels, name=raw_target))
                            if not isinstance(target, discord.TextChannel):
                                raise ScriptError("Could not find the target text channel by ID or exact name.")
                        content = action.text
                        for variable_name, variable_value in runtime_variables.items():
                            content = content.replace(f"__EXE_VAR_{variable_name}__", variable_value)
                        allowed_roles = []
                        if action.role_mentions:
                            if ctx.guild is None:
                                raise ScriptError("Role mentions only work inside a server.")
                            # Match exact role names longest-first, including names with spaces.
                            for role in sorted(ctx.guild.roles, key=lambda item: len(item.name), reverse=True):
                                token = f"@{role.name}"
                                # Match the whole role token, never a prefix such as @Mod in @Moderator.
                                pattern = re.compile(r"(?<![\w@])" + re.escape(token) + r"(?!\w)")
                                if pattern.search(content):
                                    content = pattern.sub(lambda _: role.mention, content)
                                    if role not in allowed_roles:
                                        allowed_roles.append(role)
                            # Numeric IDs are accepted as explicit role references.
                            role_id_pattern = re.compile(r"(?<!\w)@([0-9]{15,22})(?!\d)")
                            def replace_role_id(match: re.Match[str]) -> str:
                                role = ctx.guild.get_role(int(match.group(1)))
                                if role is None:
                                    return match.group(0)
                                if role not in allowed_roles:
                                    allowed_roles.append(role)
                                return role.mention
                            content = role_id_pattern.sub(replace_role_id, content)
                        await target.send(
                            content,
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False, users=False, roles=allowed_roles, replied_user=False
                            ),
                        )
                    elif isinstance(action, DiscordAction):
                        try:
                            action_result = await execute_discord_action(ctx, action)
                            if action.result_variable and action_result is not None:
                                runtime_variables[action.result_variable] = action_result
                        except discord.Forbidden as exc:
                            log.warning(
                                "Discord denied .exe action %s in guild %s (channel %s), actor %s, target args %r: %s",
                                action.name, ctx.guild.id if ctx.guild else "DM", ctx.channel.id,
                                ctx.author.id, action.arguments, getattr(exc, "text", str(exc)),
                            )
                            raise ScriptError(
                                f"Discord refused '{action.name}'. Verify the bot's permissions and role hierarchy. "
                                "Check the bot logs for details."
                            ) from exc
                finally:
                    log.info(".exe action %d/%d finished: %s (elapsed=%.2fs, channel=%s actor=%s)",
                             index, len(actions), action_name, time.monotonic() - started,
                             ctx.channel.id, ctx.author.id)

        try:
            await asyncio.wait_for(execute_actions(), timeout=settings.script_timeout_seconds)
            await ctx.message.add_reaction("✅")
            return True
        except TimeoutError:
            log.warning(".exe script timed out after %ss at action %s/%s (channel=%s actor=%s)",
                        settings.script_timeout_seconds, current_action["index"], len(actions),
                        ctx.channel.id, ctx.author.id)
            await ctx.reply("Script stopped: execution time limit reached.", mention_author=False)
        except ScriptError as exc:
            await ctx.reply(f"Action refused: {exc}", mention_author=False)
        except discord.Forbidden as exc:
            log.warning(
                "Discord denied .exe action outside its action handler in guild %s (channel %s), actor %s: %s",
                ctx.guild.id if ctx.guild else "DM",
                ctx.channel.id,
                ctx.author.id,
                getattr(exc, "text", str(exc)),
            )
            await ctx.reply(
                "Discord refused this action. Check the bot's effective permissions and role hierarchy; "
                "details were written to the bot log.",
                mention_author=False,
            )
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
            'Condition: if greeting == "Hello": send("yes"); optional next line: else: send("no")\n'
            'Compact condition: I(greeting, "Hello", m("yes")); compact else on next line: E(m("no"))\n'
            'Repeat: repeat 3: send(greeting) or R(3, m(greeting))\n'
            'Server actions: ban(id, "reason"), unban(id), kick(id, "reason"), timeout(id, minutes), untimeout(id)\n'
            'Roles/channels: create_role("name"), delete_role(id_or_exact_name), create_channel("name"), delete_channel(id_or_exact_name)\n'
            'Moderation: slowmode(seconds), clear(count); requires matching Discord permissions and bot role access.\n'
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
