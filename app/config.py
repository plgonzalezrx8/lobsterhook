"""Configuration loading and validation for Lobsterhook."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from app.models import AccountRoute, AppSettings, RuntimeConfig

DEFAULT_CONFIG_PATHS = (
    Path("lobsterhook.toml"),
    Path.home() / ".config" / "lobsterhook" / "config.toml",
)


class ConfigError(ValueError):
    """Raised when the Lobsterhook config file is invalid."""


def resolve_config_path(path: str | Path | None) -> Path:
    """Locate the first usable config path when the caller does not provide one."""

    if path is not None:
        candidate = Path(path).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Config file does not exist: {candidate}")
        return candidate

    for candidate in DEFAULT_CONFIG_PATHS:
        expanded = candidate.expanduser().resolve()
        if expanded.exists():
            return expanded

    searched = ", ".join(str(item) for item in DEFAULT_CONFIG_PATHS)
    raise FileNotFoundError(f"No config file found. Checked: {searched}")


def load_config(path: str | Path | None = None) -> RuntimeConfig:
    """Load the file-based runtime configuration."""

    config_path = resolve_config_path(path)
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)

    app_table = payload.get("app", {})
    accounts_table = payload.get("accounts")
    if not isinstance(accounts_table, list) or not accounts_table:
        raise ConfigError("Config must define at least one [[accounts]] entry.")

    app_settings = AppSettings(
        data_dir=_resolve_path(app_table.get("data_dir", "./data"), config_path.parent),
        himalaya_bin=str(app_table.get("himalaya_bin", "himalaya")),
        himalaya_config=_optional_path(app_table.get("himalaya_config"), config_path.parent),
        poll_interval_seconds=_positive_int(app_table.get("poll_interval_seconds", 60), "poll_interval_seconds"),
        page_size=_positive_int(app_table.get("page_size", 50), "page_size"),
        scan_page_cap=_positive_int(app_table.get("scan_page_cap", 10), "scan_page_cap"),
        scan_lookback_seconds=_positive_int(
            app_table.get("scan_lookback_seconds", 300),
            "scan_lookback_seconds",
        ),
        dispatcher_batch_size=_positive_int(
            app_table.get("dispatcher_batch_size", 10),
            "dispatcher_batch_size",
        ),
        http_timeout_seconds=_positive_int(app_table.get("http_timeout_seconds", 30), "http_timeout_seconds"),
        initial_backoff_seconds=_positive_int(
            app_table.get("initial_backoff_seconds", 30),
            "initial_backoff_seconds",
        ),
        max_backoff_seconds=_positive_int(
            app_table.get("max_backoff_seconds", 900),
            "max_backoff_seconds",
        ),
        max_attempts=_positive_int(app_table.get("max_attempts", 5), "max_attempts"),
        user_agent=str(app_table.get("user_agent", "lobsterhook/0.1.0")),
    )

    accounts: dict[str, AccountRoute] = {}
    for entry in accounts_table:
        account = _parse_account(entry, config_path.parent)
        if account.name in accounts:
            raise ConfigError(f"Duplicate account config: {account.name}")
        accounts[account.name] = account

    return RuntimeConfig(config_path=config_path, app=app_settings, accounts=accounts)


def resolve_bearer_token(account: AccountRoute) -> str:
    """Resolve an account token from inline, env, or file-backed config."""

    if account.bearer_token:
        return account.bearer_token

    if account.bearer_token_env:
        value = os.getenv(account.bearer_token_env)
        if not value:
            raise ConfigError(
                f"Environment variable {account.bearer_token_env!r} is not set for account {account.name!r}."
            )
        return value

    if account.bearer_token_file:
        if not account.bearer_token_file.exists():
            raise ConfigError(
                f"Bearer token file does not exist for account {account.name!r}: {account.bearer_token_file}"
            )
        return account.bearer_token_file.read_text(encoding="utf-8").strip()

    raise ConfigError(f"Account {account.name!r} does not define a bearer token source.")


def _parse_account(entry: object, base_dir: Path) -> AccountRoute:
    if not isinstance(entry, dict):
        raise ConfigError("Each [[accounts]] entry must be a TOML table.")

    name = str(entry.get("name", "")).strip()
    if not name:
        raise ConfigError("Each [[accounts]] entry must include a non-empty `name`.")

    folders_value = entry.get("folders", ["INBOX"])
    if not isinstance(folders_value, list) or not folders_value:
        raise ConfigError(f"Account {name!r} must define a non-empty `folders` list.")

    folders = tuple(str(item) for item in folders_value)
    webhook_url = str(entry.get("webhook_url", "")).strip()
    if not webhook_url:
        raise ConfigError(f"Account {name!r} must define `webhook_url`.")

    token_sources = [
        entry.get("bearer_token"),
        entry.get("bearer_token_env"),
        entry.get("bearer_token_file"),
    ]
    if sum(value is not None for value in token_sources) != 1:
        raise ConfigError(
            f"Account {name!r} must define exactly one of `bearer_token`, "
            "`bearer_token_env`, or `bearer_token_file`."
        )

    return AccountRoute(
        name=name,
        folders=folders,
        webhook_url=webhook_url,
        payload_mode=_payload_mode(entry.get("payload_mode", "full"), name),
        bearer_token=entry.get("bearer_token"),
        bearer_token_env=entry.get("bearer_token_env"),
        bearer_token_file=_optional_path(entry.get("bearer_token_file"), base_dir),
        enabled=bool(entry.get("enabled", True)),
    )


def _resolve_path(raw_value: str | Path, base_dir: Path) -> Path:
    value = Path(raw_value).expanduser()
    if value.is_absolute():
        return value.resolve()
    return (base_dir / value).resolve()


def _optional_path(raw_value: str | Path | None, base_dir: Path) -> Path | None:
    if raw_value is None:
        return None
    if raw_value == "":
        return None
    return _resolve_path(raw_value, base_dir)


def _positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{field_name} must be an integer.")
    if not isinstance(value, (int, str)):
        raise ConfigError(f"{field_name} must be an integer.")

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer.") from exc

    if number <= 0:
        raise ConfigError(f"{field_name} must be greater than zero.")
    return number


def _payload_mode(value: object, account_name: str) -> str:
    mode = str(value).strip().lower()
    if mode not in {"full", "minimal"}:
        raise ConfigError(
            f"Account {account_name!r} must define payload_mode as either 'full' or 'minimal'."
        )
    return mode
