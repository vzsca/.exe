from exe_bot.config import Settings
from exe_bot.permissions import is_owner, may_manage_access, may_run_scripts


def test_only_configured_owner_can_manage_access():
    settings = Settings(token="test-token", owner_id=100)
    assert may_manage_access(100, settings)
    assert not may_manage_access(200, settings)


def test_scripts_are_limited_to_owner_and_whitelist():
    settings = Settings(token="test-token", owner_id=100)
    assert may_run_scripts(100, settings, [])
    assert may_run_scripts(200, settings, [200])
    assert not may_run_scripts(300, settings, [200])


def test_owner_check_uses_exact_user_id():
    settings = Settings(token="test-token", owner_id=100)
    assert is_owner(100, settings)
    assert not is_owner(101, settings)
