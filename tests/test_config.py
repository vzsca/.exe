import pytest

from exe_bot.config import _positive_float, _positive_int


def test_script_timeout_accepts_five_minutes(monkeypatch):
    monkeypatch.setenv("SCRIPT_TIMEOUT_SECONDS", "300")
    assert _positive_float("SCRIPT_TIMEOUT_SECONDS", 60.0) == 300.0


def test_script_timeout_rejects_more_than_five_minutes(monkeypatch):
    monkeypatch.setenv("SCRIPT_TIMEOUT_SECONDS", "301")
    with pytest.raises(RuntimeError, match="at most 300"):
        _positive_float("SCRIPT_TIMEOUT_SECONDS", 60.0)


def test_action_budget_accepts_one_thousand(monkeypatch):
    monkeypatch.setenv("MAX_SCRIPT_ACTIONS", "1000")
    assert _positive_int("MAX_SCRIPT_ACTIONS", 20) == 1000


def test_action_budget_rejects_more_than_one_thousand(monkeypatch):
    monkeypatch.setenv("MAX_SCRIPT_ACTIONS", "1001")
    with pytest.raises(RuntimeError, match="between 1 and 1000"):
        _positive_int("MAX_SCRIPT_ACTIONS", 20)



def test_members_intent_is_disabled_by_default(monkeypatch):
    from exe_bot.config import load_settings

    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("OWNER_ID", "123456789")
    monkeypatch.delenv("ENABLE_MEMBERS_INTENT", raising=False)
    assert load_settings().enable_members_intent is False


def test_members_intent_can_be_enabled_explicitly(monkeypatch):
    from exe_bot.config import load_settings

    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("OWNER_ID", "123456789")
    monkeypatch.setenv("ENABLE_MEMBERS_INTENT", "true")
    assert load_settings().enable_members_intent is True


def test_members_intent_rejects_invalid_boolean(monkeypatch):
    from exe_bot.config import load_settings

    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("OWNER_ID", "123456789")
    monkeypatch.setenv("ENABLE_MEMBERS_INTENT", "sometimes")
    with pytest.raises(RuntimeError, match="ENABLE_MEMBERS_INTENT must be a boolean"):
        load_settings()
