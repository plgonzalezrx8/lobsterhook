"""SQL helpers shared by the database layer."""

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    last_successful_scan_at TEXT,
    last_scan_started_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account, folder)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    remote_id_kind TEXT NOT NULL DEFAULT 'backend_id',
    message_id TEXT,
    thread_key TEXT NOT NULL,
    sender TEXT,
    subject TEXT,
    received_at TEXT,
    raw_path TEXT NOT NULL,
    normalized_path TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    processed_at TEXT,
    UNIQUE(account, folder, remote_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    payload_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    job_type TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    last_error TEXT,
    last_response_status INTEGER,
    last_response_body TEXT,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_available ON jobs(status, available_at);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    attempt_number INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    error TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_delivery_attempts_job_id ON delivery_attempts(job_id);
"""
