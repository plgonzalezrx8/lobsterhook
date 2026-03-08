# 00 - Start Here

## Last Updated
2026-03-08

## Purpose
Provide the minimum context needed to continue Lobsterhook without rediscovering the repository.

## Current Phase
Initial v1 scaffold is implemented and documented. The codebase now supports both full and minimal webhook payload modes, plus HTML cleanup and Markdown fallback, but it has not yet been validated against a full live mailbox-to-webhook run.

## Current Blockers
- No committed production `lobsterhook.toml` exists by design, so local runtime validation depends on machine-specific setup.

## Immediate Priorities
1. Run a real mailbox smoke test with a non-production webhook receiver and confirm end-to-end delivery.
2. Validate minimal payload mode on a noisy HTML email and confirm the webhook body is materially smaller and easier to consume.
3. Harden delivery observability with more explicit response logging and replay tooling if live testing exposes gaps.

## Read Next
1. [01-task-list.md](./01-task-list.md)
2. [DEVELOPMENT-STATUS.md](./DEVELOPMENT-STATUS.md)
3. [ARCHITECTURE.md](./ARCHITECTURE.md)
4. [project-structure.md](./project-structure.md)
5. [features/mailbox-polling.md](./features/mailbox-polling.md)
6. [implementation/sqlite-queue-and-idempotency.md](./implementation/sqlite-queue-and-idempotency.md)

## Key Constraints
- Himalaya envelope ids are treated as opaque backend ids, not as raw IMAP UIDs.
- Raw `.eml` export is the canonical source for message normalization and outbound webhook payloads.
- Minimal webhook mode must not leak local artifact paths or the full header dump.
