import pytest

from exe_bot.language import (
    ScriptError,
    SendMessage,
    SetVariable,
    expand_actions,
    parse_script,
)


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
    with pytest.raises(ScriptError, match="text strings"):
        parse_script("send(123)")


def test_standard_variables_are_supported():
    program = parse_script('let greeting = "hello"\nsend(greeting)')
    assert program == [SetVariable("greeting", "hello"), SendMessage("hello")]
    assert expand_actions(program) == [SendMessage("hello")]


def test_compact_variables_match_standard_semantics():
    standard = parse_script('let greeting = "hello"\nsend(greeting)')
    compact = parse_script('v(greeting, "hello")\nm(greeting)')
    assert expand_actions(standard) == expand_actions(compact)


def test_standard_and_compact_repeat_match():
    standard = parse_script('repeat 3: send("go")')
    compact = parse_script('R(3, m("go"))')
    expected = [SendMessage("go")] * 3
    assert expand_actions(standard) == expected
    assert expand_actions(compact) == expected


def test_repeat_count_is_bounded():
    with pytest.raises(ScriptError, match="between 1 and 10"):
        parse_script('repeat 11: send("no")')


def test_unknown_variable_is_reported():
    with pytest.raises(ScriptError, match="unknown variable"):
        parse_script("send(missing)")


def test_repeat_expansion_respects_action_limit():
    with pytest.raises(ScriptError, match="limit of 4"):
        parse_script('repeat 3: send("x")\nsend("y")\nsend("z")', max_actions=4)
