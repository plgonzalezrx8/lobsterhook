"""Mailbox poller that ingests unseen emails into local state and queue jobs."""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import RuntimeConfig
from app.db import Database
from app.himalaya_adapter import HimalayaAdapter, HimalayaAdapterError
from app.models import Envelope, JobPayload
from app.normalizer import normalize_email
from app.storage import StorageManager

LOGGER = logging.getLogger(__name__)

REMOTE_ID_KIND = "himalaya_backend_id"


@dataclass(frozen=True)
class PollerSummary:
    """Small return type for logging and tests."""

    processed_messages: int = 0
    failed_mailboxes: int = 0


class MailPoller:
    """Walk configured mailboxes, capture unseen mail, and queue webhook jobs."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        database: Database,
        storage: StorageManager,
        adapter: HimalayaAdapter,
    ) -> None:
        self.config = config
        self.database = database
        self.storage = storage
        self.adapter = adapter

    def run_forever(self) -> None:
        """Poll until the process is terminated."""

        while True:
            summary = self.run_once()
            LOGGER.info(
                "Poll cycle finished: processed=%s failed_mailboxes=%s",
                summary.processed_messages,
                summary.failed_mailboxes,
            )
            time.sleep(self.config.app.poll_interval_seconds)

    def run_once(self) -> PollerSummary:
        """Scan every configured mailbox once."""

        processed_total = 0
        failed_mailboxes = 0
        self.storage.ensure_layout()
        self.database.initialize()

        for account in self.config.accounts.values():
            if not account.enabled:
                continue
            for folder in account.folders:
                try:
                    processed_total += self._scan_mailbox(account.name, folder)
                except HimalayaAdapterError:
                    failed_mailboxes += 1
                    LOGGER.exception("Himalaya failed while scanning %s/%s", account.name, folder)
                except Exception:
                    failed_mailboxes += 1
                    LOGGER.exception("Unexpected polling failure for %s/%s", account.name, folder)

        return PollerSummary(processed_messages=processed_total, failed_mailboxes=failed_mailboxes)

    def _scan_mailbox(self, account: str, folder: str) -> int:
        started_at = _utcnow()
        started_at_iso = started_at.isoformat()
        self.database.ensure_mailbox(account, folder, started_at_iso)
        self.database.mark_scan_started(account, folder, started_at_iso)

        mailbox = self.database.get_mailbox(account, folder)
        last_success = _parse_iso(mailbox["last_successful_scan_at"]) if mailbox and mailbox["last_successful_scan_at"] else None
        cutoff = last_success - timedelta(seconds=self.config.app.scan_lookback_seconds) if last_success else None

        processed = 0
        scan_successful = True
        for page in range(1, self.config.app.scan_page_cap + 1):
            envelopes = self.adapter.list_envelopes(
                account=account,
                folder=folder,
                page=page,
                page_size=self.config.app.page_size,
            )
            if not envelopes:
                break

            page_all_known = True
            page_old_enough = cutoff is not None
            for envelope in envelopes:
                envelope_date = _parse_iso(envelope.date)
                if cutoff is None or envelope_date is None or envelope_date > cutoff:
                    page_old_enough = False

                if self.database.message_exists(account, folder, envelope.remote_id):
                    continue

                page_all_known = False
                try:
                    self._ingest_envelope(envelope)
                    processed += 1
                except sqlite3.IntegrityError:
                    LOGGER.warning("Duplicate insert skipped for %s/%s/%s", account, folder, envelope.remote_id)
                except Exception:
                    scan_successful = False
                    LOGGER.exception("Failed to ingest %s/%s/%s", account, folder, envelope.remote_id)

            # Stop only when the entire page is known and clearly older than the
            # lookback cutoff; this preserves a safety buffer for delayed mail.
            if cutoff is not None and page_all_known and page_old_enough:
                break

        if scan_successful:
            self.database.mark_scan_finished(account, folder, _utcnow().isoformat())

        return processed

    def _ingest_envelope(self, envelope: Envelope) -> None:
        detected_at = _utcnow()
        year = detected_at.strftime("%Y")
        month = detected_at.strftime("%m")
        raw_path, normalized_path, event_path = self.storage.build_message_paths(
            account=envelope.account,
            folder=envelope.folder,
            remote_id=envelope.remote_id,
            year=year,
            month=month,
        )

        temp_raw_path = self.storage.create_temporary_eml_path(envelope.remote_id)
        exported_at_iso = _utcnow().isoformat()
        try:
            self.adapter.export_message(
                account=envelope.account,
                folder=envelope.folder,
                remote_id=envelope.remote_id,
                destination=temp_raw_path,
            )
            self.storage.promote_raw_message(temp_raw_path, raw_path)
        finally:
            if temp_raw_path.exists():
                temp_raw_path.unlink(missing_ok=True)

        normalized = normalize_email(
            account=envelope.account,
            folder=envelope.folder,
            remote_id=envelope.remote_id,
            remote_id_kind=REMOTE_ID_KIND,
            raw_path=raw_path,
            normalized_path=normalized_path,
            detected_at=detected_at.isoformat(),
            exported_at=exported_at_iso,
        )
        normalized_payload = normalized.to_dict()
        self.storage.write_json(normalized_path, normalized_payload)

        event_payload = {
            "event_type": "mail.received",
            "account": envelope.account,
            "folder": envelope.folder,
            "remote_id": envelope.remote_id,
            "detected_at": detected_at.isoformat(),
            "normalized_path": str(normalized_path),
            "raw_path": str(raw_path),
        }
        self.storage.write_json(event_path, event_payload)

        dedupe_key = f"mail.received:{envelope.account}:{envelope.folder}:{envelope.remote_id}"
        job_payload = JobPayload(
            account=envelope.account,
            folder=envelope.folder,
            remote_id=envelope.remote_id,
            normalized_path=str(normalized_path),
            event_payload_path=str(event_path),
        )
        self.database.create_message_event_and_job(
            message={
                "account": envelope.account,
                "folder": envelope.folder,
                "remote_id": envelope.remote_id,
                "remote_id_kind": REMOTE_ID_KIND,
                "message_id": normalized.message_id,
                "thread_key": normalized.thread_key,
                "sender": normalized.sender.get("address"),
                "subject": normalized.subject,
                "received_at": normalized.sent_at or envelope.date,
                "raw_path": str(raw_path),
                "normalized_path": str(normalized_path),
                "body_hash": normalized.body_hash,
                "status": "queued",
            },
            event_type="mail.received",
            event_dedupe_key=dedupe_key,
            payload_path=str(event_path),
            job_type="dispatch_webhook",
            job_payload=job_payload.to_dict(),
            available_at=detected_at.isoformat(),
            created_at=detected_at.isoformat(),
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
