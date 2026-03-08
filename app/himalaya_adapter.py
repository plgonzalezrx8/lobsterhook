"""Subprocess adapter for Himalaya CLI operations."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from app.models import Envelope


class HimalayaAdapterError(RuntimeError):
    """Raised when a Himalaya subprocess returns invalid data or fails."""


class HimalayaAdapter:
    """Wrap the small Himalaya CLI surface that Lobsterhook relies on."""

    def __init__(self, *, himalaya_bin: str, himalaya_config: Path | None = None) -> None:
        self.himalaya_bin = himalaya_bin
        self.himalaya_config = himalaya_config

    def list_envelopes(self, *, account: str, folder: str, page: int, page_size: int) -> list[Envelope]:
        """List envelope metadata for one mailbox page."""

        command = self._base_command()
        command.extend(
            [
                "--output",
                "json",
                "envelope",
                "list",
                "--account",
                account,
                "--folder",
                folder,
                "--page",
                str(page),
                "--page-size",
                str(page_size),
            ]
        )
        result = self._run(command)
        try:
            payload = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise HimalayaAdapterError(f"Himalaya returned invalid envelope JSON: {exc}") from exc

        if not isinstance(payload, list):
            raise HimalayaAdapterError("Himalaya envelope list payload was not a JSON list.")

        envelopes: list[Envelope] = []
        for item in payload:
            if not isinstance(item, dict):
                raise HimalayaAdapterError("Himalaya envelope list contained a non-object item.")
            envelopes.append(
                Envelope(
                    account=account,
                    folder=folder,
                    remote_id=str(item["id"]),
                    subject=_coerce_text(item.get("subject")),
                    sender_name=_coerce_nested(item.get("from"), "name"),
                    sender_address=_coerce_nested(item.get("from"), "addr"),
                    recipient_name=_coerce_nested(item.get("to"), "name"),
                    recipient_address=_coerce_nested(item.get("to"), "addr"),
                    date=_coerce_text(item.get("date")),
                    flags=tuple(str(flag) for flag in item.get("flags", [])),
                    has_attachment=bool(item.get("has_attachment", False)),
                )
            )
        return envelopes

    def export_message(self, *, account: str, folder: str, remote_id: str, destination: Path) -> Path:
        """Export one raw message to the destination `.eml` path."""

        destination.parent.mkdir(parents=True, exist_ok=True)
        command = self._base_command()
        command.extend(
            [
                "message",
                "export",
                "--full",
                "--account",
                account,
                "--folder",
                folder,
                "--destination",
                str(destination),
                remote_id,
            ]
        )
        self._run(command)
        if not destination.exists():
            raise HimalayaAdapterError(f"Himalaya export completed without creating {destination}.")
        return destination

    def _base_command(self) -> list[str]:
        command = [self.himalaya_bin, "--quiet"]
        if self.himalaya_config is not None:
            command.extend(["--config", str(self.himalaya_config)])
        return command

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["RUST_LOG"] = "off"
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise HimalayaAdapterError(stderr or "Unknown Himalaya error")
        return result


def _coerce_text(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _coerce_nested(value: object, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    nested = value.get(key)
    return _coerce_text(nested)
