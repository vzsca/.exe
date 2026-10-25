import pytest

from exe_bot.language import (
    ScriptError,
    InputVariable,
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



def test_compact_section_separator_acts_like_newline():
    source = 'v(greeting, "hello")§m(greeting)§R(2, m("again"))'
    program = parse_script(source)
    assert expand_actions(program) == [
        SendMessage("hello"),
        SendMessage("again"),
        SendMessage("again"),
    ]


def test_section_separator_inside_quoted_text_is_preserved():
    program = parse_script('m("left§right")§m("next")')
    assert expand_actions(program) == [
        SendMessage("left§right"),
        SendMessage("next"),
    ]


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



def test_compact_repeat_supports_multiple_nested_actions():
    program = parse_script(
        'R(2, m("start")§create_role("Tester", "#5865F2", "view_channel, send_messages"))'
    )
    assert expand_actions(program) == [
        SendMessage("start"),
        DiscordAction("create_role", ("Tester", "#5865F2", "view_channel, send_messages")),
        SendMessage("start"),
        DiscordAction("create_role", ("Tester", "#5865F2", "view_channel, send_messages")),
    ]


def test_compact_condition_supports_multiple_nested_actions():
    program = parse_script(
        'v(mode, "safe")§I(mode, "safe", m("allowed")§create_category("Test"))'
    )
    assert expand_actions(program) == [
        SendMessage("allowed"),
        DiscordAction("create_category", ("Test",)),
    ]


def test_nested_separator_inside_quotes_is_preserved():
    program = parse_script('R(2, m("left§right")§m("next"))')
    assert expand_actions(program) == [
        SendMessage("left§right"),
        SendMessage("next"),
        SendMessage("left§right"),
        SendMessage("next"),
    ]


def test_nested_repeat_can_contain_multiple_actions():
    program = parse_script('R(2, m("outer")§R(2, m("inner")))')
    assert expand_actions(program) == [
        SendMessage("outer"),
        SendMessage("inner"),
        SendMessage("inner"),
        SendMessage("outer"),
        SendMessage("inner"),
        SendMessage("inner"),
    ]



def test_indented_repeat_supports_multiple_actions():
    program = parse_script('repeat 2:\n    send("start")\n    send("end")')
    assert expand_actions(program) == [
        SendMessage("start"), SendMessage("end"),
        SendMessage("start"), SendMessage("end"),
    ]


def test_nested_indented_blocks_are_supported():
    program = parse_script(
        'repeat 2:\n'
        '    send("outer")\n'
        '    repeat 2:\n'
        '        send("inner")'
    )
    assert expand_actions(program) == [
        SendMessage("outer"), SendMessage("inner"), SendMessage("inner"),
        SendMessage("outer"), SendMessage("inner"), SendMessage("inner"),
    ]


def test_indented_if_else_blocks_are_supported():
    program = parse_script(
        'let mode = "safe"\n'
        'if mode == "admin":\n'
        '    send("admin")\n'
        '    send("second admin message")\n'
        'else:\n'
        '    send("safe")'
    )
    assert expand_actions(program) == [SendMessage("safe")]


def test_unexpected_indentation_is_rejected():
    with pytest.raises(ScriptError, match="unexpected indentation"):
        parse_script('send("one")\n    send("two")')


def test_empty_indented_block_is_rejected():
    with pytest.raises(ScriptError, match="block body cannot be empty"):
        parse_script('repeat 2:\nsend("not indented")')



def test_send_f_string_supports_defined_variables_and_role_mentions():
    program = parse_script('let greeting = "Salut"\nsend(f"{greeting} @Moderateurs")')
    assert expand_actions(program) == [SendMessage("Salut @Moderateurs", None, True)]


def test_send_can_target_a_channel_by_name_or_id():
    assert parse_script('send("hello", "#general")') == [
        SendMessage("hello", "#general", False)
    ]
    assert parse_script('send("hello", "123456789012345678")') == [
        SendMessage("hello", "123456789012345678", False)
    ]


def test_f_string_does_not_allow_python_expressions():
    with pytest.raises(ScriptError, match="only support text and defined variables"):
        parse_script('send(f"{1 + 1}")')


def test_input_variable_is_parsed_and_kept_in_action_order():
    program = parse_script('let pseudo = input("Quel est ton pseudo ?")\nsend(f"Bienvenue {pseudo} !")')
    assert isinstance(program[0], InputVariable)
    assert program[0].name == "pseudo"
    assert program[0].question == "Quel est ton pseudo ?"
    actions = expand_actions(program)
    assert actions[0] == program[0]
    assert actions[1] == SendMessage("Bienvenue __EXE_VAR_pseudo__ !", None, True)


def test_input_requires_a_non_empty_question():
    with pytest.raises(ScriptError, match="input question cannot be empty"):
        parse_script('let answer = input("")\nsend("ok")')


def test_list_and_dictionary_values_and_indexing():
    program = parse_script('let users = ["Alice", "Bob"]\nlet config = {"prefix": "!exe", "mode": "safe"}\nsend(f"{users[0]} uses {config[\'prefix\']}")')
    assert program[-1] == SendMessage("Alice uses !exe", None, True)


def test_create_role_can_be_called_inside_f_string():
    program = parse_script('send(f"Created {create_role(\'Testers\')}")')
    assert program == [
        DiscordAction("create_role", ("Testers",), "__exe_result_0"),
        SendMessage("Created __EXE_VAR___exe_result_0__", None, True),
    ]


def test_list_and_dictionary_are_bounded():
    with pytest.raises(ScriptError, match="limited to 100"):
        parse_script('let users = ' + repr(list(range(101))) + '\nsend("ok")')



def test_guild_inventory_functions_are_allowed_only_as_no_arg_fstring_calls():
    program = parse_script(
        'send(f"Roles: {guilds_roles()}")\\n'
        'send(f"Members: {guilds_members()}")\\n'
        'send(f"Channels: {guilds_channels()}")\\n'
        'send(f"Categories: {guilds_categories()}")'
    )
    assert len(program) == 8
    assert all(isinstance(item, DiscordAction) or isinstance(item, SendMessage) for item in program)
    with pytest.raises(ScriptError, match="takes no arguments"):
        parse_script('send(f"{guilds_roles(1)}")')


def test_indented_counted_loop_supports_counter_interpolation():
    program = parse_script(
        'repeat 3 as i:\n'
        '    send(f"item {i}")'
    )
    assert expand_actions(program) == [
        SendMessage("item 1"), SendMessage("item 2"), SendMessage("item 3")
    ]


def test_counted_loop_interpolates_role_names_and_keeps_ping_actions():
    program = parse_script('repeat 3 as i: send(f"{create_role(\'role {i}\')}")')
    assert program == [
        DiscordAction("create_role", ("role 1",), "__exe_result_0"),
        SendMessage("__EXE_VAR___exe_result_0__", None, True),
        DiscordAction("create_role", ("role 2",), "__exe_result_0"),
        SendMessage("__EXE_VAR___exe_result_0__", None, True),
        DiscordAction("create_role", ("role 3",), "__exe_result_0"),
        SendMessage("__EXE_VAR___exe_result_0__", None, True),
    ]
