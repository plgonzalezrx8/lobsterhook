# Architecture

## Overview
Lobsterhook is a local-first Python service that turns newly detected Himalaya mailbox messages into durable outbound webhook deliveries. It separates mailbox access, local normalization, queueing, and HTTP dispatch so retries and audit data stay under local control.

## Tech Stack
- Framework / runtime: Python 3.14 standard-library application executed with `uv`
- Language(s): Python
- Data layer: SQLite via `sqlite3`
- Auth / identity: Per-account Bearer token outbound webhook auth
- Validation: TOML parsing with explicit config validation and runtime checks
- Testing: `pytest`
- Deployment target: macOS-first local services via `launchd`

## Runtime Topology
1. The `poller` process calls Himalaya to list recent envelopes for configured accounts and folders.
2. For each unseen remote id, Lobsterhook exports a raw `.eml`, normalizes it into JSON, writes local artifacts, and inserts a queue job.
3. The `dispatcher` process claims queued jobs, POSTs the normalized JSON to the configured webhook, and records retries or dead-letter outcomes in SQLite.

## Major Boundaries
- Himalaya owns mailbox access; Lobsterhook does not attempt to reimplement IMAP synchronization.
- Raw `.eml` export is the normalization source of truth; `message read` is not part of the ingest path.
- Webhook secrets stay in config sources, not in queued job payloads.

## Data Flow
1. [`app/himalaya_adapter.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/himalaya_adapter.py) lists envelopes and exports unseen raw mail.
2. [`app/normalizer.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/normalizer.py) parses the `.eml` and produces the normalized JSON payload.
3. [`app/db.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/db.py) persists mailbox state, events, queue jobs, and delivery attempts.
4. [`app/dispatcher.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/dispatcher.py) loads the normalized JSON and performs outbound delivery.

## External Integrations
- Himalaya CLI 1.2.x for mailbox access
- Arbitrary outbound webhook receivers authenticated with Bearer tokens

## Related Docs
- [project-structure.md](./project-structure.md)
- [SECURITY-GUIDELINES.md](./SECURITY-GUIDELINES.md)
- [features/mailbox-polling.md](./features/mailbox-polling.md)
- [features/outbound-webhook-delivery.md](./features/outbound-webhook-delivery.md)
- [implementation/himalaya-adapter.md](./implementation/himalaya-adapter.md)
