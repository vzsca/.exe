"""Safe parser for the first .exe language features.

The standard and compact forms are parsed separately and produce the same
internal instructions. No Python code is evaluated or executed.
"""

from dataclasses import dataclass
import ast
import re


class ScriptError(ValueError):
    """A user-facing script syntax or validation error."""


@dataclass(frozen=True, slots=True)
class SetVariable:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class SendMessage:
    text: str


@dataclass(frozen=True, slots=True)
class DiscordAction:
    name: str
    arguments: tuple[str | int, ...]


@dataclass(frozen=True, slots=True)
class Repeat:
    count: int
    body: tuple["Instruction", ...]


@dataclass(frozen=True, slots=True)
class IfEquals:
    matched: bool
    body: tuple["Instruction", ...]
    else_body: tuple["Instruction", ...] = ()


Instruction = SetVariable | SendMessage | DiscordAction | Repeat | IfEquals
_NAME = r"[A-Za-z_][A-Za-z0-9_]{0,31}"
_SET_STANDARD = re.compile(rf"^let\s+({_NAME})\s*=\s*(.+)$")
_SET_COMPACT = re.compile(rf"^v\(\s*({_NAME})\s*,\s*(.+)\s*\)$")
_SEND_STANDARD = re.compile(r"^send\((.*)\)$")
_SEND_COMPACT = re.compile(r"^m\((.*)\)$")
_REPEAT_STANDARD = re.compile(r"^repeat\s+(\d+)\s*:\s*(.+)$")
_REPEAT_COMPACT = re.compile(r"^R\(\s*(\d+)\s*,\s*(.+)\s*\)$")
_IF_STANDARD = re.compile(rf"^if\s+({_NAME})\s*==\s*(.+?)\s*:\s*(.+)$")
_IF_COMPACT = re.compile(rf"^I\(\s*({_NAME})\s*,\s*(.+?)\s*,\s*(.+)\s*\)$")
_ELSE_STANDARD = re.compile(r"^else\s*:\s*(.+)$")
_ELSE_COMPACT = re.compile(r"^E\(\s*(.+)\s*\)$")
_DISCORD_ACTIONS = {
    "ban": (2, 2), "unban": (1, 2), "kick": (1, 2),
    "timeout": (2, 2), "untimeout": (1, 1),
    "create_role": (1, 3), "delete_role": (1, 1),
    "create_category": (1, 2), "create_channel": (1, 3), "delete_channel": (1, 1),
    "slowmode": (1, 1), "clear": (1, 1),
}
_ACTION_CALL = re.compile(r"^([a-z_]+)\((.*)\)$", re.IGNORECASE)
_MAX_REPEAT = 10
_MAX_DEPTH = 4


def _parse_value(source: str, line_number: int, variables: dict[str, str]) -> str:
    source = source.strip()
    if re.fullmatch(_NAME, source):
        if source not in variables:
            raise ScriptError(f"Line {line_number}: unknown variable '{source}'")
        return variables[source]
    try:
        value = ast.literal_eval(source)
    except (ValueError, SyntaxError) as exc:
        raise ScriptError(
            f"Line {line_number}: expected quoted text or a defined variable"
        ) from exc
    if not isinstance(value, str):
        raise ScriptError(f"Line {line_number}: values must be text strings")
    if len(value) > 1800:
        raise ScriptError(f"Line {line_number}: text is too long (maximum 1800 characters)")
    return value


def _split_statements(source: str) -> list[tuple[int, str]]:
    """Split instructions on top-level newlines, semicolons, or § separators."""
    statements: list[tuple[int, str]] = []
    quote: str | None = None
    escaped = False
    paren_depth = 0
    current: list[str] = []
    statement_line = 1

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        if not current:
            statement_line = line_number
        for char in raw_line:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == "\\" and quote:
                current.append(char)
                escaped = True
                continue
            if char in ("'", '"'):
                if quote is None:
                    quote = char
                elif quote == char:
                    quote = None
            elif quote is None:
                if char == "(":
                    paren_depth += 1
                elif char == ")":
                    if paren_depth == 0:
                        raise ScriptError("Unexpected closing parenthesis in script")
                    paren_depth -= 1

            if char in (";", "§") and quote is None and paren_depth == 0:
                part = "".join(current).strip()
                if part and not part.startswith("#"):
                    statements.append((statement_line, part))
                current = []
                statement_line = line_number
            else:
                current.append(char)

        if quote is None and paren_depth == 0:
            part = "".join(current).strip()
            if part and not part.startswith("#"):
                statements.append((statement_line, part))
            current = []
        else:
            current.append("\n")

    part = "".join(current).strip()
    if part and not part.startswith("#"):
        statements.append((statement_line, part))
    if quote is not None:
        raise ScriptError("Unclosed quote in script")
    if paren_depth != 0:
        raise ScriptError("Unclosed parenthesis in script")
    return statements


