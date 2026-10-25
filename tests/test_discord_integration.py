from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from exe_bot.bot import build_bot
from exe_bot.config import Settings


class FakeRole:
    def __init__(self, role_id: int, name: str):
        self.id = role_id
        self.name = name
        self.mention = f"<@&{role_id}>"


def make_context(owner_id: int, roles: list[FakeRole]):
    channel = SimpleNamespace(id=300, send=AsyncMock())
    author = SimpleNamespace(id=owner_id, bot=False)
    message = SimpleNamespace(add_reaction=AsyncMock())
    guild = SimpleNamespace(
        roles=roles,
        get_role=lambda role_id: next((role for role in roles if role.id == role_id), None),
        get_channel=lambda channel_id: None,
        text_channels=[],
    )
    replies = []

    async def reply(content, **kwargs):
        replies.append(content)

    ctx = SimpleNamespace(
        author=author,
        channel=channel,
        guild=guild,
        message=message,
        reply=AsyncMock(side_effect=reply),
    )
    return ctx, channel, replies, guild


@pytest.mark.asyncio
async def test_role_name_mentions_require_a_complete_name_boundary(tmp_path):
    owner_id = 123
    short = FakeRole(11111111111111111, "Mod")
    long = FakeRole(22222222222222222, "Moderator")
    ctx, channel, _, _ = make_context(owner_id, [short, long])
    bot = build_bot(Settings(token="test", owner_id=owner_id, database_path=str(tmp_path / "db.sqlite3")))
    try:
        await bot.get_command("exe").callback(ctx, script='send(f"@Moderator; @Mod")')
        channel.send.assert_awaited_once()
        sent_text = channel.send.await_args.args[0]
        allowed = channel.send.await_args.kwargs["allowed_mentions"].roles
        assert sent_text == f"{long.mention}; {short.mention}"
        assert allowed == [long, short]
    finally:
        await bot.close()


@pytest.mark.asyncio
async def test_created_role_is_mentioned_by_id_even_with_duplicate_names(tmp_path):
    owner_id = 123
    old_role = FakeRole(11111111111111111, "Helpers")
    created_role = FakeRole(22222222222222222, "Helpers")
    ctx, channel, _, guild = make_context(owner_id, [old_role])
    async def create_role(**kwargs):
        guild.roles.append(created_role)
        return created_role
    guild.create_role = AsyncMock(side_effect=create_role)
    bot = build_bot(Settings(token="test", owner_id=owner_id, database_path=str(tmp_path / "db.sqlite3")))
    try:
        await bot.get_command("exe").callback(
            ctx, script='send(f"Created {create_role(\'Helpers\')}")'
        )
        channel.send.assert_awaited_once()
        assert channel.send.await_args.args[0] == f"Created {created_role.mention}"
        assert channel.send.await_args.kwargs["allowed_mentions"].roles == [created_role]
    finally:
        await bot.close()
