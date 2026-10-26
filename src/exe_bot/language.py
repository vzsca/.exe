"""Parser for the documented .exe script syntax.

The public entry point accepts only the modern, brace-based syntax and validates
its surface grammar before translating it into internal instructions. Expressions
are evaluated through an explicit AST allowlist; no Python code is executed.
"""

from dataclasses import dataclass
import ast
import re
import random


class ScriptError(ValueError):
    """A user-facing script syntax or validation error."""


@dataclass(frozen=True, slots=True)
class SetVariable:
    name: str
    value: object


@dataclass(frozen=True, slots=True)
class InputVariable:
    name: str
    question: str


@dataclass(frozen=True, slots=True)
class SendMessage:
    text: str
    channel: str | None = None
    role_mentions: bool = False


@dataclass(frozen=True, slots=True)
class DiscordAction:
    name: str
    arguments: tuple[str | int, ...]
    result_variable: str | None = None


@dataclass(frozen=True, slots=True)
class Repeat:
    count: int
    body: tuple["Instruction", ...]


@dataclass(frozen=True, slots=True)
class IfEquals:
    matched: bool
    body: tuple["Instruction", ...]
    else_body: tuple["Instruction", ...] = ()


Instruction = SetVariable | InputVariable | SendMessage | DiscordAction | Repeat | IfEquals
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
    "timeout": (2, 2), "untimeout": (1, 1), "give_role": (2, 2), "remove_role": (2, 2),
    "create_role": (1, 3), "delete_role": (1, 1),
    "create_category": (1, 2), "create_channel": (1, 3), "delete_channel": (1, 1),
    "slowmode": (1, 1), "clear": (1, 1),
    "guilds_roles": (0, 0), "guilds_members": (0, 0),
    "guilds_channels": (0, 0), "guilds_categories": (0, 0),
}
_ACTION_CALL = re.compile(r"^([a-z_]+)\((.*)\)$", re.IGNORECASE)
_MAX_REPEAT = 10
_MAX_DEPTH = 4



_ALLOWED_BINOPS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.FloorDiv: lambda left, right: left // right,
    ast.Mod: lambda left, right: left % right,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: lambda value: +value,
    ast.USub: lambda value: -value,
    ast.Not: lambda value: not value,
}
_ALLOWED_COMPAREOPS = {
    ast.Eq: lambda left, right: left == right,
    ast.NotEq: lambda left, right: left != right,
    ast.Lt: lambda left, right: left < right,
    ast.LtE: lambda left, right: left <= right,
    ast.Gt: lambda left, right: left > right,
    ast.GtE: lambda left, right: left >= right,
}


