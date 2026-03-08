"""CLI entrypoint for Lobsterhook."""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from app.config import load_config
from app.db import Database
from app.dispatcher import WebhookDispatcher
from app.himalaya_adapter import HimalayaAdapter
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI program entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s %(message)s")

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
