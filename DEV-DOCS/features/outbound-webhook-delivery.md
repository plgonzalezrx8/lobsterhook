# Feature - Outbound Webhook Delivery

## Purpose
Deliver normalized email payloads to downstream systems without coupling Lobsterhook to any one consumer.

## Scope
- In scope: queued outbound HTTP POST delivery, Bearer-token auth, retry scheduling, delivery attempt audit, dead-letter transitions
- Out of scope: inbound webhooks, custom signature schemes, mailbox draft creation, or OpenClaw-specific orchestration

## Current Behavior
- The dispatcher claims queued jobs from SQLite in batches.
- Each claimed job loads the normalized JSON payload from disk, resolves the per-account Bearer token, and builds the outbound payload according to the account `payload_mode`.
- `payload_mode = "full"` preserves the current behavior and POSTs the whole normalized JSON document.
- `payload_mode = "minimal"` POSTs only the key headers, debug metadata, and the preferred message field selected by the normalizer.
- HTTP `2xx` responses mark the job done and the message delivered.
- Network failures, `408`, `429`, and `5xx` responses retry with exponential backoff up to the configured attempt limit.
- Other non-success responses move the job to `dead_letter`.

## Key Files
- [`app/dispatcher.py`](../../app/dispatcher.py)
- [`app/db.py`](../../app/db.py)

## Edge Cases
- Dispatcher-internal failures such as missing normalized payload files are caught and converted into retry or dead-letter state instead of crashing the batch.
- Bearer tokens are resolved from config sources at delivery time, so a queued job does not persist secrets.
- Minimal payload mode intentionally omits headers, raw paths, normalized paths, attachments, and HTML bodies from the webhook body.
- The dispatcher sleeps only when no jobs were processed in the current loop, which keeps a busy queue draining promptly.

## Validation and Testing
- `tests/test_dispatcher.py` covers the permanent-failure dead-letter path.
- `tests/test_dispatcher_payloads.py` covers both `full` and `minimal` payload shaping.
- Additional live tests are still needed for successful delivery and retry timing against a disposable receiver.

## Open Follow-Ups
- Add operator tooling to inspect or replay dead-letter jobs if real integrations need it.
