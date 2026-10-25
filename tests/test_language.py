import pytest

from exe_bot.language import ScriptError, SendMessage, parse_script


def test_standard_and_compact_forms_share_action_type():
    standard = parse_script('send("hello")')
    compact = parse_script('m("hello")')
    assert standard == compact == [SendMessage("hello")]


def test_comments_and_blank_lines_are_ignored():
    assert parse_script('# comment\n\nsend("ok")') == [SendMessage("ok")]


def test_unknown_instruction_has_line_number():
    with pytest.raises(ScriptError, match="Line 2"):
        parse_script('\nrun_python("no")')


def test_action_limit_is_enforced():
    with pytest.raises(ScriptError, match="limit of 1"):
        parse_script('send("a")\nm("b")', max_actions=1)


def test_non_string_argument_is_rejected():
    with pytest.raises(ScriptError, match="must be a string"):
        parse_script('send(123)')
