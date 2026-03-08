# Project Structure

## Purpose
Explain the Lobsterhook repository layout and the role of each major directory.

## Root Layout
```text
lobsterhook/
├── app/
├── DEV-DOCS/
├── launchd/
├── scripts/
├── tests/
├── .gitignore
├── LICENSE
├── lobsterhook.example.toml
├── pyproject.toml
├── README.md
└── uv.lock
```

## Important Paths
- `app/` — Runtime code for config loading, Himalaya integration, message normalization, local storage, polling, and dispatch.
- `tests/` — Pytest coverage for the current runtime contract.
- `scripts/` — Thin wrappers around `uv run python -m app ...` for local operations and service managers.
- `launchd/` — macOS plist templates that point at the runner scripts.
- `DEV-DOCS/` — Operational docs, status tracking, and reusable implementation notes.

## Implementation Rules
- Keep mailbox, storage, and delivery responsibilities separated by module instead of collapsing them into a single service object.
- Add new runtime commands through [`app/__main__.py`](../app/__main__.py) and cover them with tests or smoke checks.
- Keep tracked configs credential-free. Real runtime secrets belong in env vars or local files outside git.

## Ownership / Boundaries
- `app/himalaya_adapter.py` is the only module that should know about Himalaya CLI subprocess details.
- `app/db.py` owns SQLite schema and status transitions.
- `app/normalizer.py` owns email parsing and portable thread/body extraction.
