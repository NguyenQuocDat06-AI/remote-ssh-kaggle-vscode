"""Standalone Kaggle launcher, embedded in both notebooks by update_notebooks.py."""

import base64
import binascii
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen


def read_tunnel_secret(name):
    value = os.environ.get(name)
    if not value:
        try:
            from kaggle_secrets import UserSecretsClient
            value = UserSecretsClient().get_secret(name)
        except Exception:
            raise RuntimeError(
                f"Thêm và bật Secret {name} trong Add-ons > Secrets của notebook."
            ) from None
    value = value.strip() if isinstance(value, str) else ""
    if not value or any(character.isspace() for character in value) or "\0" in value:
        raise ValueError(f"Secret {name} phải có giá trị và không chứa khoảng trắng.")
    return value


def parse_tunnel_id(tunnel_id):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-z0-9]+", tunnel_id):
        raise ValueError(
            "VSCODE_TUNNEL_ID phải là ID đầy đủ có vùng, ví dụ swift-field-gbd67x7.asse."
        )
    return tuple(tunnel_id.rsplit(".", 1))


def token_expiration(token):
    """Read expiry for diagnostics; authentication is performed by the service."""
    if token.startswith(("ghp_", "github_pat_", "gho_", "ghu_", "ghs_")):
        raise ValueError("VSCODE_TUNNEL_TOKEN cần token Dev Tunnel, không phải token GitHub.")
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        expiry = claims.get("exp") if isinstance(claims, dict) else None
    except (IndexError, ValueError, binascii.Error, UnicodeDecodeError):
        # Do not assume all future tunnel tokens use the current JWT format.
        return None
    if isinstance(expiry, (int, float)) and not isinstance(expiry, bool):
        if expiry <= time.time():
            raise ValueError("Token Dev Tunnel đã hết hạn. Cấp lại và cập nhật VSCODE_TUNNEL_TOKEN.")
        return expiry
    return None


def install_vscode_cli(directory):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("Chạy notebook này trên Kaggle Linux x86_64.")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cli = directory / "code"
    url = "https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64"
    print("Đang tải VS Code CLI bản stable...", flush=True)
    with tempfile.TemporaryDirectory(prefix="vscode-download-", dir=directory) as temporary:
        archive = Path(temporary) / "cli.tar.gz"
        for attempt in range(3):
            try:
                with urlopen(url, timeout=60) as response, archive.open("wb") as target:
                    shutil.copyfileobj(response, target)
                break
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise RuntimeError("Không tải được VS Code CLI. Kiểm tra Internet trên Kaggle.") from None
                time.sleep(2)
        # Copy only the CLI file; archive paths are never extracted to disk.
        with tarfile.open(archive, "r:gz") as package:
            member = next((item for item in package.getmembers()
                           if item.isfile() and Path(item.name).name == "code"), None)
            if member is None:
                raise RuntimeError("Gói tải về không chứa VS Code CLI.")
            executable = Path(temporary) / "code"
            with package.extractfile(member) as source, executable.open("wb") as target:
                shutil.copyfileobj(source, target)
            executable.chmod(0o755)
            executable.replace(cli)
    version = subprocess.run([str(cli), "--version"], capture_output=True, text=True, timeout=30)
    if version.returncode:
        raise RuntimeError("VS Code CLI không chạy được trên image hiện tại.")
    print(version.stdout.strip(), flush=True)
    return cli


def notebook_environment():
    env = os.environ.copy()
    env.pop("VSCODE_TUNNEL_TOKEN", None)
    env["KAGGLE_PYTHON"] = sys.executable
    bins = [Path(sys.executable).parent.as_posix(), env.get("PATH", "")]
    bins += [path for path in ("/opt/bin", "/usr/local/nvidia/bin", "/usr/local/cuda/bin")
             if Path(path).is_dir()]
    env["PATH"] = ":".join(dict.fromkeys(part for value in bins for part in value.split(":") if part))
    libs = [env.get("LD_LIBRARY_PATH", "")]
    libs += [path for path in ("/usr/local/nvidia/lib64", "/usr/local/nvidia/lib", "/usr/local/cuda/lib64")
             if Path(path).is_dir()]
    env["LD_LIBRARY_PATH"] = ":".join(dict.fromkeys(part for value in libs for part in value.split(":") if part))
    if "CUDA_HOME" not in env and Path("/usr/local/cuda").is_dir():
        env["CUDA_HOME"] = "/usr/local/cuda"
    return env


def stop_tunnel_process(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_vscode_tunnel(cli, name="kaggle"):
    if platform.system() != "Linux":
        raise RuntimeError("Chạy cell tunnel trên Kaggle Linux.")
    if not re.fullmatch(r"[a-zA-Z0-9-]{1,20}", name):
        raise ValueError("Tên tunnel cần 1-20 ký tự: chữ, số hoặc dấu '-'.")
    tunnel_id = read_tunnel_secret("VSCODE_TUNNEL_ID")
    identifier, cluster = parse_tunnel_id(tunnel_id)
    token = read_tunnel_secret("VSCODE_TUNNEL_TOKEN")
    expiry = token_expiration(token)
    print(f"Đang kết nối tunnel {tunnel_id}; tên máy: {name}.", flush=True)
    if expiry is not None:
        print(f"Token còn khoảng {(expiry - time.time()) / 3600:.1f} giờ.", flush=True)
    print("VS Code: Remote Tunnels: Connect to Tunnel > đăng nhập GitHub > chọn máy khi tunnel sẵn sàng.", flush=True)
    print(f"Python của notebook: {sys.executable}\nWorkspace: /kaggle/working", flush=True)
    print("Giữ cell này chạy trong lúc làm việc. Interrupt/Stop để đóng tunnel.", flush=True)
    # Session state stays outside notebook outputs and persisted workspace files.
    with tempfile.TemporaryDirectory(prefix="kaggle-vscode-session-") as session:
        command = [str(cli), "--cli-data-dir", session, "tunnel", "--name", name,
                   "--tunnel-id", identifier, "--cluster", cluster, "--host-token", token,
                   "--accept-server-license-terms"]
        try:
            process = subprocess.Popen(
                command, cwd="/kaggle/working", env=notebook_environment(), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", bufsize=1, start_new_session=True,
            )
        except OSError:
            raise RuntimeError("Không khởi động được VS Code CLI. Chạy lại cell cài đặt.") from None
        try:
            for line in process.stdout:
                print(line.replace(token, "[TOKEN ĐÃ ẨN]"), end="", flush=True)
            returncode = process.wait()
            if returncode:
                # Never use CalledProcessError here: it includes the secret argv.
                raise RuntimeError(
                    f"Tunnel dừng với mã {returncode}. Kiểm tra log, Internet, ID và token. "
                    f"Cấp token mới trên Windows: devtunnel token {tunnel_id} "
                    "--scopes host --scopes manage --scopes connect"
                )
            print("Tunnel đã đóng. Chạy lại cell này để kết nối lại.", flush=True)
        except KeyboardInterrupt:
            print("Đang đóng tunnel...", flush=True)
        finally:
            stop_tunnel_process(process)
            process.stdout.close()
