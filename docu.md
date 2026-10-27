# DHS / .exe Language Reference

This document describes only the DHS/.exe scripting language as implemented by the current parser and runtime. It does not document bot commands, the control panel, setup, repository operations, or legal documents. DHS is a restricted scripting language, **not general Python**. Arbitrary Python execution, imports, object attribute access, and arbitrary function calls are not supported.

## 1. Basic rules

- Keywords, types, and native function names are English.
- Every instruction ends with a semicolon (`;`). Newlines do not replace semicolons.
- Blocks use `{` and `}`; a closing brace needs no semicolon.
- Native Discord functions must start with `@`.
- Variable names start with a letter or underscore, followed by letters, digits, or underscores. Maximum length: 32 characters.
- Single- and double-quoted strings are supported.
- Empty scripts and scripts with no action are rejected.
- Legacy `let` declarations, unprefixed `send(...)`, and compact forms `v(...)`, `m(...)`, `R(...)`, `I(...)`, and `E(...)` are rejected.

```text
var greeting.str = "Hello";
var count.int = 2;
set count = count + 1;
@send(f"{greeting}: {count}");
```

## 2. Variables and types

Declaration: `var NAME.TYPE = VALUE;`

Assignment: `set NAME = EXPRESSION;`

Declare a variable before assigning to it. Assignments are checked against the variable's declared type; `set` does not change that type.

| Type | Meaning and accepted values |
|---|---|
| `str` | Text |
| `int` | Integer; Boolean values do not count as integers for type checking |
| `float` | Integer or floating-point number |
| `bool` | `True` or `False` |
| `list` | List or tuple |
| `dict` | Dictionary |
| `time` | Number or string; no special time arithmetic |
| `user.id` | Discord user/member reference |
| `channel.id` | Discord channel reference |
| `category.id` | Discord category reference |
| `role.id` | Discord role reference |
| `message.id` | Discord message reference |

Discord `.id` types accept a string, integer, or `None`. This does not prove the referenced Discord object exists.

Convenient shorthand declarations are supported when the variable name matches the Discord ID type: `var user.id = None;`, `var channel.id = None;`, `var category.id = None;`, `var role.id = None;`, and `var message.id = None;`. Full declarations such as `var helper_role.role.id = None;` are also supported.

Rules:
- `float` accepts integers.
- `bool` does not accept `0` or `1` as substitutes for Boolean values.
- `list` accepts lists and tuples; `dict` accepts dictionaries.
- `time` accepts numbers or strings, but not Boolean values.
- `None` is accepted for Discord `.id` types.

```text
var username.str = "Alex";
var attempts.int = 3;
var ratio.float = 1.5;
var active.bool = True;
var names.list = ["Alex", "Sam"];
var config.dict = {"mode": "safe", "retries": 3};
var helper_role.role.id = None;
set attempts = attempts + 1;
```

## 3. Literals, collections, and indexing

Supported literals include strings (`"hello"` or `'hello'`), numbers (`12`, `-4`, `2.75`), Booleans (`True`, `False`), `None`, lists (`[1, 2, 3]`), tuples (`(10, 20)`), dictionaries (`{"mode": "safe", "retries": 3}`), and nested dictionaries.

Indexing works on strings, lists, tuples, and dictionaries:

```text
var names.list = ["Alex", "Sam"];
var first.str = names[0];
var config.dict = {"service": {"enabled": True}};
var enabled.bool = config["service"]["enabled"];
```

Collections are limited to 100 items. Keys and indexes must be valid safe expressions; invalid keys or indexes raise an error.

## 4. Operators and logic

