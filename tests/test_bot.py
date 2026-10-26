import asyncio
from unittest.mock import AsyncMock

from exe_bot.config import Settings
from exe_bot.bot import build_bot


def test_unwhitelisted_user_is_denied_before_script_execution(tmp_path):
    async def scenario():
        bot = build_bot(Settings(
            token="test-token",
            owner_id=100,
            database_path=str(tmp_path / "bot.sqlite3"),
        ))
        ctx = type("Context", (), {})()
        ctx.author = type("Author", (), {"id": 200})()
        ctx.reply = AsyncMock()
        ctx.message = type("Message", (), {})()
        ctx.channel = type("Channel", (), {"id": 10})()
        ctx.guild = None

        try:
            command = bot.get_command("exe")
            await command.callback(ctx, script='@send("should not run");')
            ctx.reply.assert_awaited_once()
            assert "Access denied" in ctx.reply.await_args.args[0]
        finally:
            await bot.close()

    asyncio.run(scenario())


def test_non_owner_cannot_manage_whitelist(tmp_path):
    async def scenario():
        bot = build_bot(Settings(
            token="test-token",
            owner_id=100,
            database_path=str(tmp_path / "admin.sqlite3"),
        ))
        ctx = type("Context", (), {})()
        ctx.author = type("Author", (), {"id": 200})()
        ctx.reply = AsyncMock()
        ctx.message = type("Message", (), {})()
        ctx.channel = type("Channel", (), {"id": 10})()
        ctx.guild = None

        try:
            command = bot.get_command("exe")
            await command.callback(ctx, script="admin add 300")
            ctx.reply.assert_awaited_once()
            assert "only the configured owner" in ctx.reply.await_args.args[0]
            assert bot.db.list_whitelist() == []
        finally:
            bot.db.close()
            await bot.close()

    asyncio.run(scenario())
