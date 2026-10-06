#!/usr/bin/env bash
set -euo pipefail

TOKEN=${NGROK_AUTHTOKEN:-${1:-}}
if [[ -z "$TOKEN" || "$TOKEN" == YOUR_NGROK_TOKEN || "$TOKEN" == *[[:space:]]* ]]; then
    echo "Set NGROK_AUTHTOKEN using Kaggle Secrets before running this script." >&2
    exit 1
fi
if ! command -v ngrok >/dev/null; then
    echo "Run install_ssh_server.sh first." >&2
    exit 1
fi
umask 077
ngrok config add-authtoken "$TOKEN"
ngrok config check
