from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

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


def make_context(tmp_path, *, actor_position=10, bot_position=20, target_role_position=5):
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
    settings = Settings(token="test", owner_id=actor.id, database_path=str(tmp_path / "db.sqlite3"))
    return ctx, target_role, target, build_bot(settings)


@pytest.mark.asyncio
async def test_role_hierarchy_rejects_role_at_or_above_bot(tmp_path):
    ctx, _, target, bot = make_context(tmp_path, bot_position=5, target_role_position=5)
    with patch("exe_bot.bot.discord.Member", FakeMember):
        try:
            await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
            assert "bot's highest role must be above" in ctx.reply.await_args.args[0]
            target.add_roles.assert_not_awaited()
        finally:
            await bot.close()


@pytest.mark.asyncio
async def test_role_hierarchy_rejects_role_at_or_above_actor(tmp_path):
    ctx, _, target, bot = make_context(tmp_path, actor_position=5, bot_position=20, target_role_position=5)
    with patch("exe_bot.bot.discord.Member", FakeMember):
        try:
            await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
            assert "Your highest role must be above" in ctx.reply.await_args.args[0]
            target.add_roles.assert_not_awaited()
        finally:
            await bot.close()


@pytest.mark.asyncio
async def test_discord_forbidden_is_reported_without_leaking_exception(tmp_path):
    ctx, _, target, bot = make_context(tmp_path)
    target.add_roles.side_effect = discord.Forbidden(MagicMock(status=403), "missing permission")
    with patch("exe_bot.bot.discord.Member", FakeMember):
        try:
            await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
            assert "Discord refused 'give_role'" in ctx.reply.await_args.args[0]
        finally:
            await bot.close()


@pytest.mark.asyncio
async def test_discord_http_error_is_reported_to_script_author(tmp_path):
    ctx, _, target, bot = make_context(tmp_path)
    target.add_roles.side_effect = discord.HTTPException(MagicMock(status=500), "temporary API failure")
    with patch("exe_bot.bot.discord.Member", FakeMember):
        try:
            await bot.get_command("exe").callback(ctx, script='@add_role("456", "Helpers");')
            assert "Discord rejected an action" in ctx.reply.await_args.args[0]
        finally:
            await bot.close()
