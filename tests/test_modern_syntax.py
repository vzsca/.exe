import pytest

from exe_bot.language import (
    DiscordAction,
    InputVariable,
    SendMessage,
    ScriptError,
    expand_actions,
    parse_script,
)


def test_english_brace_syntax_and_at_send():
    program = parse_script('var greeting.str = "Hello"; @send(greeting);')
    assert expand_actions(program) == [SendMessage("Hello")]


def test_brace_if_and_repeat_syntax():
    program = parse_script(
        'var mode.str = "safe";\n'
        'if (mode == "safe") {\n'
        '  @send("allowed");\n'
        '}\n'
        'repeat(2) { @send("again"); }'
    )
    assert expand_actions(program) == [
        SendMessage("allowed"),
        SendMessage("again"),
        SendMessage("again"),
    ]


def test_canonical_english_action_names_are_supported():
    assert parse_script('@add_role("123456789012345678", "Helpers");') == [
        DiscordAction("give_role", ("123456789012345678", "Helpers"))
    ]
    assert parse_script('@create_channel("general");') == [
        DiscordAction("create_channel", ("general",))
    ]


def test_typed_input_declaration_uses_input_instruction():
    program = parse_script(
        'var username.input{str, "What is your username?"} = "";\n'
        '@send(f"Hello {username}!");'
    )
    assert isinstance(program[0], InputVariable)
    assert program[0].name == "username"
    assert program[0].question == "What is your username?"


def test_unknown_declared_type_is_rejected():
    with pytest.raises(ScriptError, match="Unknown variable type"):
        parse_script('var value.unknown = "x"; @send(value);')


def test_unclosed_brace_is_rejected():
    with pytest.raises(ScriptError, match="Unclosed block brace"):
        parse_script('repeat(2) { @send("x");')


def test_none_is_accepted_for_unset_typed_discord_ids():
    program = parse_script('var target.user.id = None; @send("ready");')
    assert program[0].name == "target"
    assert program[0].value is None
    assert expand_actions(program) == [SendMessage("ready")]


def test_misspelled_channel_function_is_not_a_supported_alias():
    with pytest.raises(ScriptError, match="unknown instruction"):
        parse_script('@create_chanel("general")')

def test_arithmetic_expressions_and_set_updates_are_supported():
    program = parse_script(
        'var count.int = 2; set count = count + 3 * 2; @send(f"count={count}");'
    )
    assert expand_actions(program) == [SendMessage("count=8")]


def test_safe_expression_rejects_function_calls():
    with pytest.raises(ScriptError, match="invalid or unsupported expression"):
        parse_script('var value.int = __import__("os").system("whoami"); @send("x")')


def test_boolean_and_none_literals_are_preserved():
    program = parse_script('var enabled.bool = True; var target.user.id = None; @send("ready");')
    assert program[0].value is True
    assert program[1].value is None

def test_missing_semicolon_is_rejected():
    with pytest.raises(ScriptError, match="every instruction must end"):
        parse_script('var greeting.str = "Hello"\n@send(greeting);')


def test_legacy_send_syntax_is_rejected():
    with pytest.raises(ScriptError, match="must start with @"):
        parse_script('send("Hello");')

def test_multiple_statements_on_one_line_are_supported():
    program = parse_script('var count.int = 1; set count = count + 2; @send(f"{count}");')
    assert expand_actions(program) == [SendMessage("3")]


def test_newlines_after_semicolons_are_optional():
    program = parse_script('var count.int = 1;\nset count = count + 1;\n@send(f"{count}");')
    assert expand_actions(program) == [SendMessage("2")]


def test_missing_semicolon_before_closing_brace_is_rejected():
    with pytest.raises(ScriptError, match="must end with"):
        parse_script('if (True == True) { @send("missing") }')


def test_legacy_native_call_inside_a_line_is_rejected():
    with pytest.raises(ScriptError, match="start with"):
        parse_script('var x.str = "ok"; send(x);')


def test_semicolon_inside_string_is_not_a_separator():
    program = parse_script('@send("one; two");')
    assert expand_actions(program) == [SendMessage("one; two")]
