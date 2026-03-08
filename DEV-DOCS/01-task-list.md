# 01 - Task List

## Last Updated
2026-03-08

## Purpose
Track the active execution backlog for Lobsterhook.

## Blockers
- None inside the repository. Live validation depends on local Himalaya account access and a reachable webhook endpoint.

## In Progress
- [ ] Validate the current implementation against a real Himalaya account and a disposable webhook receiver.

## Up Next
- [ ] Validate `payload_mode = "minimal"` on a real HTML-heavy email and confirm the webhook consumer gets the slim payload shape.
- [ ] Add a small replay or inspect command for dead-letter jobs and delivery attempts.
- [ ] Add more integration coverage around malformed Himalaya JSON and missing normalized payload files.
- [ ] Add success-path dispatcher coverage with a stubbed receiver response.

## Backlog
- [ ] Add Linux `systemd` unit templates after the macOS `launchd` flow is validated.
- [ ] Add richer outbound webhook metadata or custom headers if real consumers need them.

## Completed Recently
- [x] Implemented the Lobsterhook v1 scaffold with poller, dispatcher, SQLite state, and local artifact storage.
- [x] Bootstrapped `DEV-DOCS/` and expanded the root `README.md`.
- [x] Added GitHub Actions CI for tests and CLI smoke checks on push and pull requests.
- [x] Added HTML cleanup, Markdown fallback, and configurable minimal webhook payload mode.

## Notes
- See [features/mailbox-polling.md](./features/mailbox-polling.md) for poller behavior details.
- See [implementation/himalaya-adapter.md](./implementation/himalaya-adapter.md) for the CLI assumptions that shape the current design.
