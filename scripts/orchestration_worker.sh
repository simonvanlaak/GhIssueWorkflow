#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
CONFIG_PATH="${1:-$ROOT_DIR/config.example.yaml}"

cd "$ROOT_DIR"
git pull --ff-only

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip -q install --upgrade pip
python -m pip -q install -e "$ROOT_DIR"

gh-issue-workflow --config "$CONFIG_PATH" tick
