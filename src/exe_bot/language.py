"""Tiny safe language front-end; no Python evaluation or arbitrary function calls.

Initial syntax:
  Standard: send("Hello")
  Compact:  m("Hello")

Both forms produce the same SendMessage action. This grammar intentionally starts
small; variables, conditions, loops and Discord administration actions are future work.
"""

from dataclasses import dataclass
import ast
import re


class ScriptError(ValueError):
    """A user-facing script syntax or validation error."""


@dataclass(frozen=True, slots=True)
class SendMessage:
    text: str


Action = SendMessage
_STANDARD = re.compile(r"^send\((.*)\)$")
_COMPACT = re.compile(r"^m\((.*)\)$")


def _parse_string_argument(source: str, line_number: int) -> str:
    try:
        value = ast.literal_eval(source.strip())
    except (ValueError, SyntaxError) as exc:
        raise ScriptError(f"Line {line_number}: expected a quoted text string, e.g. send(\"Hello\")") from exc
    if not isinstance(value, str):
        raise ScriptError(f"Line {line_number}: the message argument must be a string")
    if len(value) > 1800:
        raise ScriptError(f"Line {line_number}: message is too long (maximum 1800 characters)")
    return value


def parse_script(source: str, *, max_actions: int = 20) -> list[Action]:
    """Parse the supported standard/compact forms into a common action list."""
    if len(source) > 8000:
        raise ScriptError("Script is too long (maximum 8000 characters)")

    actions: list[Action] = []
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _STANDARD.fullmatch(line)
        if match is None:
            match = _COMPACT.fullmatch(line)
        if match is None:
            raise ScriptError(
                f"Line {line_number}: unknown instruction. Use send(\"text\") or compact m(\"text\")."
            )

        actions.append(SendMessage(_parse_string_argument(match.group(1), line_number)))
        if len(actions) > max_actions:
            raise ScriptError(f"Script exceeds the limit of {max_actions} actions")

    if not actions:
        raise ScriptError("Script is empty")
    return actions
