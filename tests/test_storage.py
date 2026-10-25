import pytest

from exe_bot.storage import Database, StorageError


def test_whitelist_add_list_and_remove(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    assert db.add_whitelist(123, 456) is True
    assert db.add_whitelist(123, 456) is False
    assert db.is_whitelisted(123)
    assert db.list_whitelist() == [123]
    assert db.remove_whitelist(123) is True
    assert db.remove_whitelist(123) is False
    assert not db.is_whitelisted(123)


def test_scripts_are_isolated_by_owner(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    db.save_script(100, "hello", 'send("hello")')
    db.save_script(200, "hello", 'send("different")')
    assert db.get_script(100, "hello") == 'send("hello")'
    assert db.get_script(200, "hello") == 'send("different")'
    assert db.list_scripts(100) == ["hello"]
    assert db.delete_script(100, "hello")
    assert db.get_script(100, "hello") is None
    assert db.get_script(200, "hello") == 'send("different")'


def test_script_save_updates_existing_name(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    db.save_script(100, "hello", 'send("one")')
    db.save_script(100, "hello", 'send("two")')
    assert db.get_script(100, "hello") == 'send("two")'


def test_event_handlers_can_be_disabled(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    db.save_event(100, "welcome", 'send("hi")', enabled=False)
    assert db.get_event(100, "welcome") == ('send("hi")', False)
    assert db.list_events(100) == ["welcome"]
    assert db.delete_event(100, "welcome")
    assert db.get_event(100, "welcome") is None


def test_invalid_names_are_rejected(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    with pytest.raises(StorageError, match="Name must start"):
        db.save_script(100, "../oops", 'send("no")')


def test_empty_script_is_rejected(tmp_path):
    db = Database(str(tmp_path / "exe.sqlite3"))
    with pytest.raises(StorageError, match="between 1 and 8000"):
        db.save_script(100, "empty", "   ")
