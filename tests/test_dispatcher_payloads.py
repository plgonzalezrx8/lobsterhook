from __future__ import annotations

import json
from pathlib import Path

from app.config import load_config
from app.db import Database
from app.dispatcher import WebhookDispatcher


def _write_config(tmp_path: Path, payload_mode: str) -> Path:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        f"""
        [app]
        data_dir = "./data"

        [[accounts]]
        name = "support"
        folders = ["INBOX"]
        webhook_url = "https://example.com/webhook"
        payload_mode = "{payload_mode}"
        bearer_token = "secret-token"
        """,
        encoding="utf-8",
    )
    return config_path


def test_dispatcher_uses_minimal_payload_shape(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, "minimal"))
    dispatcher = WebhookDispatcher(config=config, database=Database(config.app.database_path))
    normalized_payload = {
        "account": "support",
        "folder": "INBOX",
        "remote_id": "42",
        "detected_at": "2026-03-08T12:00:00+00:00",
        "return_path": "<sender@example.com>",
        "date": "Sat, 08 Mar 2026 10:15:00 +0000",
        "sender": {"name": "Example Sender", "address": "sender@example.com"},
        "to": [{"name": "Support Team", "address": "support@example.com"}],
        "subject": "Testing Lobsterhook",
        "preferred_message": "Hello from plain text.",
        "preferred_message_format": "plain",
        "preferred_message_source": "text/plain",
        "headers": {"X-Test": ["1"]},
        "raw_path": "/tmp/raw.eml",
        "normalized_path": "/tmp/normalized.json",
        "html_body": "<p>Hello</p>",
        "text_body": "Hello",
        "attachments": [],
    }

    payload = dispatcher._build_webhook_payload("minimal", normalized_payload)

    assert payload == {
        "account": "support",
        "folder": "INBOX",
        "remote_id": "42",
        "detected_at": "2026-03-08T12:00:00+00:00",
        "return_path": "<sender@example.com>",
        "date": "Sat, 08 Mar 2026 10:15:00 +0000",
        "from": {"name": "Example Sender", "address": "sender@example.com"},
        "to": [{"name": "Support Team", "address": "support@example.com"}],
        "subject": "Testing Lobsterhook",
        "message": "Hello from plain text.",
        "message_format": "plain",
        "message_source": "text/plain",
    }


def test_dispatcher_preserves_full_payload_mode(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, "full"))
    dispatcher = WebhookDispatcher(config=config, database=Database(config.app.database_path))
    normalized_payload = {"account": "support", "headers": {"X-Test": ["1"]}}

    payload = dispatcher._build_webhook_payload("full", normalized_payload)

    assert payload is normalized_payload
