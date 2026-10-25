import pytest

from exe_bot.language import (
    ScriptError,
    DiscordAction,
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



def test_standard_equality_condition_runs_only_when_true():
    program = parse_script('let mode = "safe"\nif mode == "safe": send("allowed")')
    assert expand_actions(program) == [SendMessage("allowed")]


def test_standard_equality_condition_skips_false_body():
    program = parse_script('let mode = "safe"\nif mode == "danger": send("no")')
    assert expand_actions(program) == []


def test_compact_condition_matches_standard_semantics():
    standard = parse_script('let mode = "safe"\nif mode == "safe": send("allowed")')
    compact = parse_script('v(mode, "safe")\nI(mode, "safe", m("allowed"))')
    assert expand_actions(standard) == expand_actions(compact)


def test_condition_requires_defined_variable():
    with pytest.raises(ScriptError, match="unknown variable"):
        parse_script('if mode == "safe": send("no")')


def test_condition_body_counts_towards_action_limit_even_when_false():
    with pytest.raises(ScriptError, match="limit of 1"):
        parse_script('let mode = "safe"\nif mode == "no": send("a")\nsend("b")', max_actions=1)



def test_standard_else_runs_when_condition_is_false():
    program = parse_script(
        'let mode = "safe"\n'
        'if mode == "admin": send("allowed")\n'
        'else: send("denied")'
    )
    assert expand_actions(program) == [SendMessage("denied")]


def test_standard_else_is_skipped_when_condition_is_true():
    program = parse_script(
        'let mode = "safe"\n'
        'if mode == "safe": send("allowed")\n'
        'else: send("denied")'
    )
    assert expand_actions(program) == [SendMessage("allowed")]


def test_else_action_counts_towards_action_limit():
    with pytest.raises(ScriptError, match="limit of 1"):
        parse_script(
            'let mode = "safe"\n'
            'if mode == "safe": send("allowed")\n'
            'else: send("denied")',
            max_actions=1,
        )


def test_else_without_if_is_rejected():
    with pytest.raises(ScriptError, match="else must immediately follow"):
        parse_script('else: send("denied")')



def test_compact_else_runs_when_condition_is_false():
    program = parse_script(
        'v(mode, "safe")\n'
        'I(mode, "admin", m("allowed"))\n'
        'E(m("denied"))'
    )
    assert expand_actions(program) == [SendMessage("denied")]


def test_compact_else_is_skipped_when_condition_is_true():
    program = parse_script(
        'v(mode, "safe")\n'
        'I(mode, "safe", m("allowed"))\n'
        'E(m("denied"))'
    )
    assert expand_actions(program) == [SendMessage("allowed")]


def test_compact_else_without_condition_is_rejected():
    with pytest.raises(ScriptError, match="else must immediately follow"):
        parse_script('E(m("denied"))')


@pytest.mark.parametrize('source, expected', [
    ('ban("123456789012345678", "spam")', DiscordAction('ban', ('123456789012345678', 'spam'))),
    ('unban("123456789012345678")', DiscordAction('unban', ('123456789012345678',))),
    ('kick("123456789012345678", "spam")', DiscordAction('kick', ('123456789012345678', 'spam'))),
    ('timeout("123456789012345678", 10)', DiscordAction('timeout', ('123456789012345678', 10))),
    ('untimeout("123456789012345678")', DiscordAction('untimeout', ('123456789012345678',))),
    ('create_role("Helpers")', DiscordAction('create_role', ('Helpers',))),
    ('create_role("Helpers", "#5865F2")', DiscordAction('create_role', ('Helpers', '#5865F2'))),
    ('create_role("Helpers", "#5865F2", "view_channel, send_messages")', DiscordAction('create_role', ('Helpers', '#5865F2', 'view_channel, send_messages'))),
    ('delete_role("123456789012345678")', DiscordAction('delete_role', ('123456789012345678',))),
    ('create_category("Tests")', DiscordAction('create_category', ('Tests',))),
    ('create_category("Private", "@everyone:view_channel=deny, Moderators:view_channel=allow")', DiscordAction('create_category', ('Private', '@everyone:view_channel=deny, Moderators:view_channel=allow'))),
    ('create_channel("general")', DiscordAction('create_channel', ('general',))),
    ('create_channel("staff", "Staff")', DiscordAction('create_channel', ('staff', 'Staff'))),
    ('create_channel("staff", "Staff", "@everyone:view_channel=deny, Moderators:view_channel=allow")', DiscordAction('create_channel', ('staff', 'Staff', '@everyone:view_channel=deny, Moderators:view_channel=allow'))),
    ('delete_channel("123456789012345678")', DiscordAction('delete_channel', ('123456789012345678',))),
    ('slowmode(5)', DiscordAction('slowmode', (5,))),
    ('clear(25)', DiscordAction('clear', (25,))),
])
def test_discord_actions_parse_to_explicit_instructions(source, expected):
    assert parse_script(source) == [expected]
    assert expand_actions(parse_script(source)) == [expected]


def test_unknown_function_is_not_allowed():
    with pytest.raises(ScriptError, match='unknown instruction'):
        parse_script('run_python("print(1)")')


def test_discord_action_counts_towards_action_limit():
    with pytest.raises(ScriptError, match='limit of 1'):
        parse_script('clear(5)\nban("123456789012345678", "reason")', max_actions=1)
