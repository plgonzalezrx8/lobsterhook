from __future__ import annotations

from pathlib import Path

from app.config import load_config
from app.db import Database
from app.models import Envelope
from app.poller import MailPoller
from app.storage import StorageManager


class FakeAdapter:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path
        self.exported_ids: list[str] = []

    def list_envelopes(self, *, account: str, folder: str, page: int, page_size: int) -> list[Envelope]:
        if page == 1:
            return [
                Envelope(
                    account=account,
                    folder=folder,
                    remote_id="42",
                    subject="Testing Lobsterhook",
                    sender_name="Example Sender",
                    sender_address="sender@example.com",
                    recipient_name="Support Team",
                    recipient_address="support@example.com",
                    date="2026-03-08T10:15:00+00:00",
                )
            ]
        return []

    def export_message(self, *, account: str, folder: str, remote_id: str, destination: Path) -> Path:
        self.exported_ids.append(remote_id)
        destination.write_bytes(self.fixture_path.read_bytes())
        return destination


def test_poller_ingests_message_once_and_skips_on_repeat(tmp_path: Path) -> None:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        """
        [app]
        data_dir = "./data"

        [[accounts]]
        name = "support"
        folders = ["INBOX"]
        webhook_url = "https://example.com/webhook"
        bearer_token = "secret-token"
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)
    database = Database(config.app.database_path)
    storage = StorageManager(config.app.data_dir)
    fixture_path = Path(__file__).parent / "fixtures" / "sample_email.eml"
    adapter = FakeAdapter(fixture_path)
    poller = MailPoller(config=config, database=database, storage=storage, adapter=adapter)

    first_summary = poller.run_once()
    second_summary = poller.run_once()

    assert first_summary.processed_messages == 1
    assert second_summary.processed_messages == 0
    assert adapter.exported_ids == ["42"]
    assert database.message_exists("support", "INBOX", "42")