def _eval_expression(node: ast.AST, variables: dict[str, object]) -> object:
    """Evaluate a deliberately small expression AST; never call eval/exec."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            return node.value
        raise ValueError("unsupported constant")
    if isinstance(node, ast.Name):
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        if node.id not in variables:
            raise ValueError(f"unknown variable '{node.id}'")
        return variables[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_eval_expression(item, variables) for item in node.elts]
        if len(values) > 100:
            raise ValueError("collections are limited to 100 items")
        return values if isinstance(node, ast.List) else tuple(values)
    if isinstance(node, ast.Dict):
        if len(node.keys) > 100:
            raise ValueError("collections are limited to 100 items")
        return {
            _eval_expression(key, variables): _eval_expression(value, variables)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_expression(node.left, variables)
        right = _eval_expression(node.right, variables)
        if isinstance(node.op, ast.Mult) and (
            (isinstance(left, (str, list, tuple)) and isinstance(right, int) and right > 1000)
            or (isinstance(right, (str, list, tuple)) and isinstance(left, int) and left > 1000)
        ):
            raise ValueError("repetition result is too large")
        result = _ALLOWED_BINOPS[type(node.op)](left, right)
        if isinstance(result, (str, list, tuple)) and len(result) > 1800:
            raise ValueError("expression result is too large")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_expression(node.operand, variables))
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        # Preserve Python's short-circuit semantics without evaluating arbitrary code.
        if isinstance(node.op, ast.And):
            result: object = True
            for item in node.values:
                result = _eval_expression(item, variables)
                if not result:
                    return result
            return result
        result = False
        for item in node.values:
            result = _eval_expression(item, variables)
            if result:
                return result
        return result
    if isinstance(node, ast.Compare):
        left = _eval_expression(node.left, variables)
        for operator, comparator in zip(node.ops, node.comparators):
            if type(operator) not in _ALLOWED_COMPAREOPS:
                raise ValueError("unsupported comparison")
            right = _eval_expression(comparator, variables)
            if not _ALLOWED_COMPAREOPS[type(operator)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Subscript):
        value = _eval_expression(node.value, variables)
        index = _eval_expression(node.slice, variables)
        if not isinstance(value, (list, tuple, str, dict)):
            raise ValueError("indexing is only supported for strings, lists, tuples, and dictionaries")
        return value[index]
    raise ValueError("unsupported expression")


def _safe_expression(source: str, variables: dict[str, object]) -> object:
    try:
        parsed = ast.parse(source, mode="eval")
        return _eval_expression(parsed.body, variables)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError, KeyError, IndexError) as exc:
        raise ValueError(str(exc) or "invalid expression") from exc


def _parse_value(source: str, line_number: int, variables: dict[str, object]) -> object:
    source = source.strip()
    random_call = re.fullmatch(r"randint\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", source, re.IGNORECASE)
    if random_call:
        lower, upper = map(int, random_call.groups())
        if lower > upper:
            raise ScriptError(f"Line {line_number}: randint minimum cannot exceed maximum")
        if lower < -1_000_000_000 or upper > 1_000_000_000:
            raise ScriptError(f"Line {line_number}: randint bounds must be between -1000000000 and 1000000000")
        return random.randint(lower, upper)
    if source in {"True", "False", "None"}:
        return {"True": True, "False": False, "None": None}[source]
    if re.fullmatch(_NAME, source):
        if source not in variables:
            raise ScriptError(f"Line {line_number}: unknown variable '{source}'")
        return variables[source]
    try:
        value = _safe_expression(source, variables)
    except ValueError as exc:
        raise ScriptError(f"Line {line_number}: invalid or unsupported expression: {exc}") from exc
    if not isinstance(value, (str, int, float, bool, list, dict, tuple)) and value is not None:
        raise ScriptError(f"Line {line_number}: unsupported value type")
    if isinstance(value, (list, tuple, dict)) and len(value) > 100:
        raise ScriptError(f"Line {line_number}: collections are limited to 100 items")
    if isinstance(value, str) and len(value) > 1800:
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
    variables: dict[str, object],
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
            elif isinstance(instruction, InputVariable):
                variables[instruction.name] = "__EXE_PENDING_INPUT__"
            elif isinstance(instruction, DiscordAction) and instruction.result_variable:
                variables[instruction.result_variable] = f"__EXE_VAR_{instruction.result_variable}__"
    return body

def _split_arguments(source: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    paren_depth = 0
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
        elif quote is None:
            if char == "(":
                paren_depth += 1
            elif char == ")":
                if paren_depth == 0:
                    raise ScriptError("Unexpected closing parenthesis in function arguments")
                paren_depth -= 1
        if char == "," and quote is None and paren_depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if quote:
        raise ScriptError("Unclosed quote in function arguments")
    if paren_depth:
        raise ScriptError("Unclosed parenthesis in function arguments")
    if current or source.strip():
        parts.append("".join(current).strip())
    return parts


def _parse_discord_action(statement: str, line_number: int, variables: dict[str, object]) -> DiscordAction | None:
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
        if isinstance(value, str):
            # Allow bounded repeat variables in quoted action arguments, e.g.
            # create_channel("annonces-{i}") inside "repeat 3 as i: ...".
            value = re.sub(
                r"{([A-Za-z_][A-Za-z0-9_]*)}",
                lambda match: str(variables[match.group(1)]) if match.group(1) in variables else match.group(0),
                value,
            )
        if isinstance(value, str) and len(value) > 1800:
            raise ScriptError(f"Line {line_number}: argument is too long")
        arguments.append(value)
    return DiscordAction(name, tuple(arguments))


def _parse_one(
    statement: str,
    line_number: int,
    variables: dict[str, object],
    depth: int,
) -> list[Instruction]:
    if depth > _MAX_DEPTH:
        raise ScriptError(f"Line {line_number}: repeat nesting exceeds {_MAX_DEPTH} levels")

    action_assignment = re.fullmatch(rf"set\s+({_NAME})\s*=\s*create_role\((.*)\)", statement)
    if action_assignment:
        name, raw_arguments = action_assignment.groups()
        if name not in variables:
            raise ScriptError(f"Line {line_number}: declare '{name}' with a typed variable before assigning a native action result")
        action = _parse_discord_action(f"create_role({raw_arguments})", line_number, variables)
        if action is None:
            raise ScriptError(f"Line {line_number}: invalid create_role assignment")
        return [DiscordAction(action.name, action.arguments, name)]

    match = _SET_STANDARD.fullmatch(statement) or _SET_COMPACT.fullmatch(statement)
    if match:
        name, raw_value = match.groups()
        input_match = re.fullmatch(r"""input\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*\)""", raw_value.strip())
        if input_match:
            question = _parse_value(input_match.group(1), line_number, variables)
            if not isinstance(question, str) or not question:
                raise ScriptError(f"Line {line_number}: input question cannot be empty and must be text")
            return [InputVariable(name, question)]
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

    for_match = re.fullmatch(rf"for\s+({_NAME})\s+in\s+range\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*:\s*(.+)", statement)
    if for_match:
        loop_name, raw_start, raw_stop, body_source = for_match.groups()
        start, stop = int(raw_start), int(raw_stop)
        if abs(start) > 1_000_000 or abs(stop) > 1_000_000:
            raise ScriptError(f"Line {line_number}: range bounds must be between -1000000 and 1000000")
        if stop <= start:
            raise ScriptError(f"Line {line_number}: range stop must be greater than range start")
        if stop - start > _MAX_REPEAT:
            raise ScriptError(f"Line {line_number}: range is limited to {_MAX_REPEAT} iterations")
        expanded: list[Instruction] = []
        original = variables.get(loop_name, None)
        had_original = loop_name in variables
        for loop_value in range(start, stop):
            variables[loop_name] = loop_value
            loop_body = _parse_body(body_source.strip(), line_number, variables, depth + 1)
            if not loop_body:
                raise ScriptError(f"Line {line_number}: for body cannot be empty")
            expanded.extend(loop_body)
        if had_original:
            variables[loop_name] = original
        else:
            variables.pop(loop_name, None)
        return expanded

    loop_match = re.fullmatch(rf"repeat\s+(\d+)\s+as\s+({_NAME})\s*:\s*(.+)", statement)
    if loop_match:
        raw_count, loop_name, body_source = loop_match.groups()
        count = int(raw_count)
        if not 1 <= count <= _MAX_REPEAT:
            raise ScriptError(f"Line {line_number}: repeat count must be between 1 and {_MAX_REPEAT}")
        expanded: list[Instruction] = []
        original = variables.get(loop_name, None)
        had_original = loop_name in variables
        for loop_value in range(1, count + 1):
            variables[loop_name] = loop_value
            loop_body = _parse_body(body_source.strip(), line_number, variables, depth + 1)
            if not loop_body:
                raise ScriptError(f"Line {line_number}: repeat body cannot be empty")
            expanded.extend(loop_body)
        if had_original:
            variables[loop_name] = original
        else:
            variables.pop(loop_name, None)
        return expanded

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

    # Resolve create_role(...) as the second argument without evaluating it as Python.
    # Match the nested call explicitly; the ordinary argument parser only accepts literals.
    role_assignment = re.fullmatch(
        r"(give_role|remove_role)\(\s*(.*?)\s*,\s*(create_role\s*\(.*\))\s*\)",
        statement,
    )
    if role_assignment:
        action_name, raw_member, raw_role = role_assignment.groups()
        member_action = _parse_discord_action(f"unban({raw_member})", line_number, variables)
        if member_action is None:
            raise ScriptError(f"Line {line_number}: invalid member argument")
        created_role = _parse_discord_action(raw_role, line_number, variables)
        if created_role is None or created_role.name != "create_role":
            raise ScriptError(f"Line {line_number}: expected create_role(...) as the role argument")
        result_name = "__exe_result_0"
        return [
            DiscordAction("create_role", created_role.arguments, result_name),
            DiscordAction(action_name, (member_action.arguments[0], f"__EXE_VAR_{result_name}__")),
        ]

    action = _parse_discord_action(statement, line_number, variables)
    if action is not None:
        return [action]

    match = _SEND_STANDARD.fullmatch(statement) or _SEND_COMPACT.fullmatch(statement)
    if match:
        parts = _split_arguments(match.group(1))
        if not 1 <= len(parts) <= 2:
            raise ScriptError(f"Line {line_number}: send expects message text and an optional channel")
        raw_text = parts[0].strip()
        is_f_string = raw_text.startswith('f"') or raw_text.startswith("f'")
        role_mentions = is_f_string and "@" in raw_text
        deferred_actions: list[DiscordAction] = []
        if is_f_string:
            try:
                parsed = ast.parse(raw_text, mode="eval").body
            except SyntaxError as exc:
                raise ScriptError(f"Line {line_number}: invalid f-string") from exc
            if not isinstance(parsed, ast.JoinedStr):
                raise ScriptError(f"Line {line_number}: f must prefix a quoted string")
            chunks: list[str] = []
            for value in parsed.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    chunks.append(value.value)
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
                    if value.value.id not in variables:
                        raise ScriptError(f"Line {line_number}: unknown variable '{value.value.id}' in f-string")
                    current = variables[value.value.id]
                    chunks.append(f"__EXE_VAR_{value.value.id}__" if current == "__EXE_PENDING_INPUT__" else str(current))
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Subscript) and isinstance(value.value.value, ast.Name):
                    variable_name = value.value.value.id
                    if variable_name not in variables:
                        raise ScriptError(f"Line {line_number}: unknown variable '{variable_name}' in f-string")
                    try:
                        index = ast.literal_eval(value.value.slice)
                        chunks.append(str(variables[variable_name][index]))
                    except (ValueError, SyntaxError, KeyError, IndexError, TypeError) as exc:
                        raise ScriptError(f"Line {line_number}: invalid list/dictionary index in f-string") from exc
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Call) and isinstance(value.value.func, ast.Name) and value.value.func.id == "randint":
                    call = value.value
                    if len(call.args) != 2 or call.keywords or not all(isinstance(arg, ast.Constant) and isinstance(arg.value, int) and not isinstance(arg.value, bool) for arg in call.args):
                        raise ScriptError(f"Line {line_number}: randint() in f-strings expects two integer literals")
                    lower, upper = (arg.value for arg in call.args)
                    if lower > upper:
                        raise ScriptError(f"Line {line_number}: randint minimum cannot exceed maximum")
                    if lower < -1_000_000_000 or upper > 1_000_000_000:
                        raise ScriptError(f"Line {line_number}: randint bounds must be between -1000000000 and 1000000000")
                    chunks.append(str(random.randint(lower, upper)))
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Call) and isinstance(value.value.func, ast.Name) and value.value.func.id in {"guilds_roles", "guilds_members", "guilds_channels", "guilds_categories"}:
                    call = value.value
                    if call.args or call.keywords:
                        raise ScriptError(f"Line {line_number}: {call.func.id}() takes no arguments")
                    result_name = f"__exe_result_{len(deferred_actions)}"
                    deferred_actions.append(DiscordAction(call.func.id, (), result_name))
                    chunks.append(f"__EXE_VAR_{result_name}__")
                elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Call) and isinstance(value.value.func, ast.Name) and value.value.func.id == "create_role":
                    call = value.value
                    if not 1 <= len(call.args) <= 3 or call.keywords:
                        raise ScriptError(f"Line {line_number}: create_role in f-strings expects 1 to 3 simple arguments")
                    args = []
                    for arg in call.args:
                        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, (str, int)) or isinstance(arg.value, bool):
                            raise ScriptError(f"Line {line_number}: create_role arguments in f-strings must be quoted text or integers")
                        arg_value = arg.value
                        if isinstance(arg_value, str):
                            arg_value = re.sub(
                                r"{([A-Za-z_][A-Za-z0-9_]*)}",
                                lambda match: str(variables[match.group(1)]) if match.group(1) in variables else match.group(0),
                                arg_value,
                            )
                        args.append(arg_value)
                    result_name = f"__exe_result_{len(deferred_actions)}"
                    deferred_actions.append(DiscordAction("create_role", tuple(args), result_name))
                    chunks.append(f"__EXE_VAR_{result_name}__")
                else:
                    raise ScriptError(f"Line {line_number}: f-strings only support text and defined variables, list/dictionary indexing, and create_role(...)")
            text_value = "".join(chunks)
            if len(text_value) > 1800:
                raise ScriptError(f"Line {line_number}: text is too long (maximum 1800 characters)")
        else:
            text_value = _parse_value(raw_text, line_number, variables)
            if not isinstance(text_value, str):
                raise ScriptError(f"Line {line_number}: send expects text strings")
        channel = None
        if len(parts) == 2:
            channel = str(_parse_value(parts[1], line_number, variables)).strip()
            if not channel:
                raise ScriptError(f"Line {line_number}: target channel cannot be empty")
        return [*deferred_actions, SendMessage(text_value, channel, role_mentions)]

    raise ScriptError(
        f"Line {line_number}: unknown instruction. Use typed declarations such as "
        '"var name.str = \\"text\\";", native calls such as \'@send("text");\', '
        "and brace-based if/else or repeat blocks. See docu.md for supported syntax."
    )


def _block_to_compact(header: str, children: list[str], line_no: int) -> str:
    body = "§".join(children)
    for_match = re.fullmatch(r"for\s+([A-Za-z_][A-Za-z0-9_]{0,31})\s+in\s+range\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", header)
    if for_match:
        loop_name, start, stop = for_match.groups()
        return f"for {loop_name} in range({start}, {stop}): " + body
    repeat_match = re.fullmatch(r"repeat\s+(\d+)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]{0,31}))?", header)
    if repeat_match:
        count, loop_name = repeat_match.groups()
        if loop_name:
            return f"repeat {count} as {loop_name}: " + body
        return "R(" + count + ", " + body + ")"
    if_match = re.fullmatch(rf"if\s+({_NAME})\s*==\s*(.+)", header)
    if if_match:
        return "I(" + if_match.group(1) + ", " + if_match.group(2) + ", " + body + ")"
    if header == "else":
        return "E(" + body + ")"
    raise ScriptError(f"Line {line_no}: unsupported indented block")


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
                re.fullmatch(r"repeat\s+\d+(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]{0,31})?\s*:", text)
                or re.fullmatch(rf"for\s+{_NAME}\s+in\s+range\(\s*-?\d+\s*,\s*-?\d+\s*\)\s*:", text)
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
                result.append(_block_to_compact(text[:-1].rstrip(), children, line_no))
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
    # If there are no indented lines, still reject a block header whose next
    # instruction is at the same indentation level.
    if not any(indent > parsed_lines[0][0] for indent, _, _ in parsed_lines):
        for position, (indent, text, line_no) in enumerate(parsed_lines):
            is_block = text.endswith(":") and (
                re.fullmatch(r"repeat\s+\d+(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]{0,31})?\s*:", text)
                or re.fullmatch(rf"for\s+{_NAME}\s+in\s+range\(\s*-?\d+\s*,\s*-?\d+\s*\)\s*:", text)
                or re.fullmatch(rf"if\s+{_NAME}\s*==\s*.+:", text)
                or text == "else:"
            )
            if is_block and (
                position + 1 >= len(parsed_lines)
                or parsed_lines[position + 1][0] <= indent
            ):
                raise ScriptError(f"Line {line_no}: block body cannot be empty")
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
            re.fullmatch(r"repeat\s+\d+(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]{0,31})?\s*:", text)
            or re.fullmatch(rf"for\s+{_NAME}\s+in\s+range\(\s*-?\d+\s*,\s*-?\d+\s*\)\s*:", text)
            or re.fullmatch(rf"if\s+{_NAME}\s*==\s*.+:", text)
            or text == "else:"
        ):
            if index + 1 >= len(parsed_lines) or parsed_lines[index + 1][0] <= indent:
                raise ScriptError(f"Line {line_no}: block body cannot be empty")
            children, index = parse_level(index + 1, indent)
            if not children:
                raise ScriptError(f"Line {line_no}: block body cannot be empty")
            output.append(_block_to_compact(text[:-1].rstrip(), children, line_no))
        else:
            output.append(text)
            index += 1
    return "\n".join(output)



_TYPE_NAMES = ("user.id", "channel.id", "category.id", "role.id", "message.id", "str", "int", "float", "bool", "list", "dict", "time")

def _value_matches_type(value: object, type_name: str) -> bool:
    """Check runtime values against the declared .exe variable type."""
    if value is None:
        return type_name.endswith(".id")
    if type_name == "str":
        return isinstance(value, str)
    if type_name.endswith(".id"):
        return (isinstance(value, (str, int)) and not isinstance(value, bool))
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, (list, tuple))
    if type_name == "dict":
        return isinstance(value, dict)
    if type_name == "time":
        return isinstance(value, (int, float, str)) and not isinstance(value, bool)
    return False
_NATIVE_ALIASES = {
    "mute": "timeout",
    "unmute": "untimeout",
    "add_role": "give_role",
    "remove_role": "remove_role",
}


def _normalize_modern_syntax(source: str) -> str:
    """Translate the agreed English, brace-based surface syntax to the legacy AST parser.

    This is a compatibility layer, not Python evaluation. Expressions and function names
    are still validated by the existing allowlist after normalization.
    """
    # First scan the source to turn top-level semicolons and braces into statement
    # boundaries while leaving quoted strings (including f-strings) untouched.
    lines: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    depth_paren = 0
    indent = 0
    input_brace = False
    literal_brace_depth = 0
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
            current.append(char)
            continue
        if quote is None:
            if char == "(":
                depth_paren += 1
            elif char == ")":
                depth_paren = max(0, depth_paren - 1)
            if depth_paren == 0 and char == "{" and "".join(current).strip().endswith(".input"):
                current.append(char)
                input_brace = True
                continue
            if depth_paren == 0 and char == "}" and input_brace:
                current.append(char)
                input_brace = False
                continue
            if depth_paren == 0 and char == "{" and literal_brace_depth:
                literal_brace_depth += 1
                current.append(char)
                continue
            if depth_paren == 0 and char == "}" and literal_brace_depth:
                literal_brace_depth -= 1
                current.append(char)
                continue
            if depth_paren == 0 and char == "{":
                header = "".join(current).strip()
                is_block_header = bool(
                    re.match(r"^(?:if|elif|else|repeat|for)\b", header)
                )
                if not is_block_header:
                    current.append(char)
                    literal_brace_depth = 1
                    continue
                current = []
                if not header:
                    raise ScriptError("Unexpected opening brace")
                header = re.sub(r"^if\s*\((.*)\)\s*$", r"if \1", header)
                header = re.sub(r"^elif\s*\((.*)\)\s*$", r"elif \1", header)
                header = re.sub(r"^else\s*$", "else", header)
                header = re.sub(r"^repeat\s*\((.*)\)\s*$", r"repeat \1", header)
                header = re.sub(r"^for\s+(.+?)\s+in\s+(.+?)\s*$", r"for \1 in \2", header)
                lines.append("    " * indent + header + ":")
                indent += 1
                continue
            if depth_paren == 0 and char == "}":
                part = "".join(current).strip()
                if part:
                    lines.append("    " * indent + part)
                    current = []
                if indent == 0:
                    raise ScriptError("Unexpected closing brace")
                indent -= 1
                continue
            if depth_paren == 0 and char == ";":
                part = "".join(current).strip()
                if part:
                    lines.append("    " * indent + part)
                current = []
                continue
            if char == "\n":
                part = "".join(current).strip()
                if part:
                    lines.append("    " * indent + part)
                current = []
                continue
        current.append(char)
    part = "".join(current).strip()
    if part:
        lines.append("    " * indent + part)
    if indent:
        raise ScriptError("Unclosed block brace")

    normalized: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Typed declarations become the existing variable instruction form.
        decl = re.fullmatch(r"var\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_.]+)\s*=\s*(.+)", stripped)
        if decl:
            name, type_name, value = decl.groups()
            if type_name not in _TYPE_NAMES:
                raise ScriptError(f"Unknown variable type '{type_name}'")
            stripped = f"let {name} = {value}"
        else:
            input_decl = re.fullmatch(
                r"""var\s+([A-Za-z_][A-Za-z0-9_]*)\.input\{([A-Za-z_.]+)\s*,\s*("(?:[^"\\\\]|\\\\.)*"|'(?:[^'\\\\]|\\\\.)*')\}\s*=\s*(.+)""",
                stripped,
            )
            if input_decl:
                name, type_name, question, _initial = input_decl.groups()
                if type_name not in _TYPE_NAMES or type_name in {"list", "dict", "time"}:
                    raise ScriptError(f"Unsupported input type '{type_name}'")
                stripped = f"let {name} = input({question})"
            else:
                assign = re.fullmatch(r"set\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", stripped)
                if assign and not re.fullmatch(r"@?create_role\s*\(.*\)", assign.group(2).strip()):
                    stripped = f"let {assign.group(1)} = {assign.group(2)}"

        # Native calls require @ in the new syntax; the runtime registry remains allowlisted.
        stripped = re.sub(r"(?<![\w@])@([A-Za-z_][A-Za-z0-9_]*)\s*\(", r"\1(", stripped)
        for old_name, new_name in _NATIVE_ALIASES.items():
            stripped = re.sub(rf"\b{re.escape(old_name)}\s*\(", f"{new_name}(", stripped)
        # The legacy engine uses timeout(minutes) for mute(duration).
        normalized.append(" " * (len(line) - len(line.lstrip())) + stripped)
    return "\n".join(normalized)


