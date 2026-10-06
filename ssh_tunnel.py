"""Run ngrok in a notebook and print a usable VS Code SSH configuration."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit


def connection_config(public_url):
    url = urlsplit(public_url)
    if url.scheme != "tcp" or not url.hostname or not url.port:
        raise ValueError(f"Expected an ngrok TCP endpoint, got {public_url!r}.")
    return (f"Host Kaggle\n    HostName {url.hostname}\n    Port {url.port}\n"
            "    User root\n    ServerAliveInterval 60\n    ServerAliveCountMax 3\n")


def endpoint_from_log(log_text):
    for line in log_text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        endpoint = event.get("url", "")
        if isinstance(endpoint, str) and endpoint.startswith("tcp://"):
            connection_config(endpoint)
            return endpoint
    return None


def run_tunnel(startup_timeout=60):
    port = int(os.environ.get("SSH_PORT", "22"))
    with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:
        if not sock.recv(256).startswith(b"SSH-2.0-"):
            raise RuntimeError("No SSH server is listening. Run the setup cell again.")
    ngrok = shutil.which("ngrok")
    if not ngrok:
        raise RuntimeError("ngrok is missing. Run the setup cell again.")
    # Read this process's JSON log so another agent's inspector cannot supply
    # a stale endpoint. This also works with notebook HTTP proxy environments.
    with tempfile.TemporaryDirectory(prefix="kaggle-ngrok-") as directory:
        log_path = Path(directory) / "agent.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [ngrok, "tcp", f"127.0.0.1:{port}", "--log=stdout", "--log-format=json"],
                stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + startup_timeout
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"ngrok exited with status {process.returncode}.")
                    endpoint = endpoint_from_log(log_path.read_text(encoding="utf-8"))
                    if endpoint:
                        print("Paste this into your local ~/.ssh/config:\n", flush=True)
                        print(connection_config(endpoint), flush=True)
                        print("Keep this cell running while using VS Code. Interrupt it to stop the tunnel.", flush=True)
                        result = process.wait()
                        if result:
                            raise RuntimeError(f"ngrok exited with status {result}.")
                        return
                    time.sleep(0.5)
                raise TimeoutError(f"ngrok did not create a TCP endpoint within {startup_timeout} seconds.")
            except KeyboardInterrupt:
                print("Stopping the ngrok tunnel...", flush=True)
            except Exception:
                log.flush()
                error_log = log_path.read_text(encoding="utf-8")[-12000:]
                token = os.environ.get("NGROK_AUTHTOKEN")
                if token:
                    error_log = error_log.replace(token, "[redacted]")
                print(error_log, flush=True)
                print("Check Kaggle Internet, your ngrok token and TCP access for your account.", flush=True)
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    run_tunnel()
