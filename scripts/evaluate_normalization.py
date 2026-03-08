#!/usr/bin/env python3
"""Run normalization fixture evaluation and emit machine-readable JSON output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow direct script execution without packaging the project.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def build_parser() -> argparse.ArgumentParser:
    """Build CLI arguments for normalization expectation evaluation."""

    parser = argparse.ArgumentParser(description="Evaluate normalization fixtures against expectation manifests.")
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=Path("tests/fixtures"),
        help="Directory containing .eml fixture files.",
    )
    parser.add_argument(
        "--expectation-dir",
        type=Path,
        default=Path("tests/fixtures/normalization_expectations"),
        help="Directory containing JSON expectation manifests.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path for JSON output. Stdout is always written.",
    )
    return parser


def main() -> int:
    """Program entrypoint for local and CI fixture evaluation."""

    from app.normalization_evaluator import evaluate_expectation_directory

    parser = build_parser()
    args = parser.parse_args()

    report = evaluate_expectation_directory(
        fixture_dir=args.fixture_dir,
        expectation_dir=args.expectation_dir,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