def _validate_modern_surface_syntax(source: str) -> None:
    """Validate statement terminators and reject legacy syntax before normalization."""
    legacy_patterns = (
        (r"(?<![\w@])\blet\s+", "Legacy 'let' declarations are not supported; use 'var name.type = value;'"),
        (r"(?<![\w@])\bv\s*\(", "Compact syntax v(...) is not supported."),
        (r"(?<![\w@])\bm\s*\(", "Compact syntax m(...) is not supported."),
        (r"(?<![\w@])\bR\s*\(", "Compact syntax R(...) is not supported."),
        (r"(?<![\w@])\bI\s*\(", "Compact syntax I(...) is not supported."),
        (r"(?<![\w@])\bE\s*\(", "Compact syntax E(...) is not supported."),
        (r"(?<![@\w])send\s*\(", "Native functions must start with @, for example '@send(...);'"),
        (r"(?<![@\w])(?:ban|unban|kick|timeout|untimeout|give_role|remove_role|create_role|delete_role|create_category|create_channel|delete_channel|slowmode|clear|dm|lock|unlock|set_channel|set_role)\s*\(", "Native functions must start with '@'."),
    )
    # Do not scan inside quoted strings: examples and message text may contain
    # words that look like old syntax.
    visible: list[str] = []
    quote: str | None = None
    escaped = False
    for char in source:
        if quote:
            visible.append(" ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
            visible.append(" ")
        else:
            visible.append(char)
    surface = "".join(visible)
    for pattern, message in legacy_patterns:
        if re.search(pattern, surface):
            raise ScriptError(message)

    quote = None
    escaped = False
    paren_depth = 0
    block_depth = 0
    literal_brace_depth = 0
    statement: list[str] = []
    line_number = 1
    statement_line = 1
    input_brace = False
    for char in source:
        if escaped:
            statement.append(char)
            escaped = False
            if char == "\n":
                line_number += 1
            continue
        if quote:
            statement.append(char)
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            if char == "\n":
                line_number += 1
            continue
        if char in ("'", '"'):
            quote = char
            statement.append(char)
        elif char == "(":
            paren_depth += 1
            statement.append(char)
        elif char == ")":
            if paren_depth == 0:
                raise ScriptError(f"Line {line_number}: unexpected closing parenthesis")
            paren_depth -= 1
            statement.append(char)
        elif char == "\n":
            if literal_brace_depth:
                statement.append(char)
            elif not "".join(statement).strip():
                statement = []
                statement_line = line_number + 1
            elif paren_depth == 0:
                raise ScriptError(
                    f"Line {statement_line}: every instruction must end with ';' before a newline"
                )
            else:
                statement.append(char)
            line_number += 1
        elif char == "{" and paren_depth == 0:
            prefix = "".join(statement).strip()
            if re.fullmatch(r"var\s+[A-Za-z_]\w*\.input", prefix):
                input_brace = True
                statement.append(char)
            elif input_brace:
                statement.append(char)
            elif literal_brace_depth:
                literal_brace_depth += 1
                statement.append(char)
            elif re.match(r"^(?:if|elif|else|repeat|for)\b", prefix):
                statement = []
                block_depth += 1
                statement_line = line_number
            else:
                # A non-block brace starts a dictionary literal; the safe expression
                # evaluator validates its contents after normalization.
                literal_brace_depth = 1
                statement.append(char)
        elif char == "}" and paren_depth == 0:
            if input_brace:
                input_brace = False
                statement.append(char)
            elif literal_brace_depth:
                literal_brace_depth -= 1
                statement.append(char)
            else:
                if "".join(statement).strip():
                    raise ScriptError(
                        f"Line {statement_line}: every instruction inside a block must end with ';'"
                    )
                if block_depth == 0:
                    raise ScriptError(f"Line {line_number}: unexpected closing brace")
                block_depth -= 1
                statement = []
                statement_line = line_number
        elif char == ";" and paren_depth == 0 and literal_brace_depth == 0:
            if not "".join(statement).strip():
                raise ScriptError(f"Line {line_number}: empty instruction")
            statement = []
            statement_line = line_number
        else:
            statement.append(char)
    if quote:
        raise ScriptError("Unclosed quote in script")
    if paren_depth:
        raise ScriptError("Unclosed parenthesis in script")
    if "".join(statement).strip():
        raise ScriptError(f"Line {statement_line}: every instruction must end with ';'")
    if block_depth:
        raise ScriptError("Unclosed block brace")

def parse_script(source: str, *, max_actions: int = 20) -> list[Instruction]:
    """Parse modern brace-based syntax with mandatory statement semicolons."""
    if len(source) > 8000:
        raise ScriptError("Script is too long (maximum 8000 characters)")
    _validate_modern_surface_syntax(source)
    declared_source = source
    source = _normalize_modern_syntax(source)
    source = _normalize_indented_blocks(source)
    statements = _split_statements(source)
    if not statements:
        raise ScriptError("Script is empty")

    variables: dict[str, object] = {}
    instructions: list[Instruction] = []
    declared_types: dict[str, str] = {}
    for declaration in re.finditer(r"var\s+([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_.]+)\s*=", declared_source):
        declared_types[declaration.group(1)] = declaration.group(2)
    for declaration in re.finditer(r"var\s+([A-Za-z_][A-Za-z0-9_]*)\.input\{([A-Za-z_.]+)\s*,", declared_source):
        declared_types[declaration.group(1)] = declaration.group(2)
    def validate_declared_types(instruction: Instruction, line_number: int) -> None:
        if isinstance(instruction, DiscordAction) and instruction.result_variable and not instruction.result_variable.startswith("__exe_result_"):
            declared_type = declared_types.get(instruction.result_variable)
            if declared_type != "role.id":
                raise ScriptError(
                    f"Line {line_number}: the result of create_role must be assigned to a variable declared as 'role.id'"
                )
        elif isinstance(instruction, SetVariable) and instruction.name in declared_types:
            declared_type = declared_types[instruction.name]
            if declared_type not in _TYPE_NAMES or not _value_matches_type(instruction.value, declared_type):
                raise ScriptError(
                    f"Line {line_number}: value assigned to '{instruction.name}' "
                    f"does not match declared type '{declared_type}'"
                )
        elif isinstance(instruction, Repeat):
            for nested in instruction.body:
                validate_declared_types(nested, line_number)
        elif isinstance(instruction, IfEquals):
            for nested in (*instruction.body, *instruction.else_body):
                validate_declared_types(nested, line_number)

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
            validate_declared_types(instruction, line_number)
            instructions.append(instruction)
            if isinstance(instruction, SetVariable):
                variables[instruction.name] = instruction.value
            elif isinstance(instruction, InputVariable):
                variables[instruction.name] = "__EXE_PENDING_INPUT__"
            elif isinstance(instruction, DiscordAction) and instruction.result_variable:
                variables[instruction.result_variable] = f"__EXE_VAR_{instruction.result_variable}__"

    action_budget = sum(_count_actions(instruction) for instruction in instructions)
    if action_budget > max_actions:
        raise ScriptError(f"Script exceeds the limit of {max_actions} actions")

    if not any(not isinstance(item, (SetVariable, InputVariable)) for item in instructions):
        raise ScriptError("Script has no actions")
    return instructions


def _count_actions(instruction: Instruction) -> int:
    if isinstance(instruction, (SendMessage, DiscordAction)):
        return 1
    if isinstance(instruction, (SetVariable, InputVariable)):
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
            if isinstance(item, (SendMessage, DiscordAction, InputVariable)):
                actions.append(item)
            elif isinstance(item, Repeat):
                for _ in range(item.count):
                    expand(item.body)
            elif isinstance(item, IfEquals):
                expand(item.body if item.matched else item.else_body)
            # Variables and conditions are resolved by the parser before execution.

    expand(instructions)
    return actions
