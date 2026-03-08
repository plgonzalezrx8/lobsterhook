# Testing and Performance

## Testing Strategy
- Unit / component: `pytest` covers config parsing, email normalization, queue persistence, polling idempotency, and dispatcher failure behavior.
- Integration / API: Current tests use temporary SQLite databases, fixture `.eml` files, and adapter stubs to simulate Himalaya and webhook flows.
- End-to-end / system: Not yet automated. Live mailbox and webhook validation is still a manual follow-up.

## Quality Gates
- Run `uv run --with pytest pytest` before committing runtime changes.
- Run a CLI smoke check for `python -m app`, `python -m app poller --help`, and `python -m app dispatcher --help` when CLI interfaces change.

## Current Gaps
- No automated CI pipeline exists yet.
- No live integration test exercises a real Himalaya account or an actual HTTP receiver.

## Performance Focus Areas
- Poll scans should stop after the first fully known and clearly old page so large inboxes do not get rescanned forever.
- Dispatcher retries should back off aggressively enough to avoid hammering failing webhook receivers.

## Commands
- `uv run --with pytest pytest`
- `uv run python -m app --help`
- `uv run python -m app poller --help`
- `uv run python -m app dispatcher --help`
