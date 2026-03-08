# Implementation Pattern - Himalaya Adapter

## Purpose
Capture the narrow Lobsterhook contract with Himalaya so mailbox-specific assumptions stay isolated in one module.

## When To Use
- Use [`app/himalaya_adapter.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/himalaya_adapter.py) for any mailbox listing or raw message export logic.
- Extend this module first if Lobsterhook later needs more Himalaya commands or better diagnostics.

## Key Files
- [`app/himalaya_adapter.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/himalaya_adapter.py)
- [`app/poller.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/poller.py)

## Invariants
- Treat envelope `id` as an opaque backend identifier and expose it as `remote_id`.
- Use `message export --full` for ingest. Do not build normalization around `message read`.
- Pass `--quiet` and keep the adapter responsible for subprocess error normalization.

## Failure Modes
- Invalid JSON from `envelope list` raises `HimalayaAdapterError`.
- Missing exported files after a successful subprocess call also raise `HimalayaAdapterError`.

## Validation
- `tests/test_poller.py` uses an adapter stub to validate the poller contract.
- Manual live validation should confirm the current assumptions for the configured Himalaya version and account mix.
