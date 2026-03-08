#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${LOBSTERHOOK_CONFIG:-${ROOT_DIR}/lobsterhook.toml}"

cd "${ROOT_DIR}"
uv run lobsterhook --config "${CONFIG_PATH}" poller
