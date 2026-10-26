import pytest

from exe_bot.language import DiscordAction, ScriptError, SendMessage, expand_actions, parse_script


def test_python_style_range_loop_expands_exclusive_stop():
    program = parse_script('for i in range(1, 4) { @send(f"item {i}"); }')
    assert expand_actions(program) == [
        SendMessage("item 1"),
        SendMessage("item 2"),
        SendMessage("item 3"),
    ]


def test_range_loop_interpolates_discord_action_arguments():
    program = parse_script(
        'for i in range(1, 4) { @create_category("Test-{i}"); }'
    )
    assert program == [
        DiscordAction("create_category", ("Test-1",)),
        DiscordAction("create_category", ("Test-2",)),
        DiscordAction("create_category", ("Test-3",)),
    ]

def test_range_loop_accepts_negative_start_and_keeps_stop_exclusive():
    program = parse_script('for i in range(-2, 1) { @send(f"{i}"); }')
    assert expand_actions(program) == [
        SendMessage("-2"),
        SendMessage("-1"),
        SendMessage("0"),
    ]


@pytest.mark.parametrize(
    "source, message",
    [
        ('for i in range(1, 12) { @send("too many"); }', "limited to 10 iterations"),
        ('for i in range(4, 1) { @send("backwards"); }', "stop must be greater than range start"),
        ('for i in range(-1000001, 0) { @send("too far"); }', "range bounds must be between"),
    ],
)
def test_range_loop_rejects_unsafe_or_invalid_bounds(source, message):
    with pytest.raises(ScriptError, match=message):
        parse_script(source)


def test_randint_variable_is_bounded_and_returns_an_integer():
    program = parse_script('var roll.int = randint(2, 5); @send(f"{roll}");')
    actions = expand_actions(program)
    assert len(actions) == 1
    assert isinstance(actions[0], SendMessage)
    assert actions[0].text.isdigit()
    assert 2 <= int(actions[0].text) <= 5


def test_randint_in_f_string_is_supported():
    program = parse_script('@send(f"roll={randint(2, 5)}");')
    assert len(program) == 1
    assert isinstance(program[0], SendMessage)
    assert program[0].text.startswith("roll=")
    assert 2 <= int(program[0].text.removeprefix("roll=")) <= 5


@pytest.mark.parametrize(
    "source, message",
    [
        ('var roll.int = randint(5, 2); @send("no");', "minimum cannot exceed maximum"),
        ('var roll.int = randint(-1000000001, 0); @send("no");', "bounds must be between"),
        ('@send(f"{randint(1, 1000000001)}");', "bounds must be between"),
    ],
)
def test_randint_rejects_invalid_bounds(source, message):
    with pytest.raises(ScriptError, match=message):
        parse_script(source)
