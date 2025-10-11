---
mode: agent
---
Copilot, follow these repository-wide constraints:

1. **Security-first**: Never output code that leaks secrets or bypasses the policy engine. All side-effects must be gated by approvals and sandbox checks.
2. **Typing + Tests**: Provide full type hints and propose unit tests with `pytest`. Maintain coverage expectations.
3. **Separation of Concerns**: Keep planner logic free of side-effects. Route actions via tool interfaces only.
4. **Logging**: Use `structlog` with contextual fields. Do not print secrets.
5. **Docs**: When adding or changing interfaces, update docstrings and reference docs.

# Copilot Prompt (Repository Guide)

You are assisting on a **local, permissioned personal agent** written in Python.
Default to **secure, testable, and typed** code. Follow these rules **always**:

## Architecture Boundaries
- Expose actions only via **tools** (files, mail, calendar, browser, scheduler). Do NOT perform side-effects from the planner.
- Every tool must declare: inputs schema, outputs schema, **effects** (read/write/network), and sandbox scope.
- **Policy engine** must be consulted before any action with side-effects.

## Coding Rules
- Python 3.11+, **type hints required** for all public functions.
- Raise specific exceptions. No bare `except:`. Propagate rich errors.
- Logging via `structlog` with contextual fields (task_id, tool, duration).
- Never echo secrets or tokens. Read secrets via keyring adapter (not env in prod flow).
- For file operations: enforce sandbox paths and normalize/resolve paths.

## Security Rules
- Any action that sends email, writes/renames/deletes files, or performs external POST/PUT must go through **approval prompt** and be logged.
- Plan/Tool inputs must be validated with `pydantic` models.
- Strip PII/secrets from logs. Redact common patterns (keys, tokens, email addresses) unless needed for local-only debugging.

## Testing Expectations
- For every new function: add unit tests and property tests if applicable.
- For new tools: add integration tests with fakes/stubs; never hit live endpoints by default.
- Maintain ≥90% coverage in core (planner, policy, executor, tools.files).

## Documentation
- Add docstrings (Google style) and update `ARCHITECTURE.md` sections if interfaces change.
- Update `CHANGELOG.md` for user-visible changes.

## Examples
- Implementing a new file tool should follow the pattern:
  - `list_files(path, glob) -> list[Path]`
  - `merge_pdfs(paths, out) -> Artifact` (requires approval; log hash)
- For scheduler parsing, prefer `dateutil` and provide RRULE + NL roundtrip tests.

Remember: **Local-first, privacy-first, least privilege.**

