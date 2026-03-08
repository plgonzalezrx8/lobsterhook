## Summary
- What changed and why?

## Validation
- [ ] `uv run ruff check .`
- [ ] `uv run mypy app tests scripts/evaluate_normalization.py`
- [ ] `uv run bandit -q -r app scripts/evaluate_normalization.py`
- [ ] `uv run --with pytest pytest`
- [ ] `uv run python -m app evaluate-normalization --json-output ./.tmp/normalization-eval.json`

## Contract and Heuristic Checklist
- [ ] If minimal payload changed, golden fixtures were updated in `tests/fixtures/webhook_payloads/`.
- [ ] Minimal payload compatibility policy docs were updated for any wire-shape change.
- [ ] New or changed heuristic branches include comments for:
  - why the heuristic exists
  - failure mode if removed
- [ ] `DEV-DOCS/` and README were updated for behavior/tooling changes.
