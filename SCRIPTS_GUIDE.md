# Scripts guide

Run the scripts inside a Kaggle Linux notebook. The notebooks read credentials
from Kaggle Secrets and use `subprocess` with `check=True`, so failed setup stops
execution and passwords are never interpolated into shell commands.

## `install_ssh_server.sh`

Requires `SSH_PASSWORD` in the environment, or an explicit password argument for
older callers. There is no default password. `KAGGLE_PYTHON` selects the notebook
interpreter; the notebook passes `sys.executable`. `SSH_PORT` defaults to `22`.

The script:

1. Installs OpenSSH/curl if needed, creates `/run/sshd`, and runs `ssh-keygen -A`
   to restore missing host keys even if OpenSSH is already installed.
2. Sets the root password without printing it.
3. Downloads the current official ngrok v3 binary for amd64 or arm64.
4. Calls `ssh_environment.py` to generate `/etc/ssh/sshd_config_kaggle` and
   `/etc/profile.d/kaggle-ssh.sh` from the current Python/CUDA environment.
5. Validates the config with `sshd -t`, stops the distro SSH listener if present,
   and starts the project listener directly. This works without systemd.
6. Reads an actual SSH banner before reporting success.

The dedicated configuration enables root/password authentication and TCP
forwarding for VS Code, binds to loopback, and uses internal SFTP. Image defaults
and cloud-init include files cannot override it. Its PID is in
`/run/kaggle-sshd.pid`; diagnostic logs are in `/var/log/kaggle-sshd.log`.

Repeated setup preserves existing host keys and adds each shell environment hook
only once. Environment transfer uses an allowlist; passwords, tokens, and Kaggle
credential variables are excluded. GPU paths are included only when present.

## `add_ngrok_token.sh`

Requires `NGROK_AUTHTOKEN` in the environment, or an explicit token argument for
older callers. Empty tokens and `YOUR_NGROK_TOKEN` are rejected. It saves the
ngrok token using the agent's configuration command, then validates the config.
Configuration files are created with restricted permissions.

## `run_ssh_server.sh` / `ssh_tunnel.py`

Validates ngrok's configuration and checks the local SSH banner before launching
an ngrok TCP tunnel. The deprecated `--region` flag is omitted. The Python helper
reads this agent's JSON startup log to obtain the assigned endpoint and prints a
complete `Host Kaggle` block. It does not read another agent's endpoint or kill
unrelated ngrok processes.

Startup times out after 60 seconds. ngrok failures are shown in the cell and
return a failure status. Interrupting the notebook's last cell stops its process
group and cleans up the tunnel. Keep the cell running during the connection.

## Notebook maintenance

Both notebooks clone/update `NguyenQuocDat06-AI/remote-ssh-kaggle-vscode` on `main`,
use Kaggle Secrets, and skip network/service work in batch saves. The personal
notebook retains its accelerator/data-source metadata, with the old image pin
removed. Outputs and execution counts are cleared before publishing.

Run `python update_notebooks.py` to regenerate both notebooks from the shared
cells when changing their instructions or workflow.

## Validation

Local regression tests require only Python's standard library:

```bash
python -m unittest discover -s tests -v
bash -n install_ssh_server.sh add_ngrok_token.sh run_ssh_server.sh tests/integration_ssh.sh
```

The GitHub Actions workflow additionally runs ShellCheck and disposable Linux
container tests on Ubuntu 22.04, Ubuntu 24.04, and a Python 3.13 Debian image. The
integration test removes host keys after installing OpenSSH to reproduce the
reported failure, then checks real password login, wrong-password rejection,
SFTP, transferred environment paths, repeated setup, and stable host identity.
It validates ngrok configuration with a dummy token and does not open a public
tunnel. An actual Kaggle GPU session and a valid ngrok account are still needed
for the full VS Code/GPU connection.
