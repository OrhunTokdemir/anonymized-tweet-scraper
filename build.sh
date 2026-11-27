#!/usr/bin/env bash
# Thin wrapper around build.py (the real, cross-platform build script).
# Usage: ./build.sh            same as: .venv/bin/python build.py
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
    echo "No .venv found. Create it first:  python3 -m venv .venv" >&2
    exit 1
fi

exec .venv/bin/python build.py "$@"
