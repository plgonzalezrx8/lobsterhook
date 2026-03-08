"""Filesystem storage helpers for raw messages, normalized payloads, and events."""

from __future__ import annotations

import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class StorageManager:
    """Own the local artifact layout under the data directory."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.raw_dir = self.data_dir / "raw"
        self.normalized_dir = self.data_dir / "normalized"
        self.events_dir = self.data_dir / "events"
        self.logs_dir = self.data_dir / "logs"
        self.tmp_dir = self.data_dir / "tmp"

    def ensure_layout(self) -> None:
        for directory in (
            self.data_dir,
            self.raw_dir,
            self.normalized_dir,
            self.events_dir,
            self.logs_dir,
            self.tmp_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def build_message_paths(
        self,
        *,
        account: str,
        folder: str,
        remote_id: str,
        year: str,
        month: str,
    ) -> tuple[Path, Path, Path]:
        """Partition persisted artifacts by account, folder, and message month."""

        account_name = _safe_component(account)
        folder_name = _safe_component(folder)
        file_name = f"{_safe_component(remote_id)}"
        raw_path = self.raw_dir / account_name / folder_name / year / month / f"{file_name}.eml"
        normalized_path = self.normalized_dir / account_name / folder_name / year / month / f"{file_name}.json"
        event_path = self.events_dir / year / month / f"{account_name}-{folder_name}-{file_name}.json"
        return raw_path, normalized_path, event_path

    def create_temporary_eml_path(self, remote_id: str) -> Path:
        """Export into a temporary file before promoting it into the final tree."""

        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(prefix=f"{_safe_component(remote_id)}-", suffix=".eml", dir=self.tmp_dir, delete=False) as handle:
            return Path(handle.name)

    def promote_raw_message(self, temporary_path: Path, final_path: Path) -> None:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.replace(final_path)

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(path)


def _safe_component(value: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return compact or "unknown"
