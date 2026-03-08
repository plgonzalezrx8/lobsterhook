from __future__ import annotations

from pathlib import Path

from app.normalizer import normalize_email


def test_normalize_email_extracts_bodies_headers_and_thread_key(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_email.eml"
    raw_path = tmp_path / "message.eml"
    raw_path.write_bytes(fixture.read_bytes())
    normalized_path = tmp_path / "message.json"

    normalized = normalize_email(
        account="support",
        folder="INBOX",
        remote_id="42",
        remote_id_kind="himalaya_backend_id",
        raw_path=raw_path,
        normalized_path=normalized_path,
        detected_at="2026-03-08T12:00:00+00:00",
        exported_at="2026-03-08T12:00:05+00:00",
    )

    assert normalized.message_id == "<message-123@example.com>"
    assert normalized.thread_key == "<root@example.com>"
    assert normalized.text_body == "Hello from plain text."
    assert "<strong>HTML</strong>" in (normalized.html_body or "")
    assert normalized.sender["address"] == "sender@example.com"
    assert normalized.to[0]["address"] == "support@example.com"
    assert normalized.attachments[0].filename == "note.txt"
    assert normalized.attachments[0].size_bytes > 0
    assert normalized.body_hash
