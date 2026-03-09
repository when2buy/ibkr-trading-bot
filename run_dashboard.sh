#!/usr/bin/env bash
# Start the IBKR Trading Dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Install flask if needed
pip install -q flask 2>/dev/null

echo "Starting IBKR Trading Dashboard on http://0.0.0.0:8050"
python dashboard/app.py
