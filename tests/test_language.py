import pytest

from exe_bot.language import (
    DiscordAction,
    InputVariable,
    IfEquals,
    ScriptError,
    SendMessage,
    expand_actions,
    parse_script,
)


def test_typed_variables_and_native_send():
    program = parse_script('var greeting.str = "hello"; @send(greeting);')
    assert expand_actions(program) == [SendMessage("hello")]


def test_arithmetic_and_set_update():
    program = parse_script(
        'var count.int = 2; set count = count + 3 * 2; @send(f"count={count}");'
    )
    assert expand_actions(program) == [SendMessage("count=8")]


def test_repeat_block_expands_actions():
    program = parse_script('repeat(2) { @send("again"); }')
    assert expand_actions(program) == [SendMessage("again"), SendMessage("again")]


def test_if_block_runs_when_true():
    program = parse_script(
        'var mode.str = "safe"; if (mode == "safe") { @send("allowed"); }'
    )
    assert expand_actions(program) == [SendMessage("allowed")]


def test_if_else_blocks():
    program = parse_script(
        'var mode.str = "safe"; '
        'if (mode == "admin") { @send("admin"); } else { @send("safe"); }'
    )
    assert expand_actions(program) == [SendMessage("safe")]


def test_counted_for_loop():
    program = parse_script('for i in range(0, 3) { @send(f"{i}"); }')
    assert expand_actions(program) == [SendMessage("0"), SendMessage("1"), SendMessage("2")]


def test_typed_input_declaration():
    program = parse_script(
        'var username.input{str, "Your name?"} = ""; @send("ready");'
    )
    assert isinstance(program[0], InputVariable)
    assert program[0].name == "username"
    assert program[0].question == "Your name?"


def test_none_for_unset_discord_identifier():
    program = parse_script('var target.user.id = None; @send("ready");')
    assert program[0].value is None
    assert expand_actions(program) == [SendMessage("ready")]


@pytest.mark.parametrize(
    "source",
    [
        'let greeting = "hello"; @send(greeting);',
        'send("hello");',
        'm("hello");',
        'v(greeting, "hello");',
        'R(2, @send("hello"));',
        'I(mode, "safe", @send("hello"));',
    ],
)
def test_legacy_and_compact_syntax_is_rejected(source):
    with pytest.raises(ScriptError):
        parse_script(source)


def test_native_functions_require_at_prefix():
    with pytest.raises(ScriptError, match="start with"):
        parse_script('create_channel("general");')


def test_every_statement_requires_semicolon():
    with pytest.raises(ScriptError, match="must end with"):
        parse_script('var greeting.str = "hello"')


def test_semicolon_inside_string_is_literal():
    assert expand_actions(parse_script('@send("one; two");')) == [SendMessage("one; two")]


def test_unknown_native_function_is_rejected():
    with pytest.raises(ScriptError, match="unknown instruction"):
        parse_script('@run_python("print(1)");')


def test_native_action_arguments_are_checked():
    assert parse_script('@create_channel("general");') == [
        DiscordAction("create_channel", ("general",))
    ]
    with pytest.raises(ScriptError, match="expects"):
        parse_script('@create_channel();')


def test_action_budget_is_enforced():
    with pytest.raises(ScriptError, match="limit of 1"):
        parse_script('@send("a"); @send("b");', max_actions=1)


def test_unsafe_expression_call_is_rejected():
    with pytest.raises(ScriptError):
        parse_script('var value.int = __import__("os").system("whoami"); @send("x");')


def test_unclosed_block_is_rejected():
    with pytest.raises(ScriptError, match="Unclosed block brace"):
        parse_script('repeat(2) { @send("x");')


def test_native_call_inside_string_does_not_trigger_legacy_rejection():
    assert expand_actions(parse_script('@send("write send( in a message;");')) == [
        SendMessage("write send( in a message;")
    ]


def test_unprefixed_native_call_is_rejected_even_after_other_statement():
    with pytest.raises(ScriptError, match="start with"):
        parse_script('var note.str = "ok"; create_channel("general");')


def test_unclosed_quote_is_rejected():
    with pytest.raises(ScriptError, match="Unclosed quote"):
        parse_script('@send("not closed);')


def test_action_budget_counts_both_if_branches():
    with pytest.raises(ScriptError, match="limit of 1"):
        parse_script('var enabled.bool = True; if (enabled == True) { @send("a"); } else { @send("b"); }', max_actions=1)


def test_boolean_operators_short_circuit():
    # The right-hand side must not be evaluated when the result is already known.
    program = parse_script(
        'var enabled.bool = False; '
        'var result.bool = enabled and (1 / 0); '
        '@send("safe");'
    )
    assert program[1].value is False
    assert expand_actions(program) == [SendMessage("safe")]


def test_or_operator_short_circuits():
    program = parse_script(
        'var enabled.bool = True; '
        'var result.bool = enabled or (1 / 0); '
        '@send("safe");'
    )
    assert program[1].value is True


def test_dictionary_literal_and_indexing():
    program = parse_script(
        'var config.dict = {"mode": "safe", "retries": 3}; '
        'var mode.str = config["mode"]; '
        'var retries.int = config["retries"]; '
        '@send(f"{mode}:{retries}");'
    )
    assert program[0].value == {"mode": "safe", "retries": 3}
    assert program[1].value == "safe"
    assert program[2].value == 3
    assert expand_actions(program) == [SendMessage("safe:3")]


def test_nested_dictionary_and_list_literals():
    program = parse_script(
        'var config.dict = {"items": [1, 2], "nested": {"enabled": True}}; '
        'var enabled.bool = config["nested"]["enabled"]; '
        '@send(f"{enabled}");'
    )
    assert program[0].value == {"items": [1, 2], "nested": {"enabled": True}}
    assert program[1].value is True
    assert expand_actions(program) == [SendMessage("True")]


