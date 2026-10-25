from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from pathlib import Path
import tempfile

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


class DiscordIntegrationTests(IsolatedAsyncioTestCase):
    async def test_role_name_mentions_require_a_complete_name_boundary(self):
        tmp_path = Path(tempfile.mkdtemp())
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
            self.assertEqual(sent_text, f"{long.mention}; {short.mention}")
            self.assertEqual(allowed, [long, short])
        finally:
            await bot.close()

    async def test_role_id_reference_selects_the_exact_duplicate_name_role(self):
        tmp_path = Path(tempfile.mkdtemp())
        owner_id = 123
        old_role = FakeRole(11111111111111111, "Helpers")
        selected_role = FakeRole(22222222222222222, "Helpers")
        ctx, channel, _, _ = make_context(owner_id, [old_role, selected_role])
        bot = build_bot(Settings(token="test", owner_id=owner_id, database_path=str(tmp_path / "db.sqlite3")))
        try:
            await bot.get_command("exe").callback(
                ctx, script='send(f"Created @22222222222222222")'
            )
            channel.send.assert_awaited_once()
            self.assertEqual(channel.send.await_args.args[0], f"Created {selected_role.mention}")
            self.assertEqual(channel.send.await_args.kwargs["allowed_mentions"].roles, [selected_role])
        finally:
            await bot.close()
