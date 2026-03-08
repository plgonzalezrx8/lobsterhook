# Testing and Performance

## Testing Strategy
- Unit / component: `pytest` covers config parsing, email normalization, HTML cleanup, Markdown fallback, queue persistence, polling idempotency, dispatcher payload shaping/compatibility, and normalization expectation evaluation.
- Integration / API: Current tests use temporary SQLite databases, fixture `.eml` files, and adapter stubs to simulate Himalaya and webhook flows.
- End-to-end / system: GitHub Actions runs static checks, security checks, Python tests, CLI smoke checks, and normalization evaluation on `ubuntu-latest` and `macos-latest`, but live mailbox and webhook validation is still manual.

## Quality Gates
- Run `uv run --with pytest pytest` before committing runtime changes.
- Run `uv run ruff check .`, `uv run mypy app tests scripts/evaluate_normalization.py`, and `uv run bandit -q -r app scripts/evaluate_normalization.py` before merging.
- Run `uv run python -m app evaluate-normalization --json-output ./.tmp/normalization-eval.json` to verify heuristic stability.
- Run a CLI smoke check for `python -m app`, `python -m app poller --help`, `python -m app dispatcher --help`, and `python -m app evaluate-normalization` when CLI interfaces change.
- Keep [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) aligned with the local commands above.

## Current Gaps
- No live integration test exercises a real Himalaya account or an actual HTTP receiver.
- No live fixture set yet exercises a broad range of real-world marketing email HTML and reply-chain HTML.

## Performance Focus Areas
- Poll scans should stop after the first fully known and clearly old page so large inboxes do not get rescanned forever.
- Dispatcher retries should back off aggressively enough to avoid hammering failing webhook receivers.

## Commands
- `uv run --with pytest pytest`
- `uv run ruff check .`
- `uv run mypy app tests scripts/evaluate_normalization.py`
- `uv run bandit -q -r app scripts/evaluate_normalization.py`
- `uv run python -m app --help`
- `uv run python -m app poller --help`
- `uv run python -m app dispatcher --help`
- `uv run python -m app evaluate-normalization --json-output ./.tmp/normalization-eval.json`