def test_dictionary_literal_does_not_break_following_block():
    program = parse_script(
        'var config.dict = {"mode": "safe"}; '
        'var mode.str = config["mode"]; if (mode == "safe") { @send("ok"); }'
    )
    assert expand_actions(program) == [SendMessage("ok")]



def test_condition_on_runtime_input_is_deferred_until_execution():
    program = parse_script(
        'var answer.input{str, "Type yes"} = ""; '
        'if (answer == "yes") { @send("accepted"); } '
        'else { @send("rejected"); }'
    )
    assert isinstance(program[1], IfEquals)
    assert program[1].matched is None
    actions = expand_actions(program)
    assert isinstance(actions[1], IfEquals)
    assert actions[1].variable_name == "answer"
    assert actions[1].expected == "yes"
    assert [action.text for action in expand_actions(list(actions[1].body))] == ["accepted"]
    assert [action.text for action in expand_actions(list(actions[1].else_body))] == ["rejected"]


def test_native_aliases_inside_message_strings_are_preserved():
    source = '@send("write @send( and mute( literally");'
    assert expand_actions(parse_script(source)) == [
        SendMessage("write @send( and mute( literally")
    ]


def test_expression_ast_depth_is_bounded():
    expression = "not " * 40 + "True"
    with pytest.raises(ScriptError, match="nested too deeply"):
        parse_script(f"var flag.bool = {expression}; @send(\"safe\");")


def test_expression_numeric_result_is_bounded():
    large = "9" * 1000
    expression = " * ".join([large] * 6)
    with pytest.raises(ScriptError, match="numeric result is too large"):
        parse_script(f"var value.int = {expression}; @send(\"safe\");")



def test_if_branch_keeps_all_actions_inside_the_branch():
    program = parse_script(
        'var mode.str = "safe"; '
        'if (mode == "safe") { @send("first"); @send("second"); } '
        'else { @send("blocked-1"); @send("blocked-2"); } '
        '@send("after");'
    )
    assert expand_actions(program) == [
        SendMessage("first"),
        SendMessage("second"),
        SendMessage("after"),
    ]


def test_else_branch_can_contain_multiple_actions():
    program = parse_script(
        'var mode.str = "safe"; '
        'if (mode == "admin") { @send("admin"); } '
        'else { @send("safe-1"); @send("safe-2"); }'
    )
    assert expand_actions(program) == [
        SendMessage("safe-1"),
        SendMessage("safe-2"),
    ]


def test_repeat_block_keeps_all_actions_in_each_iteration():
    program = parse_script(
        'repeat(2) { @send("first"); @send("second"); }'
    )
    assert expand_actions(program) == [
        SendMessage("first"), SendMessage("second"),
        SendMessage("first"), SendMessage("second"),
    ]



def test_fstring_accepts_nested_create_role_call_with_double_quotes():
    source = 'var test.int = 10; repeat(3){@send(f"{test}{@create_role("role","#FF0000",administrator:True)}");}'
    program = parse_script(source)
    actions = expand_actions(program)
    assert len(actions) == 6
    assert all(isinstance(action, DiscordAction) for action in actions[0::2])
    assert all(action.name == "create_role" for action in actions[0::2])
    assert all(action.arguments == ("role", "#FF0000", "administrator") for action in actions[0::2])
    assert all(isinstance(action, SendMessage) for action in actions[1::2])
    assert all(action.role_mentions for action in actions[1::2])
    assert all(action.text.startswith("10__EXE_VAR___exe_result_") for action in actions[1::2])


def test_role_id_type_is_declared_after_variable_name():
    program = parse_script('var new_role.role.id = None; @send("ready");')
    assert program[0].name == "new_role"
    assert program[0].value is None


def test_create_role_result_requires_role_id_type():
    with pytest.raises(ScriptError, match="role.id"):
        parse_script('var new_role.id = None; set new_role = @create_role("role");')



def test_role_id_shorthand_is_supported():
    program = parse_script('var role.id = None; @send("ready");')
    assert program[0].name == "role"
    assert program[0].value is None


def test_create_role_result_can_be_used_in_later_fstring():
    program = parse_script(
        'var role.id = None; '
        'set role = @create_role("Helpers", "#5865F2"); '
        '@send(f"{role}");'
    )
    actions = expand_actions(program)
    assert actions[0] == DiscordAction("create_role", ("Helpers", "#5865F2"), "role")
    assert actions[1] == SendMessage("__EXE_VAR_role__", role_mentions=True)


@pytest.mark.parametrize(
    "source, expected_action, expected_type, expected_message",
    [
        (
            'var channel.channel.id = None; set channel = @create_channel("annonces"); @send(f"{channel}");',
            "create_channel", "channel.id",
            SendMessage("#__EXE_VAR_channel__", channel_mentions=True),
        ),
        (
            'var category.category.id = None; set category = @create_category("Infos"); @send(category);',
            "create_category", "category.id", SendMessage("__EXE_VAR_category__"),
        ),
    ],
)
def test_created_channel_and_category_results_are_typed_and_reusable(
    source, expected_action, expected_type, expected_message
):
    actions = expand_actions(parse_script(source))
    assert actions[0].name == expected_action
    assert actions[0].result_variable in {"channel", "category"}
    assert actions[-1] == expected_message


def test_create_channel_result_requires_channel_id_type():
    with pytest.raises(ScriptError, match="channel.id"):
        parse_script(
            'var channel.id = None; set channel = @create_channel("annonces"); @send("ok");'
        )


def test_create_category_result_requires_category_id_type():
    with pytest.raises(ScriptError, match="category.id"):
        parse_script(
            'var category.id = None; set category = @create_category("Infos"); @send("ok");'
        )
