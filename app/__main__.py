"""CLI entrypoint for Lobsterhook."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from app.config import load_config
from app.db import Database
from app.dispatcher import WebhookDispatcher
from app.himalaya_adapter import HimalayaAdapter
from app.normalization_evaluator import evaluate_expectation_directory
from app.poller import MailPoller
from app.storage import StorageManager


def build_parser() -> argparse.ArgumentParser:
    """Build the Lobsterhook CLI parser."""

    parser = argparse.ArgumentParser(description="Himalaya-backed email to webhook bridge.")
    parser.add_argument("--config", help="Path to lobsterhook.toml. Defaults to repo/local search paths.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Python log verbosity.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create or migrate the local SQLite database.")

    poller_parser = subparsers.add_parser("poller", help="Run the mailbox poller.")
    poller_parser.add_argument("--once", action="store_true", help="Run a single poll cycle and exit.")

    dispatcher_parser = subparsers.add_parser("dispatcher", help="Run the webhook dispatcher.")
    dispatcher_parser.add_argument("--once", action="store_true", help="Run one dispatcher batch and exit.")

    evaluator_parser = subparsers.add_parser(
        "evaluate-normalization",
        help="Evaluate normalization fixtures against expectation manifests.",
    )
    evaluator_parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=Path("tests/fixtures"),
        help="Directory containing .eml fixture files.",
    )
    evaluator_parser.add_argument(
        "--expectation-dir",
        type=Path,
        default=Path("tests/fixtures/normalization_expectations"),
        help="Directory containing JSON expectation manifests.",
    )
    evaluator_parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path for JSON output. Stdout is always written.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI program entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.command == "evaluate-normalization":
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

    config = load_config(args.config)
    database = Database(config.app.database_path)

    if args.command == "init-db":
        database.initialize()
        return 0

    if args.command == "poller":
        poller = MailPoller(
            config=config,
            database=database,
            storage=StorageManager(config.app.data_dir),
            adapter=HimalayaAdapter(
                himalaya_bin=config.app.himalaya_bin,
                himalaya_config=config.app.himalaya_config,
            ),
        )
        if args.once:
            poller.run_once()
            return 0
        poller.run_forever()
        return 0

    if args.command == "dispatcher":
        dispatcher = WebhookDispatcher(config=config, database=database)
        if args.once:
            dispatcher.run_once()
            return 0
        dispatcher.run_forever()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
