"""Regression checks for environment transfer, notebooks and tunnel lifecycle."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ssh_environment
import ssh_tunnel


class EnvironmentTests(unittest.TestCase):
    def test_notebook_paths_preserved_and_secrets_excluded(self):
        env = ssh_environment.collect_environment({
            "PATH": "/opt/runtime/bin:/usr/bin:/opt/runtime/bin",
            "LD_LIBRARY_PATH": "/mounted/gpu/lib64",
            "CUDA_VISIBLE_DEVICES": "0,1",
            "SSH_PASSWORD": "test-password",
            "NGROK_AUTHTOKEN": "test-token",
            "KAGGLE_USER_SECRETS_TOKEN": "test-kaggle-token",
        }, "/opt/runtime/bin/python3.13")
        self.assertEqual(env["PATH"].split(":").count("/opt/runtime/bin"), 1)
        self.assertEqual(env["PATH"].split(":")[0], "/opt/runtime/bin")
        self.assertIn("/mounted/gpu/lib64", env["LD_LIBRARY_PATH"].split(":"))
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "0,1")
        self.assertFalse(any("TOKEN" in name or "PASSWORD" in name for name in env))

    def test_config_injection_rejected(self):
        with self.assertRaises(ValueError):
            ssh_environment.collect_environment({"PYTHONPATH": "/tmp\nPermitRootLogin no"})

    def test_repeated_setup_preserves_custom_profile_and_excludes_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "root").mkdir()
            bashrc = root / "root/.bashrc"
            bashrc.write_text("# custom user configuration\n", encoding="utf-8")
            with patch.dict(os.environ, {"SSH_PASSWORD": "do-not-write-this", "NGROK_AUTHTOKEN": "nor-this"}):
                with redirect_stdout(io.StringIO()):
                    ssh_environment.write_configuration(root)
                    first = (root / "etc/ssh/sshd_config_kaggle").read_text(encoding="utf-8")
                    ssh_environment.write_configuration(root)
            self.assertEqual(first, (root / "etc/ssh/sshd_config_kaggle").read_text(encoding="utf-8"))
            self.assertEqual(sum(line.startswith("SetEnv ") for line in first.splitlines()), 1)
            self.assertIn("# custom user configuration", bashrc.read_text(encoding="utf-8"))
            self.assertEqual(bashrc.read_text(encoding="utf-8").count(ssh_environment.PROFILE_SOURCE), 1)
            for path in root.rglob("*"):
                if path.is_file():
                    contents = path.read_text(encoding="utf-8")
                    self.assertNotIn("do-not-write-this", contents)
                    self.assertNotIn("nor-this", contents)


class TunnelTests(unittest.TestCase):
    def test_json_log_endpoint_and_partial_line(self):
        log = ('not json\n{"msg":"session established"}\n'
               '{"msg":"started tunnel","url":"tcp://1.tcp.ngrok.io:12345"}\n'
               '{"msg":"partial')
        endpoint = ssh_tunnel.endpoint_from_log(log)
        self.assertEqual(endpoint, "tcp://1.tcp.ngrok.io:12345")
        self.assertIn("HostName 1.tcp.ngrok.io\n    Port 12345", ssh_tunnel.connection_config(endpoint))
        self.assertIsNone(ssh_tunnel.endpoint_from_log('{"url":"https://example.ngrok.app"}'))

    def test_non_tcp_endpoint_rejected(self):
        for endpoint in ("https://example.ngrok.app", "tcp://example.ngrok.io", "tcp://example.ngrok.io:bad"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                ssh_tunnel.connection_config(endpoint)

    def test_startup_timeout_terminates_owned_process(self):
        process = MagicMock()
        process.poll.return_value = None
        with patch("ssh_tunnel.socket.create_connection") as connect, \
             patch("ssh_tunnel.shutil.which", return_value="ngrok"), \
             patch("ssh_tunnel.subprocess.Popen", return_value=process), \
             redirect_stdout(io.StringIO()):
            connect.return_value.__enter__.return_value.recv.return_value = b"SSH-2.0-OpenSSH_9.6\r\n"
            with self.assertRaises(TimeoutError):
                ssh_tunnel.run_tunnel(startup_timeout=0)
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=5)

    def test_interruption_cleans_up_tunnel(self):
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [KeyboardInterrupt(), 0]
        with patch("ssh_tunnel.socket.create_connection") as connect, \
             patch("ssh_tunnel.shutil.which", return_value="ngrok"), \
             patch("ssh_tunnel.subprocess.Popen", return_value=process), \
             patch("ssh_tunnel.endpoint_from_log", return_value="tcp://1.tcp.ngrok.io:12345"), \
             redirect_stdout(io.StringIO()) as output:
            connect.return_value.__enter__.return_value.recv.return_value = b"SSH-2.0-OpenSSH_9.6\r\n"
            ssh_tunnel.run_tunnel()
        self.assertIn("Host Kaggle", output.getvalue())
        self.assertIn("Stopping the ngrok tunnel", output.getvalue())
        process.terminate.assert_called_once()

    def test_ngrok_failure_is_reported_without_secret(self):
        process = MagicMock()
        process.poll.return_value = 1
        process.returncode = 1
        def spawn(*args, **kwargs):
            kwargs["stdout"].write("ERR_NGROK test-private-token\n")
            return process
        with patch("ssh_tunnel.socket.create_connection") as connect, \
             patch("ssh_tunnel.shutil.which", return_value="ngrok"), \
             patch("ssh_tunnel.subprocess.Popen", side_effect=spawn), \
             patch.dict(os.environ, {"NGROK_AUTHTOKEN": "test-private-token"}), \
             redirect_stdout(io.StringIO()) as output:
            connect.return_value.__enter__.return_value.recv.return_value = b"SSH-2.0-OpenSSH_9.6\r\n"
            with self.assertRaises(RuntimeError):
                ssh_tunnel.run_tunnel()
        self.assertIn("ERR_NGROK", output.getvalue())
        self.assertNotIn("test-private-token", output.getvalue())


class NotebookTests(unittest.TestCase):
    def test_notebooks_are_clean_and_runnable(self):
        root = Path(__file__).resolve().parents[1]
        for path in root.glob("*.ipynb"):
            with self.subTest(notebook=path.name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotIn("dockerImageVersionId", notebook["metadata"].get("kaggle", {}))
                code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
                for cell in code_cells:
                    source = "".join(cell["source"])
                    compile(source, f"{path.name}:{cell['id']}", "exec")
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])
                    self.assertNotIn("hoang-quoc-trung", source)
                    self.assertNotIn("hoangtrung020541", source)

    def test_interactive_and_batch_start_ssh_and_wait_for_tunnel(self):
        root = Path(__file__).resolve().parents[1]
        for path in root.glob("*.ipynb"):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            for mode in ("Interactive", "Batch"):
                with self.subTest(notebook=path.name, mode=mode):
                    env = {"KAGGLE_KERNEL_RUN_TYPE": mode, "SSH_PASSWORD": "test-only-password",
                           "NGROK_AUTHTOKEN": "test-only-token"}
                    with patch.dict(os.environ, env), patch("pathlib.Path.exists", return_value=False), \
                         patch("subprocess.run") as run, patch("subprocess.Popen") as popen, \
                         redirect_stdout(io.StringIO()):
                        popen.return_value.wait.return_value = 0
                        namespace = {}
                        for cell in notebook["cells"]:
                            if cell["cell_type"] == "code":
                                exec("".join(cell["source"]), namespace)
                    commands = [call.args[0] for call in run.call_args_list]
                    self.assertEqual(commands[0][:2], ["git", "clone"])
                    self.assertIn(["bash", "install_ssh_server.sh"], commands)
                    self.assertIn(["bash", "add_ngrok_token.sh"], commands)
                    popen.assert_called_once()
                    self.assertEqual(popen.call_args.args[0], ["bash", "run_ssh_server.sh"])
                    # No timeout: the notebook stays executing as long as the
                    # tunnel process is alive, including in Save & Run All.
                    popen.return_value.wait.assert_called_once_with()

    def test_batch_tunnel_failure_is_not_reported_as_success(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root / "notebook_example.ipynb").read_text(encoding="utf-8"))
        tunnel_cell = next(cell for cell in notebook["cells"] if cell["id"] == "tunnel")
        namespace = {"os": os, "sys": sys, "subprocess": __import__("subprocess"), "REPO_DIR": root}
        with patch.dict(os.environ, {"KAGGLE_KERNEL_RUN_TYPE": "Batch"}), \
             patch("subprocess.Popen") as popen:
            popen.return_value.wait.return_value = 1
            with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                exec("".join(tunnel_cell["source"]), namespace)

    def test_batch_tunnel_interruption_stops_its_process_group(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root / "notebook_example.ipynb").read_text(encoding="utf-8"))
        tunnel_cell = next(cell for cell in notebook["cells"] if cell["id"] == "tunnel")
        namespace = {"os": os, "sys": sys, "subprocess": __import__("subprocess"), "REPO_DIR": root}
        with patch.dict(os.environ, {"KAGGLE_KERNEL_RUN_TYPE": "Batch"}), \
             patch("subprocess.Popen") as popen, patch("os.killpg", create=True) as killpg, \
             redirect_stdout(io.StringIO()):
            popen.return_value.pid = 12345
            popen.return_value.poll.return_value = None
            popen.return_value.wait.side_effect = [KeyboardInterrupt(), 0]
            exec("".join(tunnel_cell["source"]), namespace)
        killpg.assert_called_once_with(12345, signal.SIGINT)


if __name__ == "__main__":
    unittest.main()
