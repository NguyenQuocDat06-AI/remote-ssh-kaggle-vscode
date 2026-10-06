<div align="center">

# Remote-SSH Kaggle using Visual Studio Code

**Connect VS Code to a Kaggle notebook with password authentication.**

<img src="imgs/architecture_ssh.png" alt="SSH architecture">
<img src="imgs/vscode_ssh_screen.png" alt="VS Code connected to Kaggle over SSH">

</div>

## Set up the notebook

1. Upload [notebook_example.ipynb](notebook_example.ipynb) or the updated
   [personal notebook](fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb) to Kaggle.
   Both use this repository:
   `https://github.com/NguyenQuocDat06-AI/remote-ssh-kaggle-vscode.git`.
2. Enable **Internet** in Notebook settings. Select a GPU if needed; CPU sessions
   also support SSH. Choose **Files only** persistence if you want your working
   files to survive between interactive sessions.
3. Open **Add-ons > Secrets**, add these secrets, and enable each for the notebook:

   | Secret name | Value |
   |---|---|
   | `SSH_PASSWORD` | Your SSH login password |
   | `NGROK_AUTHTOKEN` | Your [ngrok authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) |

4. Run the three code cells in order, or choose **Save & Run All**: update the source,
   set up SSH/ngrok, then start the tunnel. Setup supports passwords with spaces
   and shell characters and stops if a command fails. No session restart is needed.
5. Leave the tunnel cell running. It prints a complete SSH configuration like:

   ```ssh-config
   Host Kaggle
       HostName 1.tcp.ngrok.io
       Port 12345
       User root
       ServerAliveInterval 60
       ServerAliveCountMax 3
   ```

   Copy the actual hostname and port printed by your session.

**Save & Run All** executes in a separate batch session and starts SSH there too.
Open the running version's live logs and copy the SSH configuration printed by
that session. Its status stays **Running** while the tunnel is active; stop the
run when you finish. **Quick Save** saves edits without starting another session.

[ngrok TCP endpoints](https://ngrok.com/docs/gateway/agent/cli#ngrok-tcp) require an
account eligible for TCP access. Free accounts currently need a valid payment
method. ngrok account/authentication errors appear in the tunnel cell.

## Connect from VS Code

1. Install [Visual Studio Code](https://code.visualstudio.com/) and the
   **Remote - SSH** extension.
2. Open **Remote-SSH: Open SSH Configuration File** from the command palette.
   On Windows, this is normally `%USERPROFILE%\.ssh\config`.
3. Paste the generated `Host Kaggle` block into the file and save it.
4. Select **Remote-SSH: Connect to Host > Kaggle**, select **Linux** if prompted,
   and enter the password from your `SSH_PASSWORD` secret.
5. Open `/kaggle/working` and use VS Code's terminal, debugger, and file editor.

See the [VS Code Remote-SSH documentation](https://code.visualstudio.com/docs/remote/ssh)
for extension setup.

## Python and GPU environment

Setup captures the current notebook interpreter and Python/CUDA paths. Both
remote commands and terminal shells receive the environment. Existing NVIDIA
libraries are used; the scripts do not install or replace GPU drivers.

Check from the SSH terminal:

```bash
python -c "import sys; print(sys.executable)"
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

Choose the printed Python interpreter in VS Code's **Python: Select Interpreter**.
If your interpreter is named `python3` instead of `python`, use `python3` or the
printed absolute path.

Install extra packages into the notebook interpreter:

```bash
uv pip install --system --python "$KAGGLE_PYTHON" <package>
```

Or create an isolated environment that can use Kaggle's preinstalled packages:

```bash
uv venv --python "$KAGGLE_PYTHON" --system-site-packages .venv
source .venv/bin/activate
uv pip install <package>
```

A CPU session has no GPU. If the GPU checks fail, first check the notebook's
Accelerator setting and compare the same checks in the notebook.

## Start a new session

After **Stop Session**, rerun all three code cells. `/kaggle/working` may persist,
but system packages, SSH host keys, daemon processes, and the ngrok token config
must be recreated. The clone cell updates an existing repository without creating
a nested clone and stops if tracked local edits would be affected.

Update the hostname and port in your local SSH configuration before reconnecting.
If SSH reports a changed host key, verify you are connecting to your new notebook
session, then remove the old entry using the exact hostname and port:

```bash
ssh-keygen -R "[HOSTNAME]:PORT"
```

SSH does not extend Kaggle's session duration or GPU quota. Check the limits
shown in your Kaggle account.

## Troubleshooting

| Message | What to do |
|---|---|
| `sshd: no hostkeys available -- exiting` | Update this repository and rerun setup. It runs `ssh-keygen -A` even when OpenSSH is already installed. |
| `Add and enable SSH_PASSWORD/NGROK_AUTHTOKEN` | Add both secrets and enable them for this notebook. |
| `ngrok exited` or `ERR_NGROK_*` | Read the agent error in the cell; check token, account TCP access, Internet, and other running agents. |
| `Connection refused` before tunneling | Rerun setup in the current session. Check `/var/log/kaggle-sshd.log`. |
| `Batch save: SSH setup is skipped` | Import the updated notebook; earlier notebook versions disabled SSH during Save & Run All. Pulling source alone does not replace the notebook's cells. |
| `Permission denied` | Use `User root` and the password from the current secret; update both the source and notebook. |
| Debugger warning about frozen modules or `SyntaxWarning` in nbconvert | These warnings do not prevent SSH from starting; inspect the later SSH/ngrok error. |

[Kaggle's current image source](https://github.com/Kaggle/docker-python/blob/main/Dockerfile.tmpl)
uses a Colab runtime and Python 3.13. The scripts discover paths at runtime rather
than pinning Python or NVIDIA utility versions. See [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md)
for implementation and validation details.
