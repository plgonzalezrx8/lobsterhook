# Implementation Pattern - Normalization Fixture Playbook

## Purpose
Maintain a stable, anonymized fixture corpus that catches heuristic drift in email HTML cleanup and preferred-message selection.

## Workflow
1. Capture candidate `.eml` samples from staging or disposable inboxes.
2. Remove or redact personal data before committing:
   - sender and recipient names
   - email addresses
   - account identifiers
   - tracking URLs with tenant-specific IDs
3. Save sanitized fixtures under `tests/fixtures/`.
4. Add or update expectation manifests under `tests/fixtures/normalization_expectations/`.
5. Run:
   - `uv run python -m app evaluate-normalization --json-output ./.tmp/normalization-eval.json`
6. Review any failed checks and adjust expectations only when behavior changes are intentional.

## Manifest Schema
Each expectation file is JSON with this shape:

```json
{
  "fixture": "example.eml",
  "account": "support",
  "folder": "INBOX",
  "remote_id": "fixture-example",
  "checks": {
    "preferred_message_source": "text/plain",
    "preferred_message_format": "plain",
    "preferred_message_contains": ["required snippet"],
    "preferred_message_not_contains": ["forbidden snippet"],
    "markdown_contains": ["required snippet"],
    "markdown_not_contains": ["forbidden snippet"],
    "cleaned_html_contains": ["required snippet"],
    "cleaned_html_not_contains": ["forbidden snippet"],
    "quoted_reply_removed": true,
    "tracking_pixel_removed": true
  }
}
```

## Guardrails
- Keep expectations behavior-focused, not implementation-detail-focused.
- Prefer short snippet checks over full-body exact matches to reduce brittle tests.
- When adding a new heuristic, document comment rationale in code using:
  - why it exists
  - failure mode if removed
