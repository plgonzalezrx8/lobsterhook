# Implementation Pattern - Local Storage And Normalization

## Purpose
Describe how Lobsterhook turns raw `.eml` files into portable JSON payloads and durable local artifacts.

## When To Use
- Use this pattern when adding new extracted fields to the webhook payload.
- Use this pattern when modifying data retention, directory layout, or MIME parsing behavior.

## Key Files
- [`app/storage.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/storage.py)
- [`app/normalizer.py`](/Users/pedrogonzalez/CascadeProjects/lobsterhook/app/normalizer.py)

## Invariants
- Raw `.eml` exports are the canonical record of a message.
- Normalized JSON is derived from the raw `.eml`, not from Himalaya's rendered message view.
- Artifact paths are partitioned by account, folder, year, and month to keep the local state navigable.

## Failure Modes
- Malformed MIME or charset issues should degrade to replacement decoding instead of crashing the parser outright.
- Filesystem writes must stay atomic enough that partially written JSON files are not left in place.

## Validation
- `tests/test_normalizer.py` covers plain-text, HTML, attachment, and thread-key extraction.
- Live mailbox testing still needs to validate a wider range of real-world MIME structures.
