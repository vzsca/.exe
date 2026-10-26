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
