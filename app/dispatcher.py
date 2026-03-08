"""Outbound webhook dispatcher for queued Lobsterhook events."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib import error, request

from app.config import RuntimeConfig, resolve_bearer_token
from app.db import Database
from app.models import DeliveryResult

LOGGER = logging.getLogger(__name__)


class WebhookDispatcher:
    """Deliver queued normalized-message payloads to configured webhook URLs."""

    def __init__(self, *, config: RuntimeConfig, database: Database) -> None:
        self.config = config
        self.database = database

    def run_forever(self) -> None:
        """Dispatch until the process is terminated."""

        while True:
            processed = self.run_once()
            if processed == 0:
                time.sleep(self.config.app.poll_interval_seconds)

    def run_once(self) -> int:
        """Process one dispatcher batch."""

        self.database.initialize()
        now_iso = _utcnow().isoformat()
        jobs = self.database.get_due_jobs(now_iso, self.config.app.dispatcher_batch_size)
        processed = 0

        for job in jobs:
            claimed = self.database.claim_job(job["id"], _utcnow().isoformat())
            if claimed is None:
                continue
            processed += 1
            try:
                self._deliver_job(claimed)
            except Exception as exc:
                LOGGER.exception("Dispatcher crashed while handling job %s", claimed["id"])
                self._handle_internal_failure(claimed, str(exc))

        return processed

    def _deliver_job(self, job: object) -> None:
        payload = json.loads(job["payload_json"])
        account = self.config.accounts[payload["account"]]
        token = resolve_bearer_token(account)
        normalized_path = Path(payload["normalized_path"])
        normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
        webhook_payload = self._build_webhook_payload(account.payload_mode, normalized_payload)

        result = self._post_payload(account.webhook_url, token, webhook_payload)
        attempt_number = int(job["attempts"])
        requested_at = _utcnow().isoformat()
        self.database.record_delivery_attempt(
            job_id=job["id"],
            attempt_number=attempt_number,
            requested_at=requested_at,
            response_status=result.status_code,
            response_body=result.response_body,
            error=result.error,
        )

        if result.status_code is not None and 200 <= result.status_code < 300:
            self.database.mark_job_done(
                job_id=job["id"],
                finished_at=requested_at,
                response_status=result.status_code,
                response_body=result.response_body,
                account=payload["account"],
                folder=payload["folder"],
                remote_id=payload["remote_id"],
            )
            return

        should_retry = self._should_retry(result.status_code, result.error)
        attempts = int(job["attempts"])
        dead_letter = attempts >= self.config.app.max_attempts or not should_retry
        available_at = requested_at
        if not dead_letter:
            available_at = self._next_available_time(attempts).isoformat()

        error_message = result.error or f"Webhook returned HTTP {result.status_code}"
        self.database.reschedule_job(
            job_id=job["id"],
            available_at=available_at,
            error=error_message,
            response_status=result.status_code,
            response_body=result.response_body,
            dead_letter=dead_letter,
            finished_at=requested_at,
            account=payload["account"],
            folder=payload["folder"],
            remote_id=payload["remote_id"],
        )

    def _handle_internal_failure(self, job: object, error_message: str) -> None:
        payload = json.loads(job["payload_json"])
        attempts = int(job["attempts"])
        dead_letter = attempts >= self.config.app.max_attempts
        available_at = _utcnow().isoformat()
        if not dead_letter:
            available_at = self._next_available_time(attempts).isoformat()

        self.database.record_delivery_attempt(
            job_id=job["id"],
            attempt_number=attempts,
            requested_at=_utcnow().isoformat(),
            response_status=None,
            response_body=None,
            error=error_message,
        )
        self.database.reschedule_job(
            job_id=job["id"],
            available_at=available_at,
            error=error_message,
            response_status=None,
            response_body=None,
            dead_letter=dead_letter,
            finished_at=_utcnow().isoformat(),
            account=payload["account"],
            folder=payload["folder"],
            remote_id=payload["remote_id"],
        )

    def _post_payload(self, url: str, token: str, payload: dict[str, object]) -> DeliveryResult:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": self.config.app.user_agent,
        }
        req = request.Request(url=url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.config.app.http_timeout_seconds) as response:
                return DeliveryResult(
                    status_code=response.status,
                    response_body=response.read().decode("utf-8", errors="replace"),
                )
        except error.HTTPError as exc:
            return DeliveryResult(
                status_code=exc.code,
                response_body=exc.read().decode("utf-8", errors="replace"),
                error=f"HTTP {exc.code}",
            )
        except error.URLError as exc:
            return DeliveryResult(status_code=None, response_body=None, error=str(exc.reason))

    def _build_webhook_payload(self, payload_mode: str, normalized_payload: dict[str, object]) -> dict[str, object]:
        if payload_mode == "full":
            return normalized_payload

        sender = normalized_payload.get("sender") or {"name": None, "address": None}
        return {
            "account": normalized_payload.get("account"),
            "folder": normalized_payload.get("folder"),
            "remote_id": normalized_payload.get("remote_id"),
            "detected_at": normalized_payload.get("detected_at"),
            "return_path": normalized_payload.get("return_path"),
            "date": normalized_payload.get("date"),
            "from": sender,
            "to": normalized_payload.get("to"),
            "subject": normalized_payload.get("subject"),
            "message": normalized_payload.get("preferred_message"),
            "message_format": normalized_payload.get("preferred_message_format"),
            "message_source": normalized_payload.get("preferred_message_source"),
        }

    def _should_retry(self, status_code: int | None, error_message: str | None) -> bool:
        if status_code is None:
            return True
        if status_code in {408, 429}:
            return True
        if 500 <= status_code < 600:
            return True
        if error_message and "timed out" in error_message.lower():
            return True
        return False

    def _next_available_time(self, attempts: int) -> datetime:
        # Exponential backoff keeps a noisy receiver from being hammered while
        # still making retries deterministic and bounded.
        delay = min(
            self.config.app.initial_backoff_seconds * (2 ** max(0, attempts - 1)),
            self.config.app.max_backoff_seconds,
        )
        return _utcnow() + timedelta(seconds=delay)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)
