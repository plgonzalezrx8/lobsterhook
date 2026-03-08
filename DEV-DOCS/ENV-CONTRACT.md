# Environment Contract

## Purpose
Document the local tools, files, and runtime inputs required to run Lobsterhook.

## Required Binaries
- `python3` 3.14+
- `uv`
- `himalaya` 1.2.x

## Required Local Files
- A Lobsterhook config file at `./lobsterhook.toml` or `~/.config/lobsterhook/config.toml`
- A working Himalaya config file, usually `~/.config/himalaya/config.toml`, unless `app.himalaya_config` points elsewhere

## Required Config Keys
- `[app].data_dir`
- one or more `[[accounts]]`
- `[[accounts]].name`
- `[[accounts]].folders`
- `[[accounts]].webhook_url`
- exactly one bearer token source per account

## Supported Secret Sources
- `bearer_token`
- `bearer_token_env`
- `bearer_token_file`

## Runtime State
- SQLite database: `data/lobsterhook.db`
- Raw messages: `data/raw/`
- Normalized payloads: `data/normalized/`
- Event manifests: `data/events/`
- Temporary exports: `data/tmp/`
- Service logs: `data/logs/`

## Service Expectations
- `scripts/run-poller.sh` expects `LOBSTERHOOK_CONFIG` or a root-level `lobsterhook.toml`
- `scripts/run-dispatcher.sh` expects the same config path contract
- `launchd/*.plist` files are templates and require replacing `__REPO_ROOT__`
