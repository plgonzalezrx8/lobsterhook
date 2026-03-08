from __future__ import annotations

from pathlib import Path

import pytest

from app.config import ConfigError, load_config, resolve_bearer_token


def test_load_config_resolves_relative_paths_and_env_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        """
        [app]
        data_dir = "./runtime-data"
        himalaya_bin = "himalaya"

        [[accounts]]
        name = "support"
        folders = ["INBOX", "Escalations"]
        webhook_url = "https://example.com/webhook"
        bearer_token_env = "SUPPORT_TOKEN"
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("SUPPORT_TOKEN", "secret-token")

    config = load_config(config_path)

    assert config.app.data_dir == (tmp_path / "runtime-data").resolve()
    assert config.accounts["support"].folders == ("INBOX", "Escalations")
    assert resolve_bearer_token(config.accounts["support"]) == "secret-token"


def test_load_config_requires_one_token_source(tmp_path: Path) -> None:
    config_path = tmp_path / "lobsterhook.toml"
    config_path.write_text(
        """
        [[accounts]]
        name = "support"
        folders = ["INBOX"]
        webhook_url = "https://example.com/webhook"
        """,
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(config_path)
