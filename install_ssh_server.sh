#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $(uname -s) != Linux ]]; then
    echo "This script must run inside your Kaggle Linux notebook." >&2
    exit 1
fi
if (( EUID != 0 )); then
    exec sudo -E bash "$SCRIPT_DIR/install_ssh_server.sh" "$@"
fi

# The notebook passes secrets through the environment, never shell interpolation.
PASSWORD=${SSH_PASSWORD:-${1:-}}
if [[ -z "$PASSWORD" || "$PASSWORD" == *$'\n'* || "$PASSWORD" == *$'\r'* ]]; then
    echo "Set SSH_PASSWORD to a nonempty, single-line password." >&2
    exit 1
fi
PYTHON_BIN=${KAGGLE_PYTHON:-$(command -v python3)}
SSH_PORT=${SSH_PORT:-22}
if [[ ! "$SSH_PORT" =~ ^[0-9]+$ ]] || (( SSH_PORT < 1 || SSH_PORT > 65535 )); then
    echo "SSH_PORT must be a number between 1 and 65535." >&2
    exit 1
fi
export SSH_PORT
trap 'echo "SSH setup failed. Check the error above and /var/log/kaggle-sshd.log." >&2' ERR

# apt installing an already installed package does NOT restore missing host keys.
if [[ ! -x /usr/sbin/sshd ]] || ! command -v curl >/dev/null; then
    apt-get update --allow-releaseinfo-change
    DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server curl ca-certificates
fi
echo "Generating missing SSH host keys..."
mkdir -p /run/sshd
chmod 0755 /run/sshd
ssh-keygen -A
printf 'root:%s\n' "$PASSWORD" | chpasswd
unset PASSWORD SSH_PASSWORD

# Always install the current ngrok v3 binary, including in persisted workspaces.
case $(uname -m) in
    x86_64) NGROK_ARCH=amd64 ;;
    aarch64|arm64) NGROK_ARCH=arm64 ;;
    *) echo "Unsupported ngrok architecture: $(uname -m)" >&2; exit 1 ;;
esac
DOWNLOAD_DIR=$(mktemp -d)
trap 'rm -rf -- "$DOWNLOAD_DIR"' EXIT
echo "Installing the current ngrok agent..."
curl --fail --silent --show-error --location --retry 3 --connect-timeout 20 \
    "https://bin.ngrok.com/c/bNyj1mQVY4c/ngrok-v3-stable-linux-${NGROK_ARCH}.tgz" \
    -o "$DOWNLOAD_DIR/ngrok.tgz"
tar -xzf "$DOWNLOAD_DIR/ngrok.tgz" -C "$DOWNLOAD_DIR" ngrok
install -m 0755 "$DOWNLOAD_DIR/ngrok" /usr/local/bin/ngrok
/usr/local/bin/ngrok version

# A separate config avoids image defaults overriding password/root login.
"$PYTHON_BIN" "$SCRIPT_DIR/ssh_environment.py"
CONFIG_FILE=/etc/ssh/sshd_config_kaggle
/usr/sbin/sshd -t -f "$CONFIG_FILE"

# Kaggle containers do not require systemd. Stop the distro daemon if present,
# then restart only this project's listener; existing SSH sessions stay alive.
if command -v service >/dev/null; then
    service ssh stop >/dev/null 2>&1 || true
fi
if [[ -r /run/kaggle-sshd.pid ]]; then
    read -r SSHD_PID < /run/kaggle-sshd.pid
    if [[ "$SSHD_PID" =~ ^[0-9]+$ && -r "/proc/$SSHD_PID/comm" ]] \
        && [[ $(< "/proc/$SSHD_PID/comm") == sshd ]]; then
        kill "$SSHD_PID"
        for _ in {1..20}; do
            kill -0 "$SSHD_PID" 2>/dev/null || break
            sleep 0.1
        done
    fi
fi
/usr/sbin/sshd -f "$CONFIG_FILE" -E /var/log/kaggle-sshd.log
"$PYTHON_BIN" - "$SSH_PORT" <<'PY'
import socket
import sys
import time

for attempt in range(20):
    try:
        with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=2) as sock:
            if not sock.recv(256).startswith(b"SSH-2.0-"):
                raise RuntimeError("The listener did not return an SSH banner.")
        break
    except OSError:
        if attempt == 19:
            raise
        time.sleep(0.1)
print(f"SSH is ready on 127.0.0.1:{sys.argv[1]}.")
PY
