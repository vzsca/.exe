import pytest

from exe_bot.language import DiscordAction, ScriptError, SendMessage, expand_actions, parse_script


def test_python_style_range_loop_expands_exclusive_stop_at_top_level():
    program = parse_script(
        'for i in range(1, 4):\n'
        '    send(f"item {i}")'
    )
    assert expand_actions(program) == [
        SendMessage("item 1", None, True),
        SendMessage("item 2", None, True),
        SendMessage("item 3", None, True),
    ]


def test_range_loop_interpolates_discord_action_arguments():
    program = parse_script(
        'for i in range(1, 4):\n'
        '    create_category("Test-{i}")\n'
        '    create_channel("annonces-test-{i}", "Test-{i}")'
    )
    assert program == [
        DiscordAction("create_category", ("Test-1",)),
        DiscordAction("create_channel", ("annonces-test-1", "Test-1")),
        DiscordAction("create_category", ("Test-2",)),
        DiscordAction("create_channel", ("annonces-test-2", "Test-2")),
        DiscordAction("create_category", ("Test-3",)),
        DiscordAction("create_channel", ("annonces-test-3", "Test-3")),
    ]


def test_range_loop_accepts_negative_start_and_keeps_stop_exclusive():
    program = parse_script('for i in range(-2, 1): send(f"{i}")')
    assert expand_actions(program) == [
        SendMessage("-2", None, True),
        SendMessage("-1", None, True),
        SendMessage("0", None, True),
    ]


@pytest.mark.parametrize(
    "source, message",
    [
        ('for i in range(1, 12): send("too many")', "limited to 10 iterations"),
        ('for i in range(4, 1): send("backwards")', "stop must be greater than range start"),
        ('for i in range(-1000001, 0): send("too far")', "range bounds must be between"),
    ],
)
def test_range_loop_rejects_unsafe_or_invalid_bounds(source, message):
    with pytest.raises(ScriptError, match=message):
        parse_script(source)


def test_randint_variable_is_bounded_and_returns_an_integer():
    program = parse_script('let roll = randint(2, 5)\nsend(f"{roll}")')
    actions = expand_actions(program)
    assert len(actions) == 1
    assert isinstance(actions[0], SendMessage)
    assert actions[0].text.isdigit()
    assert 2 <= int(actions[0].text) <= 5


def test_randint_in_f_string_is_supported():
    program = parse_script('send(f"roll={randint(2, 5)}")')
    assert len(program) == 1
    assert isinstance(program[0], SendMessage)
    assert program[0].text.startswith("roll=")
    assert 2 <= int(program[0].text.removeprefix("roll=")) <= 5


@pytest.mark.parametrize(
    "source, message",
    [
        ('let roll = randint(5, 2)\nsend("no")', "minimum cannot exceed maximum"),
        ('let roll = randint(-1000000001, 0)\nsend("no")', "bounds must be between"),
        ('send(f"{randint(1, 1000000001)}")', "bounds must be between"),
    ],
)
def test_randint_rejects_invalid_bounds(source, message):
    with pytest.raises(ScriptError, match=message):
        parse_script(source)
