from __future__ import annotations

import json
from pathlib import Path

from app.db import Database


def test_database_records_message_event_and_job(tmp_path: Path) -> None:
    database = Database(tmp_path / "lobsterhook.db")
    database.initialize()
    now = "2026-03-08T12:00:00+00:00"
    database.ensure_mailbox("support", "INBOX", now)

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
            "received_at": now,
            "raw_path": "/tmp/raw.eml",
            "normalized_path": "/tmp/normalized.json",
            "body_hash": "abc123",
            "status": "queued",
        },
        event_type="mail.received",
        event_dedupe_key="mail.received:support:INBOX:42",
        payload_path="/tmp/event.json",
        job_type="dispatch_webhook",
        job_payload={"account": "support", "folder": "INBOX", "remote_id": "42", "normalized_path": "/tmp/normalized.json"},
        available_at=now,
        created_at=now,
    )

    assert database.message_exists("support", "INBOX", "42")
    jobs = database.get_due_jobs(now, 10)
    assert len(jobs) == 1
    assert json.loads(jobs[0]["payload_json"])["remote_id"] == "42"
