# Feature - Mailbox Polling

## Purpose
Detect newly arrived email across configured Himalaya accounts and folders without reprocessing the same message forever.

## Scope
- In scope: envelope listing, unseen detection, raw export, normalization, artifact storage, queue insertion, mailbox scan timestamps
- Out of scope: provider-native IMAP synchronization, idle push, mailbox write-back, or message read views

## Current Behavior
- The poller iterates enabled accounts and folders from the Lobsterhook TOML config.
- For each mailbox, it uses `himalaya envelope list --output json` with paging and checks each envelope `id` against the `messages` table.
- Unseen envelopes are exported with `himalaya message export --full`, normalized from the raw `.eml`, written to disk, and inserted into SQLite together with an event row and a queued delivery job.
- The mailbox is marked successfully scanned only if the full scan completed without ingest errors.

## Key Files
- [`app/poller.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/poller.py)
- [`app/himalaya_adapter.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/himalaya_adapter.py)
- [`app/db.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/db.py)

## Edge Cases
- Himalaya envelope ids are opaque backend ids, so the poller dedupes on `(account, folder, remote_id)` instead of assuming IMAP UID semantics.
- The poller stops early only when it reaches a page where every message is already known and the page is older than the previous successful scan minus the configured safety buffer.
- If one message export or normalization fails, the mailbox scan is left unsuccessful so the failed message remains eligible on the next cycle.

## Validation and Testing
- `tests/test_poller.py` covers first-ingest behavior and repeat-poll idempotency.
- Manual validation still needs to confirm the page-cutoff heuristic against live Himalaya accounts with real backlog sizes.

## Open Follow-Ups
- Validate the scan cutoff strategy against real inboxes and tune `scan_page_cap` or `scan_lookback_seconds` if needed.
