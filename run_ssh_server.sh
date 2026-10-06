#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON_BIN=${KAGGLE_PYTHON:-$(command -v python3)}
if ! command -v ngrok >/dev/null; then
    echo "Run install_ssh_server.sh and add_ngrok_token.sh first." >&2
    exit 1
fi
ngrok config check
exec "$PYTHON_BIN" -u "$SCRIPT_DIR/ssh_tunnel.py"
