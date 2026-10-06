"""Carry the notebook's Python/CUDA environment into SSH sessions (stdlib only)."""

import os
from pathlib import Path
import shlex
import site
import sys


# Deliberately exclude passwords, tokens, and unrelated notebook credentials.
ENV_NAMES = (
    "PATH", "LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONUSERBASE",
    "CUDA_HOME", "CUDA_PATH", "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES",
    "NVIDIA_DRIVER_CAPABILITIES", "CONDA_PREFIX", "VIRTUAL_ENV", "LANG", "LC_ALL",
)
PROFILE_SOURCE = '[ -r /etc/profile.d/kaggle-ssh.sh ] && . /etc/profile.d/kaggle-ssh.sh'


def merge_paths(*values):
    """Keep path order, remove duplicates and empty (current-directory) entries."""
    return ":".join(dict.fromkeys(part for value in values for part in value.split(":") if part))


def collect_environment(environ=None, executable=None):
    environ = os.environ if environ is None else environ
    executable = sys.executable if executable is None else executable
    env = {name: environ[name] for name in ENV_NAMES if name in environ}
    env["KAGGLE_PYTHON"] = executable
    gpu_bins = [path for path in ("/opt/bin", "/usr/local/cuda/bin", "/usr/local/nvidia/bin")
                if Path(path).is_dir()]
    env["PATH"] = merge_paths(Path(executable).parent.as_posix(), env.get("PATH", ""),
                              ":".join(gpu_bins), "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    gpu_libs = [path for path in ("/usr/local/nvidia/lib64", "/usr/local/nvidia/lib",
                                 "/usr/local/cuda/lib64") if Path(path).is_dir()]
    env["LD_LIBRARY_PATH"] = merge_paths(env.get("LD_LIBRARY_PATH", ""), ":".join(gpu_libs))
    package_dirs = [path for path in (*site.getsitepackages(), site.getusersitepackages())
                    if Path(path).is_dir()]
    env["PYTHONPATH"] = merge_paths(env.get("PYTHONPATH", ""), ":".join(package_dirs))
    if "CUDA_HOME" not in env and Path("/usr/local/cuda").is_dir():
        env["CUDA_HOME"] = "/usr/local/cuda"
    for name, value in env.items():
        if any(char in value for char in ("\n", "\r", "\0")):
            raise ValueError(f"{name} must not contain line breaks or NUL characters.")
    return env


def sshd_quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_configuration(root=Path("/")):
    env = collect_environment()
    port = int(os.environ.get("SSH_PORT", "22"))
    if not 1 <= port <= 65535:
        raise ValueError("SSH_PORT must be between 1 and 65535.")
    config = f"""# Managed by remote-ssh-kaggle-vscode; independent of image defaults.
Port {port}
ListenAddress 127.0.0.1
PidFile /run/kaggle-sshd.pid
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes
PermitEmptyPasswords no
UsePAM no
AllowUsers root
AllowTcpForwarding yes
ClientAliveInterval 60
ClientAliveCountMax 3
Subsystem sftp internal-sftp
"""
    config += "".join(f"SetEnv {sshd_quote(name + '=' + value)}\n" for name, value in env.items())
    config_path = root / "etc/ssh/sshd_config_kaggle"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config, encoding="utf-8")
    config_path.chmod(0o600)

    profile = root / "etc/profile.d/kaggle-ssh.sh"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("# Managed notebook environment; no credentials.\n" + "".join(
        f"export {name}={shlex.quote(value)}\n" for name, value in env.items()
    ), encoding="utf-8")
    profile.chmod(0o644)
    # Login shells may reset PATH after /etc/profile.d; bash's remote-command
    # startup also reads .bashrc. Restore the notebook paths at the end of both.
    startup_files = [".bashrc", ".profile"]
    startup_files += [name for name in (".bash_profile", ".bash_login")
                     if (root / "root" / name).exists()]
    for filename in startup_files:
        path = root / "root" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        previous = path.read_text(encoding="utf-8") if path.exists() else ""
        if PROFILE_SOURCE not in previous.splitlines():
            path.write_text(previous + "\n" + PROFILE_SOURCE + "\n", encoding="utf-8")
    print(f"SSH environment uses Python: {sys.executable}")


if __name__ == "__main__":
    write_configuration()
