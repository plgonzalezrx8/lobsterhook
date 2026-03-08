# Coding Standards

## Purpose
Document the repository-specific coding rules for Lobsterhook contributors.

## Language and Framework Rules
- Prefer Python standard-library modules before adding third-party dependencies.
- Keep runtime code under `app/` small, explicit, and file-oriented; avoid framework-heavy abstractions.
- Use `pathlib.Path`, dataclasses, and explicit helper functions instead of ad hoc string-based paths or dynamic objects.

## Naming Conventions
- Match module names to their responsibility: `poller`, `dispatcher`, `normalizer`, `storage`, `db`, `config`.
- Use `remote_id` terminology everywhere instead of `uid` unless a future adapter proves Himalaya exposes a stable IMAP UID contract.

## Typing and Validation
- Keep type hints on public functions and dataclasses.
- Validate config inputs eagerly in [`app/config.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/config.py) so runtime modes fail fast.

## Error Handling
- Preserve durable state invariants before convenience. Do not mark mailbox scans successful or jobs done on partial failure.
- Log mailbox and delivery failures with enough context to identify the affected account, folder, and remote id.

## Comments and Documentation
- Comment non-obvious invariants only: scan cutoff logic, idempotency rules, retry backoff, and MIME parsing tradeoffs.
- Keep `DEV-DOCS/` aligned with changes to architecture, config, runtime behavior, or testing workflow.

## Imports and Dependencies
- Prefer local helper functions over introducing a new package for small transformations.
- Keep new dependencies rare and justified in the change set that adds them.

## Review Checklist
- [ ] Matches existing module boundaries and naming
- [ ] Preserves queue, retry, and mailbox-state invariants
- [ ] Keeps comments focused on non-obvious behavior
- [ ] Updates `DEV-DOCS/` when behavior or workflow changed
