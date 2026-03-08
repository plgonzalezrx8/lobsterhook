# Work Log

## 2026-03-08 - Session: Sanitized Payload Mode And HTML Cleanup

### Session Goals
- Reduce webhook payload noise for HTML-heavy email.
- Keep rich local artifacts while allowing slim webhook consumers.
- Add tests and docs for the new payload contract.

### Work Completed
- Added per-account `payload_mode` support with `full` and `minimal` webhook delivery modes.
- Added HTML cleanup and Markdown fallback in the normalizer using Beautiful Soup and `markdownify`.
- Added tests for payload shaping and noisy HTML normalization.
- Updated README and DEV-DOCS to document the sanitized payload behavior.

### Follow-Up
- Validate minimal payload mode against real HTML-heavy mailbox traffic.
- Tune HTML cleanup heuristics if live mailers still leak quoted content or irrelevant markup.

## 2026-03-08 - Session: Initial Runtime Scaffold And DEV-DOCS Bootstrap

### Session Goals
- Implement the first working Lobsterhook v1 runtime scaffold.
- Research Himalaya behavior closely enough to avoid incorrect UID assumptions.
- Create the initial DEV-DOCS operating system for future sessions.

### Work Completed
- Added the Python project scaffold with config loading, SQLite schema, Himalaya CLI adapter, poller, dispatcher, storage helpers, and email normalization.
- Added tests covering config parsing, normalization, queue persistence, polling idempotency, and dispatcher dead-letter behavior.
- Added shell wrappers, `launchd` plist templates, an example config, and a fully populated `DEV-DOCS/` folder.
- Expanded the root `README.md` to describe current runtime behavior and repository usage.
- Added GitHub Actions CI to run the test suite and CLI smoke checks on pushes and pull requests.

### Follow-Up
- Validate the implementation end-to-end against a real mailbox and a disposable webhook receiver.
- Add CI for the current test suite and CLI smoke checks.
- Add operational tooling for dead-letter inspection or replay if live validation surfaces the need.
