# Lobsterhook

Lobsterhook is a local-first email-to-webhook bridge built around [Himalaya](https://github.com/pimalaya/himalaya). It polls configured mailboxes, exports each unseen message as a raw `.eml`, normalizes it into JSON with Python's standard library, stores the artifacts locally, and dispatches the normalized payload to a configured outbound webhook.

## Why Himalaya

Himalaya already solves mailbox access and account configuration. Lobsterhook keeps the sync logic outside Himalaya's scope:

- `himalaya envelope list --output json` provides compact detection metadata.
- `himalaya message export --full` provides the canonical raw `.eml` used for normalization.
- Himalaya envelope ids are treated as opaque backend ids, not assumed to be raw IMAP UIDs.

That separation keeps Lobsterhook focused on persistence, idempotency, retries, and outbound delivery.

## Current v1 Scope

- Poll multiple Himalaya accounts and multiple folders.
- Detect unseen mail using local SQLite state.
- Store raw `.eml` and normalized `.json` artifacts under `data/`.
- Queue outbound webhook deliveries with retry and dead-letter behavior.
- Run as a poller process and a dispatcher process.

Out of scope in the current implementation:

- mailbox write-back or draft creation
- inbound webhook ingestion
- OpenClaw-specific prompting or agent orchestration
- Linux-first service packaging

## Repository Layout

```text
.
├── .github/workflows/        # GitHub Actions CI workflows
├── app/                     # Python package for config, polling, normalization, and dispatch
├── launchd/                 # macOS launchd plist templates
├── scripts/                 # Thin uv-backed runner scripts
├── tests/                   # Unit and integration-style tests
├── DEV-DOCS/                # Repository operating docs
├── lobsterhook.example.toml # Example configuration
└── pyproject.toml           # Python project metadata
```

## Prerequisites

- Python 3.14+
- `uv`
- Himalaya 1.2.x available on `PATH`
- A working Himalaya account configuration, usually at `~/.config/himalaya/config.toml`

Optional:

- macOS `launchd` if you want Lobsterhook to run continuously as background services

## Configuration

Lobsterhook uses a TOML config file. The CLI searches for:

1. `./lobsterhook.toml`
2. `~/.config/lobsterhook/config.toml`

An example file lives at [`lobsterhook.example.toml`](./lobsterhook.example.toml).

Each `[[accounts]]` entry defines:

- the Himalaya account name
- the folders to monitor
- the outbound webhook URL
- the webhook `payload_mode`:
  - `full` keeps the current rich normalized JSON payload
  - `minimal` sends a slim sanitized body with only the key headers, debug metadata, and one chosen message field
- exactly one bearer-token source:
  - inline `bearer_token`
  - `bearer_token_env`
  - `bearer_token_file`

## Webhook Payload Modes

Lobsterhook keeps raw `.eml` files and rich normalized JSON locally, but the webhook body can now be configured per account.

- `payload_mode = "full"` sends the whole normalized JSON document.
- `payload_mode = "minimal"` sends only:
  - `account`
  - `folder`
  - `remote_id`
  - `detected_at`
  - `return_path`
  - `date`
  - `from`
  - `to`
  - `subject`
  - `message`
  - `message_format`
  - `message_source`

### Minimal Contract Stability Policy

- Minimal payload is treated as a versioned compatibility contract (`v1`).
- The key set and key order are intentionally deterministic.
- No wire-breaking key rename/removal is allowed without:
  - updating the versioned fixture contract tests
  - documenting the migration in the same change set

Message selection rule:

- prefer cleaned `text/plain` when it exists
- otherwise clean `text/html` and convert it to Markdown

This keeps noisy HTML, local artifact paths, and large header blobs out of webhook consumers when you switch an account to minimal mode.

## Runtime Modes

Initialize the database:

```bash
uv run python -m app --config ./lobsterhook.toml init-db
```

Run one poll cycle:

```bash
uv run python -m app --config ./lobsterhook.toml poller --once
```

Run the long-lived poller:

```bash
uv run python -m app --config ./lobsterhook.toml poller
```

Run one dispatcher batch:

```bash
uv run python -m app --config ./lobsterhook.toml dispatcher --once
```

Run the long-lived dispatcher:

```bash
uv run python -m app --config ./lobsterhook.toml dispatcher
```

Shell wrappers are available in [`scripts/`](./scripts/).

## Local Artifact Layout

By default, Lobsterhook stores runtime state under `./data`:

```text
data/
├── lobsterhook.db
├── raw/
├── normalized/
├── events/
├── logs/
└── tmp/
```

- `raw/` stores exported `.eml` files.
- `normalized/` stores JSON payloads built from the raw messages.
- In minimal payload mode, the webhook body is smaller than the normalized artifact kept on disk.
- `events/` stores compact event manifests used for audit and replay.
- `lobsterhook.db` stores mailbox state, ingested messages, queue jobs, and delivery attempts.

## Testing

Run the test suite:

```bash
uv run --with pytest pytest
```

GitHub Actions runs the same test suite and CLI smoke checks on every push, pull request, and manual dispatch through [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).

Run normalization heuristic regression checks:

```bash
uv run python -m app evaluate-normalization --json-output ./.tmp/normalization-eval.json
```

Quick CLI smoke checks:

```bash
uv run python -m app --help
uv run python -m app poller --help
uv run python -m app dispatcher --help
uv run python -m app evaluate-normalization
```

## Documentation

Start with [`DEV-DOCS/README.md`](./DEV-DOCS/README.md) and [`DEV-DOCS/00-START-HERE.md`](./DEV-DOCS/00-START-HERE.md). The `DEV-DOCS` folder is the active engineering source of truth for architecture, status, work tracking, and implementation patterns.
