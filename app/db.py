"""SQLite persistence layer for Lobsterhook."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models_sql import SCHEMA


class Database:
    """Thin SQLite wrapper for mailbox state, events, and delivery jobs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def ensure_mailbox(self, account: str, folder: str, now_iso: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO mailboxes (account, folder, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account, folder) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (account, folder, now_iso, now_iso),
            )

    def get_mailbox(self, account: str, folder: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM mailboxes WHERE account = ? AND folder = ?",
                (account, folder),
            ).fetchone()

    def mark_scan_started(self, account: str, folder: str, started_at: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE mailboxes
                SET last_scan_started_at = ?, updated_at = ?
                WHERE account = ? AND folder = ?
                """,
                (started_at, started_at, account, folder),
            )

    def mark_scan_finished(self, account: str, folder: str, finished_at: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE mailboxes
                SET last_successful_scan_at = ?, updated_at = ?
                WHERE account = ? AND folder = ?
                """,
                (finished_at, finished_at, account, folder),
            )

    def message_exists(self, account: str, folder: str, remote_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM messages
                WHERE account = ? AND folder = ? AND remote_id = ?
                """,
                (account, folder, remote_id),
            ).fetchone()
        return row is not None

    def create_message_event_and_job(
        self,
        *,
        message: dict[str, object],
        event_type: str,
        event_dedupe_key: str,
        payload_path: str,
        job_type: str,
        job_payload: dict[str, object],
        available_at: str,
        created_at: str,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    account,
                    folder,
                    remote_id,
                    remote_id_kind,
                    message_id,
                    thread_key,
                    sender,
                    subject,
                    received_at,
                    raw_path,
                    normalized_path,
                    body_hash,
                    status,
                    created_at,
                    processed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["account"],
                    message["folder"],
                    message["remote_id"],
                    message["remote_id_kind"],
                    message["message_id"],
                    message["thread_key"],
                    message["sender"],
                    message["subject"],
                    message["received_at"],
                    message["raw_path"],
                    message["normalized_path"],
                    message["body_hash"],
                    message["status"],
                    created_at,
                    None,
                ),
            )
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_type,
                    dedupe_key,
                    account,
                    folder,
                    remote_id,
                    payload_path,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    event_dedupe_key,
                    message["account"],
                    message["folder"],
                    message["remote_id"],
                    payload_path,
                    created_at,
                ),
            )
            event_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO jobs (
                    event_id,
                    job_type,
                    dedupe_key,
                    payload_json,
                    status,
                    attempts,
                    available_at,
                    created_at
                )
                VALUES (?, ?, ?, ?, 'queued', 0, ?, ?)
                """,
                (
                    event_id,
                    job_type,
                    event_dedupe_key,
                    json.dumps(job_payload, sort_keys=True),
                    available_at,
                    created_at,
                ),
            )

    def get_due_jobs(self, now_iso: str, limit: int) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'queued'
                  AND available_at <= ?
                ORDER BY available_at ASC, id ASC
                LIMIT ?
                """,
                (now_iso, limit),
            ).fetchall()

    def get_job(self, job_id: int) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def claim_job(self, job_id: int, started_at: str) -> sqlite3.Row | None:
        with self.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    attempts = attempts + 1,
                    started_at = ?
                WHERE id = ?
                  AND status = 'queued'
                """,
                (started_at, job_id),
            )
            if updated.rowcount != 1:
                return None
            return connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def record_delivery_attempt(
        self,
        *,
        job_id: int,
        attempt_number: int,
        requested_at: str,
        response_status: int | None,
        response_body: str | None,
        error: str | None,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO delivery_attempts (
                    job_id,
                    attempt_number,
                    requested_at,
                    response_status,
                    response_body,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, attempt_number, requested_at, response_status, response_body, error),
            )

    def mark_job_done(
        self,
        *,
        job_id: int,
        finished_at: str,
        response_status: int | None,
        response_body: str | None,
        account: str,
        folder: str,
        remote_id: str,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'done',
                    finished_at = ?,
                    last_error = NULL,
                    last_response_status = ?,
                    last_response_body = ?
                WHERE id = ?
                """,
                (finished_at, response_status, _trim_text(response_body), job_id),
            )
            connection.execute(
                """
                UPDATE messages
                SET status = 'delivered',
                    processed_at = ?
                WHERE account = ? AND folder = ? AND remote_id = ?
                """,
                (finished_at, account, folder, remote_id),
            )

    def reschedule_job(
        self,
        *,
        job_id: int,
        available_at: str,
        error: str,
        response_status: int | None,
        response_body: str | None,
        dead_letter: bool,
        finished_at: str,
        account: str,
        folder: str,
        remote_id: str,
    ) -> None:
        next_status = "dead_letter" if dead_letter else "queued"
        message_status = "failed" if dead_letter else "queued"
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    available_at = ?,
                    finished_at = ?,
                    last_error = ?,
                    last_response_status = ?,
                    last_response_body = ?
                WHERE id = ?
                """,
                (
                    next_status,
                    available_at,
                    finished_at,
                    _trim_text(error),
                    response_status,
                    _trim_text(response_body),
                    job_id,
                ),
            )
            connection.execute(
                """
                UPDATE messages
                SET status = ?, processed_at = ?
                WHERE account = ? AND folder = ? AND remote_id = ?
                """,
                (message_status, finished_at if dead_letter else None, account, folder, remote_id),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


def _trim_text(value: str | None, limit: int = 5000) -> str | None:
    if value is None:
        return None
    return value[:limit]
