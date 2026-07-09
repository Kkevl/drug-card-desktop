#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

check_python_version() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
        echo "Python 3.9 or newer is required."
        echo "Current Python:"
        "$1" --version || true
        exit 1
    }
}

if [ ! -x ".venv/bin/python" ]; then
    check_python_version "$PYTHON_BIN"
    "$PYTHON_BIN" -m venv .venv
fi

check_python_version ".venv/bin/python"
".venv/bin/python" -m pip install -r requirements.txt
".venv/bin/python" -m PyInstaller --noconfirm --windowed --name DrugFlashcard main.py
