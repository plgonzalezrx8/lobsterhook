"""Normalize raw RFC822 messages into a JSON payload suited for webhooks."""

from __future__ import annotations

import hashlib
import json
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup, Comment, Tag
from markdownify import BACKSLASH, STRIP, MarkdownConverter

from app.models import AttachmentMetadata, NormalizedMessage

HIDDEN_STYLE_PATTERNS = (
    "display:none",
    "display: none",
    "visibility:hidden",
    "visibility: hidden",
    "opacity:0",
    "opacity: 0",
)
QUOTED_CONTAINER_PATTERNS = (
    "gmail_quote",
    "gmail_extra",
    "gmail_attr",
    "yahoo_quoted",
    "protonmail_quote",
    "moz-cite-prefix",
    "divrplyfwdmsg",
)
TRACKING_PIXEL_DIMENSIONS = {"0", "1", "0px", "1px"}
GENERIC_IMAGE_ALTS = {"", "image", "logo", "pixel", "tracking pixel", "spacer"}


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
    cleaned_text_body = _clean_text_body(text_body)
    cleaned_html_body = _clean_html_body(html_body)
    markdown_body = _html_to_markdown(cleaned_html_body)
    preferred_message, preferred_message_format, preferred_message_source = _preferred_message(
        cleaned_text_body=cleaned_text_body,
        markdown_body=markdown_body,
    )
    sent_at = _normalize_date(message.get("Date"))
    date_header = _trim_header(message.get("Date"))
    return_path = _trim_header(message.get("Return-path"))
    body_hash = hashlib.sha256(
        json.dumps(
            {
                "text_body": text_body,
                "html_body": html_body,
                "cleaned_text_body": cleaned_text_body,
                "cleaned_html_body": cleaned_html_body,
                "markdown_body": markdown_body,
                "preferred_message": preferred_message,
                "preferred_message_format": preferred_message_format,
                "preferred_message_source": preferred_message_source,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return NormalizedMessage(
        account=account,
        folder=folder,
        remote_id=remote_id,
        remote_id_kind=remote_id_kind,
        detected_at=detected_at,
        return_path=return_path,
        date=date_header,
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
        cleaned_text_body=cleaned_text_body,
        cleaned_html_body=cleaned_html_body,
        markdown_body=markdown_body,
        preferred_message=preferred_message,
        preferred_message_format=preferred_message_format,
        preferred_message_source=preferred_message_source,
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


def _clean_text_body(value: str) -> str | None:
    if not value:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u200b", "")
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    cleaned = normalized.strip()
    return cleaned or None


def _clean_html_body(html: str | None) -> str | None:
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):
        comment.extract()

    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "canvas",
            "meta",
            "link",
            "title",
            "head",
            "iframe",
            "object",
            "embed",
            "form",
            "input",
            "button",
            "textarea",
            "select",
            "option",
        ]
    ):
        tag.decompose()

    # Heuristic cleanup keeps obvious non-message markup out of the webhook
    # fallback body without trying to fully re-implement an email client.
    for tag in list(soup.find_all(True)):
        if _is_hidden_tag(tag):
            tag.decompose()
            continue
        if _is_tracking_image(tag):
            tag.decompose()
            continue
        if _is_quoted_reply_container(tag):
            tag.decompose()

    cleaned = str(soup)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def _html_to_markdown(html: str) -> str | None:
    if not html:
        return None
    markdown = EmailMarkdownConverter(
        heading_style="ATX",
        bullets="-",
        autolinks=True,
        wrap=False,
        strip_document=STRIP,
        newline_style=BACKSLASH,
    ).convert(html)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    markdown = markdown.strip()
    return markdown or None


def _preferred_message(
    *,
    cleaned_text_body: str | None,
    markdown_body: str | None,
) -> tuple[str | None, str | None, str | None]:
    # Plain text usually comes from the sender's own alternative MIME part and
    # is therefore less noisy than HTML generated by marketing or webmail tools.
    if cleaned_text_body:
        return cleaned_text_body, "plain", "text/plain"
    if markdown_body:
        return markdown_body, "markdown", "text/html"
    return None, None, None


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


class EmailMarkdownConverter(MarkdownConverter):
    """Custom Markdown converter tuned for noisy email HTML."""

    def convert_img(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        alt = " ".join(el.get("alt", "").split())
        if alt.lower() in GENERIC_IMAGE_ALTS:
            return ""
        return alt


def _is_hidden_tag(tag: Tag) -> bool:
    if getattr(tag, "attrs", None) is None:
        return False
    if tag.has_attr("hidden"):
        return True

    aria_hidden = str(tag.get("aria-hidden", "")).strip().lower()
    if aria_hidden == "true":
        return True

    style = str(tag.get("style", "")).strip().lower()
    return any(pattern in style for pattern in HIDDEN_STYLE_PATTERNS)


def _is_tracking_image(tag: Tag) -> bool:
    if getattr(tag, "attrs", None) is None:
        return False
    if tag.name != "img":
        return False

    width = str(tag.get("width", "")).strip().lower()
    height = str(tag.get("height", "")).strip().lower()
    if width in TRACKING_PIXEL_DIMENSIONS and height in TRACKING_PIXEL_DIMENSIONS:
        return True

    style = str(tag.get("style", "")).strip().lower()
    return (
        "width:1px" in style
        or "width: 1px" in style
        or "height:1px" in style
        or "height: 1px" in style
    )


def _is_quoted_reply_container(tag: Tag) -> bool:
    if getattr(tag, "attrs", None) is None:
        return False
    classes = " ".join(tag.get("class", [])).lower()
    tag_id = str(tag.get("id", "")).lower()

    if any(pattern in classes for pattern in QUOTED_CONTAINER_PATTERNS):
        return True
    if any(pattern in tag_id for pattern in QUOTED_CONTAINER_PATTERNS):
        return True

    if tag.name != "blockquote":
        return False

    preview = tag.get_text(" ", strip=True)[:500].lower()
    return bool(
        re.search(
            r"\bon .+ wrote:|\bfrom:\b|\bsent:\b|\bsubject:\b|\bto:\b|-----original message-----",
            preview,
        )
    )
