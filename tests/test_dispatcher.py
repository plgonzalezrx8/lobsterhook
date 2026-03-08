from __future__ import annotations

import json
from pathlib import Path
from app.config import load_config
from app.db import Database
from app.dispatcher import WebhookDispatcher


def _build_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        """
        [app]
        data_dir = "./data"
        max_attempts = 2
        initial_backoff_seconds = 1
        max_backoff_seconds = 2

        [[accounts]]
        name = "support"
        folders = ["INBOX"]
        webhook_url = "https://example.com/webhook"
        bearer_token = "secret-token"
        """,
        encoding="utf-8",
    )
    return config_path


def test_dispatcher_dead_letters_permanent_failures(tmp_path: Path, monkeypatch) -> None:
    config = load_config(_build_config(tmp_path))
    database = Database(config.app.database_path)
    database.initialize()
    database.ensure_mailbox("support", "INBOX", "2026-03-08T12:00:00+00:00")

    normalized_path = config.app.data_dir / "normalized.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps({"subject": "Testing"}), encoding="utf-8")
    event_path = config.app.data_dir / "event.json"
    event_path.write_text(json.dumps({"event_type": "mail.received"}), encoding="utf-8")

    database.create_message_event_and_job(
        message={
            "account": "support",
            "folder": "INBOX",
            "remote_id": "42",
            "remote_id_kind": "himalaya_backend_id",
            "message_id": "<message-123@example.com>",
            "thread_key": "<root@example.com>",
            "sender": "sender@example.com",
            "subject": "Testing Lobsterhook",
            "received_at": "2026-03-08T12:00:00+00:00",
            "raw_path": "/tmp/raw.eml",
            "normalized_path": str(normalized_path),
            "body_hash": "abc123",
            "status": "queued",
        },
        event_type="mail.received",
        event_dedupe_key="mail.received:support:INBOX:42",
        payload_path=str(event_path),
        job_type="dispatch_webhook",
        job_payload={
            "account": "support",
            "folder": "INBOX",
            "remote_id": "42",
            "normalized_path": str(normalized_path),
            "event_payload_path": str(event_path),
        },
        available_at="2020-03-08T12:00:00+00:00",
        created_at="2020-03-08T12:00:00+00:00",
    )

    dispatcher = WebhookDispatcher(config=config, database=database)

    def fake_result(url: str, token: str, payload: dict[str, object]):
        return type("Result", (), {"status_code": 400, "response_body": "bad request", "error": "HTTP 400"})()

    monkeypatch.setattr(dispatcher, "_post_payload", fake_result)
    dispatcher.run_once()

    remaining_jobs = database.get_due_jobs("9999-01-01T00:00:00+00:00", 10)
    stored_job = database.get_job(1)

    assert remaining_jobs == []
    assert stored_job is not None
    assert stored_job["status"] == "dead_letter"
