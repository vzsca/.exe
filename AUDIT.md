# Repository Audit

Audit date: October 26, 2026  
Repository: `vzsca/.exe`  
Scope: README and language reference, parser/runtime behavior, access control, persistence, launch scripts, control panel, tests, and CI configuration.

## Executive summary

The repository documents a restricted Discord scripting language rather than Python. The README, language reference, privacy-policy template, terms template, launcher output, control-panel output, and built-in help have been converted to English. The language reference has been reconciled with the parser/runtime behavior checked during this audit.

This is a source-level maintenance audit, not a formal penetration test. Discord API behavior and permission outcomes still need validation in a private test server.

## Code-to-documentation comparison

| Area | Result |
|---|---|
| Typed variables and assignments | The parser supports the documented typed declarations and `set` assignments. |
| Safe expressions | Evaluation uses an explicit AST allowlist; arbitrary function calls and attribute access are rejected. |
| Dictionary literals | Dictionary literals, nested dictionaries, and indexing are supported by the parser and covered by regression tests. |
| Conditions | The block condition compares a variable with an expected value; an optional `else` is supported. `elif` is not implemented. |
| Loops | `repeat` and numeric `range` loops are bounded; range stop is exclusive. The implementation limits repeat/range length to 10 and nesting depth to four. |
| Input | Replies are plain text even when the declaration names `int`, `float`, `bool`, or an ID type. The reference now states that the declared initial value is ignored. |
| Discord actions | The documented action names and argument counts were compared with the parser registry and runtime handlers. Role/channel operations remain subject to Discord permissions and hierarchy. |
| Runtime limits | The configured runtime defaults to a 1,000-action budget and a 300-second timeout; scripts are capped at 8,000 characters. |
| Role mentions | The runtime restricts allowed mentions and only enables role mention resolution for supported f-string sends. User input is neutralized to prevent it from creating pings. |

## Findings

### Resolved — Unused event-handler API removed

The bot has no event registration or dispatch workflow, so the unused event-handler methods and table creation for new databases have been removed. Existing databases may retain the legacy table, but the current application does not read or write it. Event automation remains out of scope until an end-to-end design and tests are added.

### Low — Duplicate CI workflows

Both `.github/workflows/tests.yml` and `.github/workflows/python-tests.yml` ran pytest on pushes and pull requests. The latter also compiles Python modules before running tests, so the duplicate workflow added redundant CI work. The redundant `tests.yml` workflow has been removed; `python-tests.yml` remains.

### Low — Setup instructions and launcher environment disagreed

The README originally described a `.venv` directory, while the launch scripts and control panel expect a `venv` directory. The README now uses the same directory name as the launchers.

### Low — Unknown-instruction guidance suggested unsupported syntax

The parser's fallback error message suggested legacy forms such as `let` and compact calls even though the public syntax validator rejects them. The message now points users to the modern typed declarations, `@`-prefixed native calls, brace blocks, and `docu.md`.

## Security observations

- Script execution is restricted to the configured owner and whitelisted users.
- Destructive actions check the caller's and bot's effective permissions; member/role operations also check Discord role hierarchy where applicable.
- The parser evaluates expressions through a restricted AST evaluator rather than Python `eval` or `exec`.
- Script length, action count, loop expansion, input length, and execution time are bounded.
- The test suite uses mocked Discord objects. It cannot prove behavior against every live Discord permission configuration or API failure.

No claim of complete security or GDPR compliance is made by this audit. Operators should review the permission list and test the bot in a private server before production use.

## Follow-up fixes

The remediation merged through pull requests #2 and #3 addresses the identified source-level defects:

- Conditions depending on user input are deferred to runtime rather than compared against a parser placeholder.
- Native-call and alias normalization no longer rewrites text inside quoted strings.
- Expression AST depth, node count, integer magnitude, and non-finite float results are bounded.
- Server Members Intent is opt-in and documented consistently with the `@guilds_members()` feature.
- The Windows virtual-environment activation path matches the documented `venv` directory.
- Regression tests cover dynamic conditions, quoted-message normalization, expression resource bounds, and multiple actions inside `if`, `else`, and `repeat` blocks.
- Unused event-handler persistence methods and table creation for new databases have been removed.

## Validation status

GitHub Actions completed successfully for the test and compile workflow on both remediation pull requests. The suite includes regression tests for runtime-dependent conditions, quoted-string normalization, expression resource limits, optional Server Members Intent configuration, and multi-action `if`, `else`, and `repeat` blocks. Live Discord permissions and API behavior still need testing in a private server.

## Files reviewed or updated

- `README.md`
- `docu.md`
- `PRIVACY_POLICY.md`
- `TERMS_OF_USE.md`
- `src/exe_bot/language.py`
- `src/exe_bot/bot.py`
- `panel.py`
- `start_bot.bat`
- `start_bot.sh`
- `.github/workflows/python-tests.yml`


## Follow-up — typed Discord action results

The follow-up review found that only `create_role` returned a value to scripts. The runtime and parser now also support results from `create_channel` and `create_category`: channel IDs can be rendered as safe channel mentions in f-strings, and category IDs can be passed to channel-creation actions. These paths have parser regression tests. Nested direct calls to `@create_role(...)`, `@create_channel(...)`, and `@create_category(...)` inside send f-strings are now supported for quoted literal arguments. Typed assignments remain the recommended option when reusing the created object in later actions.
