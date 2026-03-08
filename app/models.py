"""Shared runtime models for Lobsterhook."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppSettings:
    """Application-level configuration shared by all runtime modes."""

    data_dir: Path
    himalaya_bin: str
    himalaya_config: Path | None
    poll_interval_seconds: int
    page_size: int
    scan_page_cap: int
    scan_lookback_seconds: int
    dispatcher_batch_size: int
    http_timeout_seconds: int
    initial_backoff_seconds: int
    max_backoff_seconds: int
    max_attempts: int
    user_agent: str

    @property
    def database_path(self) -> Path:
        """Keep the SQLite location deterministic under the data root."""

        return self.data_dir / "lobsterhook.db"


@dataclass(frozen=True)
class AccountRoute:
    """Per-account routing and secret resolution inputs."""

    name: str
    folders: tuple[str, ...]
    webhook_url: str
    bearer_token: str | None = None
    bearer_token_env: str | None = None
    bearer_token_file: Path | None = None
    enabled: bool = True


@dataclass(frozen=True)
class RuntimeConfig:
    """Fully parsed runtime configuration."""

    config_path: Path
    app: AppSettings
    accounts: dict[str, AccountRoute]


@dataclass(frozen=True)
class Envelope:
    """Compact metadata returned by `himalaya envelope list --output json`."""

    account: str
    folder: str
    remote_id: str
    subject: str | None
    sender_name: str | None
    sender_address: str | None
    recipient_name: str | None
    recipient_address: str | None
    date: str | None
    flags: tuple[str, ...] = ()
    has_attachment: bool = False


@dataclass(frozen=True)
class AttachmentMetadata:
    """Normalized attachment metadata included in webhook payloads."""

    filename: str | None
    content_type: str
    content_id: str | None
    disposition: str | None
    size_bytes: int


@dataclass(frozen=True)
class NormalizedMessage:
    """Portable JSON representation built from a raw `.eml` file."""

    account: str
    folder: str
    remote_id: str
    remote_id_kind: str
    detected_at: str
    message_id: str | None
    in_reply_to: list[str]
    references: list[str]
    thread_key: str
    subject: str | None
    sent_at: str | None
    sender: dict[str, str | None]
    to: list[dict[str, str | None]]
    cc: list[dict[str, str | None]]
    bcc: list[dict[str, str | None]]
    reply_to: list[dict[str, str | None]]
    text_body: str | None
    html_body: str | None
    attachments: list[AttachmentMetadata]
    headers: dict[str, list[str]]
    body_hash: str
    raw_path: str
    normalized_path: str
    exported_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert nested dataclasses into plain JSON-compatible structures."""

        payload = asdict(self)
        payload["attachments"] = [asdict(item) for item in self.attachments]
        return payload


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of one webhook delivery attempt."""

    status_code: int | None
    response_body: str | None
    error: str | None = None


@dataclass(frozen=True)
class JobPayload:
    """Small durable payload stored in the jobs table."""

    account: str
    folder: str
    remote_id: str
    normalized_path: str
    event_payload_path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Expose a JSON-serializable version for SQLite storage."""

        return {
            "account": self.account,
            "folder": self.folder,
            "remote_id": self.remote_id,
            "normalized_path": self.normalized_path,
            "event_payload_path": self.event_payload_path,
            "metadata": self.metadata,
        }