def _parse_body(
    source: str,
    line_number: int,
    variables: dict[str, str],
    depth: int,
) -> list[Instruction]:
    """Parse multiple nested instructions while sharing the current variables."""
    statements = _split_statements(source)
    body: list[Instruction] = []
    for _, statement in statements:
        parsed = _parse_one(statement, line_number, variables, depth)
        body.extend(parsed)
        for instruction in parsed:
            if isinstance(instruction, SetVariable):
                variables[instruction.name] = instruction.value
    return body

def _split_arguments(source: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in source:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and quote:
            current.append(char)
            escaped = True
            continue
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        if char == "," and quote is None:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if quote:
        raise ScriptError("Unclosed quote in function arguments")
    if current or source.strip():
        parts.append("".join(current).strip())
    return parts


def _parse_discord_action(statement: str, line_number: int, variables: dict[str, str]) -> DiscordAction | None:
    match = _ACTION_CALL.fullmatch(statement)
    if not match:
        return None
    name, raw_arguments = match.groups()
    name = name.lower()
    if name not in _DISCORD_ACTIONS:
        return None
    parts = _split_arguments(raw_arguments)
    minimum, maximum = _DISCORD_ACTIONS[name]
    if not minimum <= len(parts) <= maximum:
        raise ScriptError(f"Line {line_number}: {name} expects {minimum}" +
                          (f" to {maximum}" if maximum != minimum else "") + " argument(s)")
    arguments: list[str | int] = []
    for part in parts:
        if re.fullmatch(r"\d+", part):
            value: str | int = int(part)
        elif re.fullmatch(_NAME, part) and part in variables:
            value = variables[part]
        else:
            try:
                value = ast.literal_eval(part)
            except (ValueError, SyntaxError) as exc:
                raise ScriptError(f"Line {line_number}: arguments must be quoted text, integers, or defined variables") from exc
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ScriptError(f"Line {line_number}: unsupported function argument")
        if isinstance(value, str) and len(value) > 1800:
            raise ScriptError(f"Line {line_number}: argument is too long")
        arguments.append(value)
    return DiscordAction(name, tuple(arguments))


def _parse_one(
    statement: str,
    line_number: int,
    variables: dict[str, str],
    depth: int,
) -> list[Instruction]:
    if depth > _MAX_DEPTH:
        raise ScriptError(f"Line {line_number}: repeat nesting exceeds {_MAX_DEPTH} levels")

    match = _SET_STANDARD.fullmatch(statement) or _SET_COMPACT.fullmatch(statement)
    if match:
        name, raw_value = match.groups()
        return [SetVariable(name, _parse_value(raw_value, line_number, variables))]

    match = _IF_STANDARD.fullmatch(statement) or _IF_COMPACT.fullmatch(statement)
    if match:
        variable_name, raw_expected, body_source = match.groups()
        if variable_name not in variables:
            raise ScriptError(f"Line {line_number}: unknown variable '{variable_name}'")
        expected = _parse_value(raw_expected, line_number, variables)
        body = _parse_body(body_source.strip(), line_number, variables, depth + 1)
        if not body:
            raise ScriptError(f"Line {line_number}: if body cannot be empty")
        return [IfEquals(variables[variable_name] == expected, tuple(body))]

    match = _REPEAT_STANDARD.fullmatch(statement) or _REPEAT_COMPACT.fullmatch(statement)
    if match:
        raw_count, body_source = match.groups()
        count = int(raw_count)
        if not 1 <= count <= _MAX_REPEAT:
            raise ScriptError(f"Line {line_number}: repeat count must be between 1 and {_MAX_REPEAT}")
        body = _parse_body(body_source.strip(), line_number, variables, depth + 1)
        if not body:
            raise ScriptError(f"Line {line_number}: repeat body cannot be empty")
        return [Repeat(count, tuple(body))]

    action = _parse_discord_action(statement, line_number, variables)
    if action is not None:
        return [action]

    match = _SEND_STANDARD.fullmatch(statement) or _SEND_COMPACT.fullmatch(statement)
    if match:
        return [SendMessage(_parse_value(match.group(1), line_number, variables))]

    raise ScriptError(
        f"Line {line_number}: unknown instruction. Try let name = \"text\", "
        "send(\"text\"), if name == \"text\": send(\"yes\"), repeat 3: send(\"text\"), "
        "or compact v(...), m(...), I(...), E(...), R(...)."
    )


def _normalize_indented_blocks(source: str) -> str:
    """Convert indentation-based repeat/if/else blocks to the existing safe inline grammar."""
    lines = source.expandtabs(4).splitlines()
    parsed_lines: list[tuple[int, str, int]] = []
    for number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if raw[:indent].strip():
            raise ScriptError(f"Line {number}: indentation must use spaces")
        parsed_lines.append((indent, stripped, number))

    def parse_level(index: int, parent_indent: int) -> tuple[list[str], int]:
        result: list[str] = []
        while index < len(parsed_lines):
            indent, text, line_no = parsed_lines[index]
            if indent <= parent_indent:
                break
            if indent < parent_indent:
                break
            is_block = text.endswith(":") and (
                re.fullmatch(r"repeat\s+\d+\s*:", text)
                or re.fullmatch(rf"if\s+{_NAME}\s*==\s*.+:", text)
                or text == "else:"
            )
            if is_block:
                if index + 1 >= len(parsed_lines) or parsed_lines[index + 1][0] <= indent:
                    raise ScriptError(f"Line {line_no}: block body cannot be empty")
                child_indent = parsed_lines[index + 1][0]
                children, next_index = parse_level(index + 1, indent)
                if not children:
                    raise ScriptError(f"Line {line_no}: block body cannot be empty")
                result.append(text[:-1].rstrip() + ": " + "§".join(children))
                index = next_index
            else:
                if indent > parent_indent and result and parsed_lines[index - 1][0] < indent:
                    # A deeper indentation is only valid as the body of a block.
                    previous = parsed_lines[index - 1][1]
                    if not previous.endswith(":"):
                        raise ScriptError(f"Line {line_no}: unexpected indentation")
                result.append(text)
                index += 1
        return result, index

    if not parsed_lines:
        return source
    # At top level, the first line may have no indentation; all top-level lines
    # must share that indentation to avoid silently accepting malformed blocks.
    base_indent = parsed_lines[0][0]
    output: list[str] = []
    index = 0
    while index < len(parsed_lines):
        indent, text, line_no = parsed_lines[index]
        if indent != base_indent:
            raise ScriptError(f"Line {line_no}: unexpected indentation")
        if text.endswith(":") and (
            re.fullmatch(r"repeat\s+\d+\s*:", text)
            or re.fullmatch(rf"if\s+{_NAME}\s*==\s*.+:", text)
            or text == "else:"
        ):
            if index + 1 >= len(parsed_lines) or parsed_lines[index + 1][0] <= indent:
                raise ScriptError(f"Line {line_no}: block body cannot be empty")
            children, index = parse_level(index + 1, indent)
            if not children:
                raise ScriptError(f"Line {line_no}: block body cannot be empty")
            output.append(text[:-1].rstrip() + ": " + "§".join(children))
        else:
            output.append(text)
            index += 1
    return "\n".join(output)


def parse_script(source: str, *, max_actions: int = 20) -> list[Instruction]:
    """Parse standard and compact syntax to shared, validated instructions."""
    if len(source) > 8000:
        raise ScriptError("Script is too long (maximum 8000 characters)")

    statements = _split_statements(source)
    if not statements:
        raise ScriptError("Script is empty")

    variables: dict[str, str] = {}
    instructions: list[Instruction] = []
    for line_number, statement in statements:
        else_match = _ELSE_STANDARD.fullmatch(statement) or _ELSE_COMPACT.fullmatch(statement)
        if else_match:
            if not instructions or not isinstance(instructions[-1], IfEquals):
                raise ScriptError(f"Line {line_number}: else must immediately follow an if condition")
            previous = instructions[-1]
            if previous.else_body:
                raise ScriptError(f"Line {line_number}: an if condition can only have one else")
            else_body = _parse_one(else_match.group(1).strip(), line_number, variables, 1)
            instructions[-1] = IfEquals(previous.matched, previous.body, tuple(else_body))
            continue

        parsed = _parse_one(statement, line_number, variables, 0)
        for instruction in parsed:
            instructions.append(instruction)
            if isinstance(instruction, SetVariable):
                variables[instruction.name] = instruction.value

    action_budget = sum(_count_actions(instruction) for instruction in instructions)
    if action_budget > max_actions:
        raise ScriptError(f"Script exceeds the limit of {max_actions} actions")

    if not any(not isinstance(item, SetVariable) for item in instructions):
        raise ScriptError("Script has no actions")
    return instructions


def _count_actions(instruction: Instruction) -> int:
    if isinstance(instruction, (SendMessage, DiscordAction)):
        return 1
    if isinstance(instruction, SetVariable):
        return 0
    if isinstance(instruction, IfEquals):
        # Count both branches so conditionals cannot bypass the action budget.
        return sum(_count_actions(item) for item in instruction.body) + sum(
            _count_actions(item) for item in instruction.else_body
        )
    return instruction.count * sum(_count_actions(item) for item in instruction.body)


def expand_actions(instructions: list[Instruction]) -> list[SendMessage | DiscordAction]:
    """Expand bounded repeats into the shared list of executable Discord actions."""
    actions: list[SendMessage | DiscordAction] = []

    def expand(items: tuple[Instruction, ...] | list[Instruction]) -> None:
        for item in items:
            if isinstance(item, (SendMessage, DiscordAction)):
                actions.append(item)
            elif isinstance(item, Repeat):
                for _ in range(item.count):
                    expand(item.body)
            elif isinstance(item, IfEquals):
                expand(item.body if item.matched else item.else_body)
            # Variables and conditions are resolved by the parser before execution.

    expand(instructions)
    return actions
