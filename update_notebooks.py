"""Regenerate clean Kaggle notebooks; preserve each notebook's Kaggle settings."""

import json
from pathlib import Path
import textwrap


def cell(kind, source, cell_id):
    result = {"cell_type": kind, "id": cell_id, "metadata": {},
              "source": textwrap.dedent(source).strip().splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


CELLS = [
    cell("markdown", """
        # Kaggle Remote-SSH for VS Code

        Source: https://github.com/NguyenQuocDat06-AI/remote-ssh-kaggle-vscode

        1. Enable **Internet** in Notebook settings. Select a GPU if you need one.
        2. In **Add-ons > Secrets**, add and enable `SSH_PASSWORD` and `NGROK_AUTHTOKEN`.
           Get your ngrok token at https://dashboard.ngrok.com/get-started/your-authtoken.
        3. Run the following cells in the interactive editor, in order. No restart is required.
        4. Keep the last cell running during your VS Code session.

        Use **Quick Save** to save this notebook. **Save & Run All** starts a separate
        batch session; this notebook skips SSH setup there so saving can finish.
        After **Stop Session**, rerun all cells and update the generated hostname/port.
        Files in `/kaggle/working` can persist; installed services and host keys do not.
    """, "instructions"),
    cell("code", """
        import os
        from pathlib import Path
        import subprocess
        import sys

        INTERACTIVE = os.environ.get("KAGGLE_KERNEL_RUN_TYPE", "Interactive").lower() == "interactive"
        REPO_URL = "https://github.com/NguyenQuocDat06-AI/remote-ssh-kaggle-vscode.git"
        REPO_DIR = Path("/kaggle/working/remote-ssh-kaggle-vscode")

        if INTERACTIVE:
            if not REPO_DIR.exists():
                subprocess.run(["git", "clone", "--branch", "main", "--depth", "1",
                                REPO_URL, str(REPO_DIR)], check=True)
            else:
                if not (REPO_DIR / ".git").exists():
                    raise RuntimeError(f"{REPO_DIR} exists but is not a Git repository.")
                changes = subprocess.check_output(
                    ["git", "-C", str(REPO_DIR), "status", "--porcelain", "--untracked-files=no"], text=True
                ).strip()
                if changes:
                    raise RuntimeError("Save or stash your changes in the repository before updating it.")
                subprocess.run(["git", "-C", str(REPO_DIR), "remote", "set-url", "origin", REPO_URL], check=True)
                subprocess.run(["git", "-C", str(REPO_DIR), "checkout", "main"], check=True)
                subprocess.run(["git", "-C", str(REPO_DIR), "pull", "--ff-only", "origin", "main"], check=True)
            print("Notebook Python:", sys.executable, sys.version.split()[0])
        else:
            print("Batch save: SSH setup is skipped. Run cells in the interactive editor to connect.")
    """, "get-source"),
    cell("markdown", """
        ## Install and configure SSH + ngrok

        This creates missing SSH host keys, validates the server, and captures the
        notebook's Python/CUDA paths for SSH terminals. Secrets are read at runtime.
        Setup stops immediately if a command fails.
    """, "setup-instructions"),
    cell("code", """
        def read_secret(name):
            value = os.environ.get(name)
            if not value:
                try:
                    from kaggle_secrets import UserSecretsClient
                    value = UserSecretsClient().get_secret(name)
                except Exception:
                    raise RuntimeError(
                        f"Add and enable {name} in Add-ons > Secrets for this notebook."
                    ) from None
            if not value or "\\n" in value or "\\r" in value:
                raise ValueError(f"{name} must be nonempty and contain only one line.")
            return value

        if INTERACTIVE:
            setup_env = os.environ.copy()
            setup_env["KAGGLE_PYTHON"] = sys.executable
            try:
                setup_env["SSH_PASSWORD"] = read_secret("SSH_PASSWORD")
                setup_env["NGROK_AUTHTOKEN"] = read_secret("NGROK_AUTHTOKEN")
                subprocess.run(["bash", "install_ssh_server.sh"], cwd=REPO_DIR, env=setup_env, check=True)
                setup_env.pop("SSH_PASSWORD", None)
                subprocess.run(["bash", "add_ngrok_token.sh"], cwd=REPO_DIR, env=setup_env, check=True)
            finally:
                setup_env.pop("SSH_PASSWORD", None)
                setup_env.pop("NGROK_AUTHTOKEN", None)
            print("Setup complete. Run the next cell to get your SSH configuration.")
    """, "setup"),
    cell("markdown", """
        ## Connect from VS Code

        Run the cell below and copy its `Host Kaggle` block into your local
        `~/.ssh/config`. Install **Remote - SSH** in VS Code, choose **Connect to Host > Kaggle**,
        select **Linux**, and enter your `SSH_PASSWORD`. Open `/kaggle/working`.

        The cell remains running until you interrupt it. Stopping it closes the tunnel.
        ngrok TCP access requires an account eligible for TCP endpoints; a free account
        currently needs a valid payment method. If ngrok refuses the tunnel, its error
        appears in this cell.

        To check Python/GPU in an SSH terminal:
        ```bash
        python -c "import sys; print(sys.executable)"
        nvidia-smi
        python -c "import torch; print(torch.cuda.is_available())"
        ```
        A CPU session has no GPU. The scripts use existing image libraries and do not
        install or replace NVIDIA drivers.
    """, "connect-instructions"),
    cell("code", """
        if INTERACTIVE:
            import signal

            tunnel_env = os.environ.copy()
            tunnel_env["KAGGLE_PYTHON"] = sys.executable
            tunnel_process = subprocess.Popen(
                ["bash", "run_ssh_server.sh"], cwd=REPO_DIR, env=tunnel_env, start_new_session=True
            )
            try:
                returncode = tunnel_process.wait()
                if returncode:
                    raise RuntimeError(f"Tunnel stopped with exit code {returncode}. Check the error above.")
            except KeyboardInterrupt:
                if tunnel_process.poll() is None:
                    os.killpg(tunnel_process.pid, signal.SIGINT)
                    try:
                        tunnel_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(tunnel_process.pid, signal.SIGKILL)
                        tunnel_process.wait()
                print("Tunnel stopped. Rerun this cell to reconnect.")
    """, "tunnel"),
]


def main():
    for filename in ("notebook_example.ipynb", "fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb"):
        path = Path(__file__).parent / filename
        notebook = json.loads(path.read_text(encoding="utf-8"))
        notebook["cells"] = CELLS
        notebook["nbformat"] = 4
        notebook["nbformat_minor"] = 5
        notebook["metadata"]["language_info"] = {"name": "python", "file_extension": ".py",
                                                 "mimetype": "text/x-python"}
        # Use Kaggle's current image rather than pinning the old exported image.
        kaggle = notebook["metadata"].get("kaggle")
        if kaggle is not None:
            kaggle.pop("dockerImageVersionId", None)
            kaggle["isInternetEnabled"] = True
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Updated {filename} (no credentials or outputs).")


if __name__ == "__main__":
    main()
