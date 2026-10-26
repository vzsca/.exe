from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from exe_bot.bot import build_bot
from exe_bot.config import Settings


class FakeRole:
    def __init__(self, role_id, name, position, *, default=False):
        self.id = role_id
        self.name = name
        self.position = position
        self._default = default
        self.mention = f"<@&{role_id}>"

    def __ge__(self, other):
        return self.position >= other.position

    def is_default(self):
        return self._default


class FakeMember:
    def __init__(self, member_id, top_role, *, manage_roles=True, administrator=False):
        self.id = member_id
        self.top_role = top_role
        self.guild_permissions = SimpleNamespace(
            manage_roles=manage_roles, administrator=administrator
        )
        self.add_roles = AsyncMock()
        self.remove_roles = AsyncMock()
        self.bot = False

    def __str__(self):
        return str(self.id)


def make_context(database_path, *, actor_position=10, bot_position=20, target_role_position=5):
    actor_role = FakeRole(10, "Moderator", actor_position)
    bot_role = FakeRole(20, "Bot", bot_position)
    target_role = FakeRole(30, "Helpers", target_role_position)
    actor = FakeMember(123, actor_role)
    bot_member = FakeMember(999, bot_role)
    target = FakeMember(456, FakeRole(40, "Member", 1))
    roles = [actor_role, bot_role, target_role]
    guild = SimpleNamespace(
        id=1,
        owner_id=777,
        me=bot_member,
        roles=roles,
        get_role=lambda role_id: next((role for role in roles if role.id == role_id), None),
        get_member=lambda member_id: target if member_id == target.id else None,
        fetch_member=AsyncMock(return_value=target),
    )
    ctx = SimpleNamespace(
        author=actor,
        guild=guild,
        channel=SimpleNamespace(id=300),
        message=SimpleNamespace(add_reaction=AsyncMock()),
        reply=AsyncMock(),
    )
    settings = Settings(token="test", owner_id=actor.id, database_path=str(database_path))
    return ctx, target, build_bot(settings)


class DiscordActionTests(IsolatedAsyncioTestCase):
    async def test_role_hierarchy_rejects_role_at_or_above_bot(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(
                Path(directory) / "db.sqlite3", bot_position=5, target_role_position=5
            )
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
                    self.assertIn("bot's highest role must be above", ctx.reply.await_args.args[0])
                    target.add_roles.assert_not_awaited()
                finally:
                    await bot.close()

    async def test_role_hierarchy_rejects_role_at_or_above_actor(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(
                Path(directory) / "db.sqlite3", actor_position=5, bot_position=20, target_role_position=5
            )
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
                    self.assertIn("Your highest role must be above", ctx.reply.await_args.args[0])
                    target.add_roles.assert_not_awaited()
                finally:
                    await bot.close()

    async def test_discord_forbidden_is_reported_without_leaking_exception(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(Path(directory) / "db.sqlite3")
            target.add_roles.side_effect = discord.Forbidden(MagicMock(status=403), "missing permission")
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
                    self.assertIn("Discord refused 'give_role'", ctx.reply.await_args.args[0])
                finally:
                    await bot.close()

    async def test_discord_http_error_is_reported_to_script_author(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(Path(directory) / "db.sqlite3")
            target.add_roles.side_effect = discord.HTTPException(
                MagicMock(status=500), "temporary API failure"
            )
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
                    self.assertIn("Discord rejected an action", ctx.reply.await_args.args[0])
                finally:
                    await bot.close()


    async def test_create_role_result_can_be_reused_for_role_assignment(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(Path(directory) / "db.sqlite3")
            created_role = FakeRole(31, "Helpers", 4)
            async def create_role(**kwargs):
                ctx.guild.roles.append(created_role)
                return created_role
            ctx.guild.create_role = AsyncMock(side_effect=create_role)
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(
                        ctx,
                        script=(
                            'var helper_role.role.id = None; '
                            'set helper_role = @create_role("Helpers"); '
                            '@add_role("456", helper_role);'
                        ),
                    )
                    ctx.guild.create_role.assert_awaited_once()
                    target.add_roles.assert_awaited_once_with(
                        created_role, reason=f".exe by {ctx.author.id}"
                    )
                finally:
                    await bot.close()

    async def test_role_assignment_requires_manage_roles_permission(self):
        with TemporaryDirectory() as directory:
            ctx, target, bot = make_context(Path(directory) / "db.sqlite3")
            ctx.author.guild_permissions.manage_roles = False
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(
                        ctx, script='@add_role("456", "Helpers");'
                    )
                    self.assertIn("Manage Roles", ctx.reply.await_args.args[0])
                    target.add_roles.assert_not_awaited()
                finally:
                    await bot.close()

    async def test_create_role_rejects_administrator_permission(self):
        with TemporaryDirectory() as directory:
            ctx, _, bot = make_context(Path(directory) / "db.sqlite3")
            ctx.guild.create_role = AsyncMock()
            with patch("exe_bot.bot.discord.Member", FakeMember):
                try:
                    await bot.get_command("exe").callback(
                        ctx,
                        script='@create_role("Helpers", "#5865F2", "administrator");'
                    )
                    self.assertIn("administrator", ctx.reply.await_args.args[0])
                    ctx.guild.create_role.assert_not_awaited()
                finally:
                    await bot.close()


    async def test_delete_channel_rejects_category_id(self):
        with TemporaryDirectory() as directory:
            ctx, _, bot = make_context(Path(directory) / "db.sqlite3")
            category = SimpleNamespace(id=987, name="Important", delete=AsyncMock())
            ctx.guild.get_channel = lambda channel_id: category if channel_id == 987 else None
            # Reach the channel-type validation instead of failing the earlier
            # actor/bot permission checks in this mocked context.
            ctx.author.guild_permissions.manage_channels = True
            ctx.guild.me.guild_permissions.manage_channels = True

            class FakeTextChannel:
                pass

            with patch("exe_bot.bot.discord.Member", FakeMember), patch(
                "exe_bot.bot.discord.TextChannel", FakeTextChannel
            ):
                try:
                    await bot.get_command("exe").callback(
                        ctx, script='@delete_channel("987");'
                    )
                    self.assertIn("Only text channels", ctx.reply.await_args.args[0])
                    category.delete.assert_not_awaited()
                finally:
                    await bot.close()
