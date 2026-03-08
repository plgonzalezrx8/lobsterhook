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
    assert normalized.return_path is None
    assert normalized.date == "Sun, 08 Mar 2026 10:15:00 +0000"
    assert normalized.thread_key == "<root@example.com>"
    assert normalized.text_body == "Hello from plain text."
    assert normalized.cleaned_text_body == "Hello from plain text."
    assert "<strong>HTML</strong>" in (normalized.html_body or "")
    assert normalized.cleaned_html_body is not None
    assert normalized.markdown_body == "Hello from **HTML**."
    assert normalized.preferred_message == "Hello from plain text."
    assert normalized.preferred_message_format == "plain"
    assert normalized.preferred_message_source == "text/plain"
    assert normalized.sender["address"] == "sender@example.com"
    assert normalized.to[0]["address"] == "support@example.com"
    assert normalized.attachments[0].filename == "note.txt"
    assert normalized.attachments[0].size_bytes > 0
    assert normalized.body_hash


def test_normalize_email_cleans_noisy_html_and_converts_to_markdown(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "noisy_html_email.eml"
    raw_path = tmp_path / "message.eml"
    raw_path.write_bytes(fixture.read_bytes())
    normalized_path = tmp_path / "message.json"

    normalized = normalize_email(
        account="support",
        folder="INBOX",
        remote_id="99",
        remote_id_kind="himalaya_backend_id",
        raw_path=raw_path,
        normalized_path=normalized_path,
        detected_at="2026-03-08T12:00:00+00:00",
        exported_at="2026-03-08T12:00:05+00:00",
    )

    assert normalized.text_body is None
    assert normalized.cleaned_text_body is None
    assert normalized.html_body is not None
    assert normalized.cleaned_html_body is not None
    assert "console.log" not in normalized.cleaned_html_body
    assert "gmail_quote" not in normalized.cleaned_html_body
    assert "Old quoted reply" not in normalized.cleaned_html_body
    assert "display:none" not in normalized.cleaned_html_body
    assert normalized.markdown_body is not None
    assert normalized.preferred_message == normalized.markdown_body
    assert normalized.preferred_message_format == "markdown"
    assert normalized.preferred_message_source == "text/html"
    assert "Hello **team**," in normalized.markdown_body
    assert "[your account link](https://example.com/account)" in normalized.markdown_body
    assert "Old quoted reply" not in normalized.markdown_body
