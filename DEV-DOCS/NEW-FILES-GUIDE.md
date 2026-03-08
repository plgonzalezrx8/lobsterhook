# New Files Guide

## Purpose
Help contributors decide where new code and new docs belong in Lobsterhook.

## Create Code In
- Add new runtime modules in `app/` when the responsibility is part of the poller, dispatcher, config, storage, or normalization pipeline.
- Add new tests in `tests/` with names that mirror the module or behavior being covered.
- Add service-manager helpers in `scripts/` or `launchd/` only when they are operational wrappers around existing runtime behavior.

## Create Docs In
- New feature behavior: `DEV-DOCS/features/<feature-name>.md`
- New reusable technical pattern: `DEV-DOCS/implementation/<pattern-name>.md`
- New runtime or secret contract: top-level docs such as `ENV-CONTRACT.md` when the information affects every contributor

## Update Existing Docs When
- mailbox polling behavior changes
- webhook delivery semantics or retry rules change
- config shape changes
- SQLite schema or runtime directory layout changes
- test workflow or service-manager guidance changes

## Cross-Link Rules
- Link active feature or implementation docs from `00-START-HERE.md` when they are needed for the next session.
- Update `ARCHITECTURE.md` or `project-structure.md` when subsystem boundaries change.
- Add a `work-log.md` entry whenever you introduce a new DEV-DOCS file or materially change a runtime contract.