- Arithmetic: `+` (addition; also concatenates compatible strings/collections), `-` (subtraction), `*` (multiplication; may repeat strings/lists/tuples), `/` (division), `//` (floor division), `%` (remainder/modulo).
- Unary: `+X`, `-X`, `not X`.
- Boolean: `X and Y` and `X or Y`, with short-circuit evaluation; `not X`.
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`.
- Parentheses group expressions. Chained comparisons are supported by the expression evaluator.

```text
var total.int = 7 + 3;
var remainder.int = 10 % 3;
var equal.bool = total == 10;
var allowed.bool = True and not False;
var condition.bool = (total < 5) or (total >= 10);
```

Expressions support constants, variables, collection literals, indexing, and the operators above. Arbitrary function calls, object.attribute access, imports, lambdas, comprehensions, and arbitrary Python code are not supported.

## 5. Random integers

`randint(MIN, MAX)` returns a random integer including both endpoints:

```text
var roll.int = randint(1, 6);
```

`MIN` must not exceed `MAX`; both bounds must be between -1,000,000,000 and 1,000,000,000. This is a specially supported expression, not permission to call arbitrary functions.

## 6. Formatted strings (f-strings)

Insert variables or supported expressions into text using braces:

```text
var username.str = "Alex";
var score.int = 42;
@send(f"Player {username} has {score} points.");
```

Indexing inside an f-string is supported:

```text
var names.list = ["Alex", "Sam"];
@send(f"First player: {names[0]}");
```

Only `create_role`, `create_category`, and `create_channel` have special support as embedded native calls in f-strings:

```text
@send(f"Role: {@create_role("Helpers", "#5865F2")}");
@send(f"Category: {@create_category("Support")}");
@send(f"Channel: {@create_channel("general")}");
```

This is not general nested function-call support. Embedded call arguments must be quoted strings, integers, or supported role permission flags. Escape inner quotes as needed. Created role/channel/category references can be stored in correctly typed variables. Role and channel IDs inserted into f-strings are formatted as Discord mentions. User-provided input is neutralized to prevent unexpected mentions.

## 7. Conditions

Syntax:

```text
if (mode == "safe") {
    @send("Allowed");
} else {
    @send("Blocked");
}
```

The current `if` header compares one declared variable with one expected value using `==`. General compound conditions in the header are not supported. `elif` is not supported. `else` is optional, must immediately follow the `if` block, and can appear only once. Empty blocks are rejected. Although the expression evaluator supports more comparison and Boolean operators, the `if`-header grammar is narrower.

## 8. Loops

Repeat a fixed count:

```text
repeat(3) {
    @send("Again");
}
```

Repeat with a counter (starts at 1):

```text
repeat 3 as i {
    @send(f"Iteration {i}");
}
```

Numeric range (start inclusive, stop exclusive):

```text
for i in range(0, 3) {
    @send(f"Item {i}");
}
```

Repeat count must be 1 through 10. A range can contain at most 10 iterations; its bounds must be between -1,000,000 and 1,000,000, and `stop` must be greater than `start`. Looping over Discord collections is not supported. Empty loop bodies are rejected. Nested blocks are limited to four levels.

## 9. User input

```text
var username.input{str, "What is your username?"} = "";
@send(f"Hello {username}!");
```

General form: `var NAME.input{TYPE, "QUESTION"} = INITIAL_VALUE;`

Allowed input types: `str`, `int`, `float`, `bool`, `user.id`, `channel.id`, `category.id`, `role.id`, and `message.id`. `list`, `dict`, and `time` are not accepted.

Runtime behavior:
- `INITIAL_VALUE` is currently ignored.
- The reply is stored as plain text regardless of declared type; declaring `int`, `float`, or `bool` does not convert it.
- Input waits for a message from the script author in the same channel.
- The configured script timeout applies.
- Replies over 1,800 characters are rejected.
- `@` is neutralized in replies to prevent user-supplied mentions from pinging.

## 10. Native Discord functions

All native calls start with `@`. Arguments are comma-separated and text arguments should normally be quoted. Argument counts and types are validated; Discord permissions, role hierarchy, and object existence still apply at runtime.

### Messages

| Function | Behavior |
|---|---|
| `@send(MESSAGE)` | Send to the current channel. |
| `@send(MESSAGE, CHANNEL)` | Send to a text channel by ID or exact name. A leading `#` is optional for channel names. |

Examples: `@send("Hello server");` and `@send("Hello general", "#general");`.

### Moderation

| Function | Behavior |
|---|---|
| `@ban(USER, REASON)` | Ban a user; reason is required. |
| `@unban(USER_ID)` or `@unban(USER_ID, REASON)` | Remove a ban. |
| `@kick(USER)` or `@kick(USER, REASON)` | Kick a member. |
| `@timeout(USER, MINUTES)` | Timeout a member for 1 to 40,320 minutes. |
| `@untimeout(USER)` | Remove a timeout. |
| `@mute(USER, MINUTES)` | Alias for `@timeout`. |
| `@unmute(USER)` | Alias for `@untimeout`. |

For moderation targets, use a Discord ID or supported member mention; do not assume display names work.

### Roles

| Function | Behavior |
|---|---|
| `@give_role(USER, ROLE)` | Assign a role. |
| `@add_role(USER, ROLE)` | Alias for `@give_role`. |
| `@remove_role(USER, ROLE)` | Remove a role. |
| `@create_role(NAME)` | Create a role. |
| `@create_role(NAME, COLOR)` | Create a role with a color. |
| `@create_role(NAME, COLOR, PERMISSIONS)` | Create a role with color and optional comma-separated permission allowlist. |
| `@delete_role(ROLE_ID_OR_EXACT_NAME)` | Delete a role by ID or exact name. |

Color must be a six-digit hexadecimal color, e.g. `"#5865F2"`. Administrator and unsupported permissions are rejected. The result of `@create_role` must be assigned to a variable declared as `role.id` to reuse it:

```text
var helper_role.role.id = None;
set helper_role = @create_role("Helpers", "#5865F2");
@give_role("123456789012345678", helper_role);
```

The administrator permission remains forbidden even in embedded calls.

### Channels and categories

| Function | Behavior |
|---|---|
| `@create_category(NAME)` | Create a category. |
| `@create_category(NAME, PERMISSIONS)` | Create a category with permission overwrites. |
| `@create_channel(NAME)` | Create a text channel. |
| `@create_channel(NAME, CATEGORY)` | Create a text channel in an existing category. |
| `@create_channel(NAME, CATEGORY, PERMISSIONS)` | Create a text channel in a category with permission overwrites. |
| `@delete_channel(CHANNEL_ID_OR_EXACT_NAME)` | Delete a text channel by ID or exact name; categories are not accepted. |
| `@slowmode(SECONDS)` | Set slowmode in the current text channel, from 0 to 21,600 seconds. |
| `@clear(COUNT)` | Delete 1 to 100 messages in the current text channel. |

Example of created object references:

```text
var support.category.id = None;
set support = @create_category("Support");
var help_channel.channel.id = None;
set help_channel = @create_channel("help", support);
```

### Permission overwrites

General format:

```text
"@everyone:view_channel=deny, Moderators:send_messages=allow"
```

Targets may be `@everyone`, a role ID, or an exact role name. Permission names must be supported by the runtime; not every Discord permission is accepted.

### Server lists

| Function | Behavior |
|---|---|
| `@guilds_roles()` | List server roles. Takes no arguments. |
| `@guilds_members()` | List up to 100 members; requires Server Members Intent and Discord access. Takes no arguments. |
| `@guilds_channels()` | List server channels, excluding categories. Takes no arguments. |
| `@guilds_categories()` | List server categories. Takes no arguments. |

## 11. Native permissions and restrictions

The caller and bot both need the relevant Discord permission:

- Ban/unban: **Ban Members**
- Kick: **Kick Members**
- Timeout/untimeout: **Moderate Members**
- Give/add/remove/create/delete role: **Manage Roles**
- Create/delete channel/category and slowmode: **Manage Channels**
- Clear messages: **Manage Messages**

The bot's top role must be above roles it assigns or removes. The caller's top role must be above the target role unless they own the server. `@everyone` cannot be assigned or removed this way. Moderation respects Discord role hierarchy. Administrative functions only work inside a server, not in DMs.

## 12. Unsupported syntax and functions

Not implemented as native functions: `@dm`, `@lock`, `@unlock`, `@set_channel`, `@set_role`, `@time`, `@uptime`, and `@random(collection)`. Use `randint(MIN, MAX)` for random integers.

Also unsupported: `let` declarations, native calls without `@`, compact legacy syntax `v(...)`, `m(...)`, `R(...)`, `I(...)`, `E(...)`, `elif`, loops over Discord collections, general nested native calls, arbitrary Python execution, imports, and object attribute access.

## 13. Limits

- Maximum script length: 8,000 characters.
- Runtime action budget: default 1,000 and maximum 1,000 actions.
- Script/input timeout: default 300 seconds and maximum 300 seconds.
- Collection size: maximum 100 items.
- Ordinary text/expression result length: maximum 1,800 characters.
- Expression AST: maximum 256 nodes and nesting depth 32.
- Repeat/range iterations: maximum 10.
- Nested blocks: maximum four levels.
- The action budget counts actions in both conditional branches during validation.

## 14. Complete example

```text
var username.input{str, "What is your name?"} = "";
var greeting.str = "Welcome";
@send(f"{greeting}, {username}!");

var count.int = 3;
repeat(count) {
    @send(f"Message {count}");
}

var status.str = "safe";
if (status == "safe") {
    @send("The status is safe.");
} else {
    @send("The status is not safe.");
}

var created_role.role.id = None;
set created_role = @create_role("Helpers", "#5865F2");
@send(f"Created role: {created_role}");
```

## Runtime safety notes

Expressions are evaluated through an explicit AST allowlist. Native Discord actions can still make real changes and are subject to Discord permissions and role hierarchy. Review scripts before execution and grant the bot only the permissions it needs.
