#!/usr/bin/env bash
set -euo pipefail

# Minimal quality gate for GhIssueWorkflow.
# Keep it fast + deterministic; expand later if needed.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip -q install --upgrade pip

# Ensure test deps exist (repo keeps runtime deps minimal).
python -m pip -q install -e "$ROOT_DIR" pytest

pytest
