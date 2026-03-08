"""Normalize raw RFC822 messages into a JSON payload suited for webhooks."""

from __future__ import annotations

import hashlib
import json
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from app.models import AttachmentMetadata, NormalizedMessage


def normalize_email(
    *,
    account: str,
    folder: str,
    remote_id: str,
    remote_id_kind: str,
    raw_path: Path,
    normalized_path: Path,
    detected_at: str,
    exported_at: str,
) -> NormalizedMessage:
    """Build a stable JSON payload from the raw exported `.eml` file."""

    message = BytesParser(policy=policy.default).parsebytes(raw_path.read_bytes())

    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[AttachmentMetadata] = []

    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = part.get_content_disposition()
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        content_type = part.get_content_type()

        if disposition == "attachment" or filename:
            attachments.append(
                AttachmentMetadata(
                    filename=filename,
                    content_type=content_type,
                    content_id=_trim_header(part.get("Content-ID")),
                    disposition=disposition,
                    size_bytes=len(payload),
                )
            )
            continue

        body = _read_part_content(part, payload)
        if content_type == "text/plain":
            text_parts.append(body)
        elif content_type == "text/html":
            html_parts.append(body)

    message_id = _normalize_message_id(message.get("Message-ID"))
    in_reply_to = _normalize_message_ids(message.get("In-Reply-To"))
    references = _normalize_message_ids(message.get("References"))
    thread_key = _derive_thread_key(references, in_reply_to, message_id, account, folder, remote_id)
    text_body = "\n".join(part for part in text_parts if part).strip() or None
    html_body = "\n".join(part for part in html_parts if part).strip() or None
    sent_at = _normalize_date(message.get("Date"))
    body_hash = hashlib.sha256(
        json.dumps({"text_body": text_body, "html_body": html_body}, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return NormalizedMessage(
        account=account,
        folder=folder,
        remote_id=remote_id,
        remote_id_kind=remote_id_kind,
        detected_at=detected_at,
        message_id=message_id,
        in_reply_to=in_reply_to,
        references=references,
        thread_key=thread_key,
        subject=_trim_header(message.get("Subject")),
        sent_at=sent_at,
        sender=_first_address(message.get_all("From", [])),
        to=_parse_addresses(message.get_all("To", [])),
        cc=_parse_addresses(message.get_all("Cc", [])),
        bcc=_parse_addresses(message.get_all("Bcc", [])),
        reply_to=_parse_addresses(message.get_all("Reply-To", [])),
        text_body=text_body,
        html_body=html_body,
        attachments=attachments,
        headers=_collect_headers(message),
        body_hash=body_hash,
        raw_path=str(raw_path),
        normalized_path=str(normalized_path),
        exported_at=exported_at,
    )


def _read_part_content(part: object, payload: bytes) -> str:
    try:
        rendered = part.get_content()
    except LookupError:
        charset = part.get_content_charset() or "utf-8"
        rendered = payload.decode(charset, errors="replace")
    return str(rendered)


def _parse_addresses(values: list[str]) -> list[dict[str, str | None]]:
    addresses: list[dict[str, str | None]] = []
    for name, address in getaddresses(values):
        if not name and not address:
            continue
        addresses.append({"name": name or None, "address": address or None})
    return addresses


def _first_address(values: list[str]) -> dict[str, str | None]:
    parsed = _parse_addresses(values)
    return parsed[0] if parsed else {"name": None, "address": None}


def _collect_headers(message: object) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for name, value in message.items():
        headers.setdefault(name, []).append(_trim_header(str(value)) or "")
    return headers


def _normalize_message_ids(value: str | None) -> list[str]:
    if not value:
        return []
    tokens = [_normalize_message_id(item) for item in value.split()]
    return [token for token in tokens if token]


def _normalize_message_id(value: str | None) -> str | None:
    if not value:
        return None
    compact = " ".join(str(value).split()).strip()
    return compact or None


def _derive_thread_key(
    references: list[str],
    in_reply_to: list[str],
    message_id: str | None,
    account: str,
    folder: str,
    remote_id: str,
) -> str:
    # Use the oldest explicit reference first so the same conversation collapses
    # toward a stable root even when later replies append more message IDs.
    if references:
        return references[0]
    if in_reply_to:
        return in_reply_to[0]
    if message_id:
        return message_id
    return f"{account}:{folder}:{remote_id}"


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


def _trim_header(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    return " ".join(str(value).splitlines()).strip()
