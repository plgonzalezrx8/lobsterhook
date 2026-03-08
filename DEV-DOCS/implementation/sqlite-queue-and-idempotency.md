# Implementation Pattern - SQLite Queue And Idempotency

## Purpose
Document the local-state rules that prevent duplicate processing and preserve delivery history.

## When To Use
- Use this doc when changing queue state transitions, dedupe keys, mailbox scan timestamps, or delivery attempt recording.
- Use this doc when adding replay, dead-letter, or operational inspection tooling.

## Key Files
- [`app/db.py`](../../app/db.py)
- [`app/poller.py`](../../app/poller.py)
- [`app/dispatcher.py`](../../app/dispatcher.py)

## Invariants
- The primary dedupe key is `(account, folder, remote_id)` in the `messages` table.
- Event dedupe keys are `mail.received:<account>:<folder>:<remote_id>`.
- A mailbox is only marked successfully scanned after the full scan completes without ingest failures.
- Jobs are claimed by transitioning from `queued` to `running`, incrementing `attempts`, and then either returning to `queued`, moving to `dead_letter`, or finishing as `done`.

## Failure Modes
- If message ingest fails after an envelope is discovered, the mailbox stays unsuccessful and the missing message remains eligible on the next cycle.
- If dispatcher delivery fails or the normalized file is missing, the attempt is recorded and the job is retried or dead-lettered according to the retry rules.

## Validation
- `tests/test_db.py` validates message-event-job insertion.
- `tests/test_poller.py` validates duplicate detection across poll cycles.
- `tests/test_dispatcher.py` validates permanent failure dead-letter behavior.
