# .exe Language Reference

This document describes the syntax and behavior implemented by the current parser and Discord runtime. It is a reference to the current implementation, not a promise of future features.

## Syntax rules

- Keywords, types, and native function names are English.
- Every instruction must end with a semicolon (;).
- Newlines are optional after a semicolon.
- Blocks use braces ({ and }) and do not need a trailing semicolon.
- Native Discord calls must be prefixed with @.
- Legacy syntax such as let, unprefixed send(...), and compact v(), m(), R(), I(), or E() forms is rejected.
- Scripts cannot execute arbitrary Python code.

Example:

    var greeting.str = "Hello";
    var count.int = 2;
    set count = count + 1;
    @send(f"{greeting}: {count}");

## Variables and expressions

Declare a variable with var name.type = value; and update it with set name = expression;.

Supported declared types:

str, int, float, bool, list, dict, time, user.id, channel.id, category.id, role.id, and message.id.

Type checks apply to declarations and assignments. float also accepts integers; list accepts lists and tuples; dict accepts dictionaries; time accepts numbers and strings. The .id types accept strings, integers, or None for an unset reference. An .id type does not prove that the referenced Discord object exists.

Safe expressions support constants, variables, list/tuple/dictionary literals, indexing, arithmetic (+, -, *, /, //, %), Boolean operations (and, or, not), and comparisons (==, !=, <, <=, >, >=). Arbitrary function calls and Python attribute access are not allowed. Collections are limited to 100 items.

Dictionary example:

    var config.dict = {"mode": "safe", "retries": 3};
    var mode.str = config["mode"];
    var enabled.bool = config["nested"]["enabled"];

Nested dictionaries and indexing are supported. Dictionary keys and values must still be valid safe expressions.

Boolean literals are True and False; the empty value is None. randint(min, max) returns a bounded random integer. Its minimum cannot exceed its maximum, and bounds must stay between -1,000,000,000 and 1,000,000,000.

## Conditions and loops

An if condition currently compares one declared variable with one expected value. An optional else block is supported:

    var mode.str = "safe";
    if (mode == "safe") {
        @send("allowed");
    } else {
        @send("blocked");
    }

General compound expressions are not supported in block conditions. elif and loops over Discord collections are not supported.

Repeat a block a fixed number of times:

    repeat(3) {
        @send("again");
    }

Iterate over a numeric range (the stop value is exclusive):

    for i in range(0, 3) {
        @send(f"item {i}");
    }

Repeat counts and ranges are limited to 10 iterations. Range bounds must be between -1,000,000 and 1,000,000, and the stop value must be greater than the start value. Nested blocks are limited to four levels. The action budget is checked before execution.

## User input

    var username.input{str, "What is your username?"} = "";
    @send(f"Hello {username}!");

Input declarations accept str, int, float, bool, and the .id types. list, dict, and time are not accepted for input. The initial value is currently ignored: the reply is stored as plain text regardless of the declared type. Input waits for a message from the script author in the same channel and uses the configured script timeout. Replies over 1,800 characters are rejected, and @ is neutralized to prevent user-supplied mentions from pinging.

## Native Discord actions

Native calls must start with @.

| Function | Arguments | Behavior |
|---|---:|---|
| @send(message) | 1 | Send a message in the current channel. |
| @send(message, channel) | 2 | Send to a text channel identified by ID or exact name; a leading # is optional for names. |
| @ban(user, reason) | 2 | Ban a user; the reason is required by the parser. |
| @unban(user_id[, reason]) | 1–2 | Remove a ban. |
| @kick(user[, reason]) | 1–2 | Kick a member. |
| @timeout(user, minutes) | 2 | Timeout a member for 1–40,320 minutes. |
| @untimeout(user) | 1 | Remove a timeout. |
| @give_role(user, role) / @add_role(user, role) | 2 | Assign a role. |
| @remove_role(user, role) | 2 | Remove a role. |
| @create_role(name[, color[, permissions]]) | 1–3 | Create a role. Color is a six-digit hex value; permissions are a comma-separated allowlist. The administrator permission and other unsupported permissions are rejected. |
| @delete_role(role_id_or_name) | 1 | Delete a role by ID or exact name. |
| @create_category(name[, permissions]) | 1–2 | Create a category, optionally with role permission overwrites. |
| @create_channel(name[, category[, permissions]]) | 1–3 | Create a text channel, optionally in an existing category and with permission overwrites. |
| @delete_channel(channel_id_or_name) | 1 | Delete a text channel by ID or exact name. Categories are not accepted. |
| @slowmode(seconds) | 1 | Set slowmode in the current text channel (0–21,600 seconds). |
| @clear(count) | 1 | Delete 1–100 messages in the current text channel. |
| @guilds_roles() | 0 | List server roles. |
| @guilds_members() | 0 | List up to 100 server members. Requires Server Members Intent and appropriate Discord access. |
| @guilds_channels() | 0 | List server channels, excluding categories. |
| @guilds_categories() | 0 | List server categories. |

For @create_role, permission names are explicitly allowlisted in the runtime. They include selected channel, voice, moderation, and audit-log permissions, but not administrator. Category/channel overwrites use entries such as "@everyone:view_channel=deny, Moderators:send_messages=allow". Targets can be @everyone, a role ID, or an exact role name.

To reuse a role created by a script, declare a role.id variable and assign it the native action result:

    var helper_role.role.id = None;
    set helper_role = @create_role("Helpers", "#5865F2");
    @add_role("123456789012345678", helper_role);

The result is stored as an internal role reference and resolved during execution. The variable must be declared first and have type role.id. This assignment form is currently supported for @create_role only.

Aliases @mute and @unmute normalize to @timeout and @untimeout. The runtime does not implement @dm, @lock, @unlock, @set_channel.*, @set_role.*, @time, @uptime, or @random(collection). Use randint(min, max) for a random integer.

## Runtime limits and safety

- Maximum script length: 8,000 characters.
- Runtime action budget: MAX_SCRIPT_ACTIONS, default 1,000 and maximum 1,000.
- Script and input timeout: SCRIPT_TIMEOUT_SECONDS, default 300 seconds and maximum 300 seconds.
- Each Discord action is subject to the caller's and bot's effective permissions and Discord role hierarchy.
- Expressions are evaluated using an explicit AST allowlist; arbitrary eval and exec are not used.
- Native actions can still make destructive changes. Review scripts before execution and grant the bot only the permissions it needs.
