#!/usr/bin/env bash
# Run only in a disposable Linux container (see the GitHub Actions workflow).
set -euo pipefail
if [[ ! -f /.dockerenv ]]; then
    echo "Run this integration test inside a disposable Docker container." >&2
    exit 1
fi
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server curl ca-certificates python3 sshpass
export KAGGLE_PYTHON
KAGGLE_PYTHON=$(command -v python3)
export SSH_PORT=2222
export SSH_PASSWORD='integration-only ! $ " : password'
export LD_LIBRARY_PATH='/test/gpu/lib64'
export PYTHONPATH='/test/notebook packages:/test/with#hash'
export CUDA_VISIBLE_DEVICES='0,1'

# Reproduce the reported Kaggle failure: package installed, host keys missing.
"$KAGGLE_PYTHON" - <<'PY'
from pathlib import Path
for path in Path('/etc/ssh').glob('ssh_host_*'):
    path.unlink()
PY
bash install_ssh_server.sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub > /tmp/host-key-before

# Assert the effective configuration, not just the source text.
/usr/sbin/sshd -T -f /etc/ssh/sshd_config_kaggle > /tmp/ssh-effective-config
grep -qx 'permitrootlogin yes' /tmp/ssh-effective-config
grep -qx 'passwordauthentication yes' /tmp/ssh-effective-config
grep -qx 'allowtcpforwarding yes' /tmp/ssh-effective-config

SSH_ARGS=(-p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
          -o PreferredAuthentications=password -o PubkeyAuthentication=no)
export SSHPASS="$SSH_PASSWORD"
sshpass -e ssh "${SSH_ARGS[@]}" root@127.0.0.1 \
    'python3 -c "import os,sys; assert os.environ[\"LD_LIBRARY_PATH\"].startswith(\"/test/gpu/lib64\"); assert os.environ[\"CUDA_VISIBLE_DEVICES\"] == \"0,1\"; assert \"/test/notebook packages\" in sys.path; assert os.environ[\"KAGGLE_PYTHON\"] == sys.executable; print(sys.version)"'
if SSHPASS=wrong-password sshpass -e ssh "${SSH_ARGS[@]}" root@127.0.0.1 true; then
    echo "Wrong password was accepted!" >&2
    exit 1
fi
# VS Code needs file transfer as well as remote commands.
printf 'ls /kaggle\nquit\n' > /tmp/sftp-commands
mkdir -p /kaggle/working
sshpass -e sftp -P "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    root@127.0.0.1 < /tmp/sftp-commands

# Repeated setup must preserve host identity and avoid duplicate profile hooks.
bash install_ssh_server.sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub > /tmp/host-key-after
cmp /tmp/host-key-before /tmp/host-key-after
sshpass -e ssh "${SSH_ARGS[@]}" root@127.0.0.1 'bash -lc "python3 -c '\''import sys; print(sys.executable)'\''"'
"$KAGGLE_PYTHON" - <<'PY'
from pathlib import Path
from ssh_environment import PROFILE_SOURCE
for filename in ('.bashrc', '.profile'):
    assert (Path('/root') / filename).read_text().splitlines().count(PROFILE_SOURCE) == 1
PY

if NGROK_AUTHTOKEN='' bash add_ngrok_token.sh YOUR_NGROK_TOKEN; then
    echo "Placeholder ngrok token was accepted!" >&2
    exit 1
fi
# Config-only validation uses a dummy token and never opens a public tunnel.
NGROK_AUTHTOKEN=integration-config-only bash add_ngrok_token.sh
python3 -m unittest discover -s tests -v
echo 'Linux SSH integration passed.'
