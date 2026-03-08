from __future__ import annotations

import json
from pathlib import Path

from app.config import load_config
from app.db import Database
from app.dispatcher import MINIMAL_WEBHOOK_FIELD_ORDER, WebhookDispatcher

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "webhook_payloads"


def _write_config(tmp_path: Path, payload_mode: str) -> Path:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        f"""
        [app]
        data_dir = "./data"

        [[accounts]]
        name = "support"
        folders = ["INBOX"]
        webhook_url = "https://example.com/webhook"
        payload_mode = "{payload_mode}"
        bearer_token = "secret-token"
        """,
        encoding="utf-8",
    )
    return config_path


def _load_json_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_dispatcher_uses_minimal_payload_shape(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, "minimal"))
    dispatcher = WebhookDispatcher(config=config, database=Database(config.app.database_path))
    normalized_payload = _load_json_fixture("normalized_payload_input.json")
    expected_payload = _load_json_fixture("minimal_payload_expected.v1.json")

    payload = dispatcher._build_webhook_payload("minimal", normalized_payload)

    assert payload == expected_payload
    assert tuple(payload.keys()) == MINIMAL_WEBHOOK_FIELD_ORDER


def test_dispatcher_preserves_full_payload_mode(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, "full"))
    dispatcher = WebhookDispatcher(config=config, database=Database(config.app.database_path))
    normalized_payload = _load_json_fixture("normalized_payload_input.json")
    expected_payload = _load_json_fixture("full_payload_expected.v1.json")

    payload = dispatcher._build_webhook_payload("full", normalized_payload)

    assert payload == expected_payload
    assert payload is normalized_payload


def test_dispatcher_minimal_mode_preserves_contract_when_optional_fields_are_missing(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path, "minimal"))
    dispatcher = WebhookDispatcher(config=config, database=Database(config.app.database_path))
    normalized_payload: dict[str, object] = {
        "account": "support",
        "folder": "INBOX",
        "remote_id": "42",
        "detected_at": "2026-03-08T12:00:00+00:00",
    }

    payload = dispatcher._build_webhook_payload("minimal", normalized_payload)

    assert tuple(payload.keys()) == MINIMAL_WEBHOOK_FIELD_ORDER
    assert payload["from"] == {"name": None, "address": None}
    assert payload["return_path"] is None
    assert payload["subject"] is None
    assert payload["message"] is None
    assert payload["message_format"] is None
    assert payload["message_source"] is None
