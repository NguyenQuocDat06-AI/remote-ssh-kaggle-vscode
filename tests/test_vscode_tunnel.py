"""Checks for Dev Tunnel credentials, installation and notebook log handling."""

import base64
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vscode_tunnel
import update_notebooks


def test_token(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "e30." + payload + ".test-signature"


class CredentialTests(unittest.TestCase):
    def test_regional_id_split_and_missing_region_rejected(self):
        self.assertEqual(vscode_tunnel.parse_tunnel_id("swift-field-gbd67x7.asse"),
                         ("swift-field-gbd67x7", "asse"))
        for value in ("swift-field-gbd67x7", "x;echo token.asse", "x.asse.extra", "x.asse\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                vscode_tunnel.parse_tunnel_id(value)

    def test_expired_token_is_rejected_before_starting_cli(self):
        token = test_token({"exp": time.time() - 1})
        with patch.dict(os.environ, {"VSCODE_TUNNEL_ID": "test.asse", "VSCODE_TUNNEL_TOKEN": token}), \
             patch("platform.system", return_value="Linux"), patch("subprocess.Popen") as popen:
            with self.assertRaisesRegex(ValueError, "hết hạn"):
                vscode_tunnel.run_vscode_tunnel("code")
        popen.assert_not_called()

    def test_unexpired_and_future_token_formats(self):
        expiry = time.time() + 3600
        self.assertEqual(vscode_tunnel.token_expiration(test_token({"exp": expiry})), expiry)
        self.assertIsNone(vscode_tunnel.token_expiration("future-opaque-token"))
        self.assertIsNone(vscode_tunnel.token_expiration(test_token({})))

    def test_github_tokens_rejected(self):
        for prefix in ("ghp_", "github_pat_", "gho_"):
            with self.subTest(prefix=prefix), self.assertRaisesRegex(ValueError, "Dev Tunnel"):
                vscode_tunnel.token_expiration(prefix + "test")

    def test_missing_secret_and_secret_error_do_not_leak_backend_message(self):
        kaggle = MagicMock()
        kaggle.UserSecretsClient.return_value.get_secret.side_effect = RuntimeError("backend-private-token")
        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, {"kaggle_secrets": kaggle}):
            with self.assertRaises(RuntimeError) as caught:
                vscode_tunnel.read_tunnel_secret("VSCODE_TUNNEL_TOKEN")
        self.assertNotIn("backend-private-token", str(caught.exception))
        self.assertIn("Add-ons > Secrets", str(caught.exception))

    def test_notebook_environment_preserves_gpu_and_omits_tunnel_token(self):
        env = {"PATH": "/opt/runtime/bin:/usr/bin", "LD_LIBRARY_PATH": "/mounted/nvidia/lib64",
               "CUDA_VISIBLE_DEVICES": "0,1", "VSCODE_TUNNEL_TOKEN": "test-private-token"}
        with patch.dict(os.environ, env, clear=True), patch("sys.executable", "/opt/runtime/bin/python3.13"):
            result = vscode_tunnel.notebook_environment()
        self.assertEqual(result["PATH"].split(":")[0], "/opt/runtime/bin")
        self.assertTrue(result["LD_LIBRARY_PATH"].startswith("/mounted/nvidia/lib64"))
        self.assertEqual(result["CUDA_VISIBLE_DEVICES"], "0,1")
        self.assertNotIn("VSCODE_TUNNEL_TOKEN", result)


class InstallationTests(unittest.TestCase):
    def test_only_cli_is_copied_from_archive(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as package:
            for name, contents in (("./code", b"test cli"), ("../../outside.txt", b"should not be extracted")):
                member = tarfile.TarInfo(name)
                member.size = len(contents)
                package.addfile(member, io.BytesIO(contents))
        archive.seek(0)
        with tempfile.TemporaryDirectory() as directory, \
             patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"), \
             patch("vscode_tunnel.urlopen", return_value=archive), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "test version", "")), \
             redirect_stdout(io.StringIO()):
            cli = vscode_tunnel.install_vscode_cli(Path(directory) / "bin")
            self.assertEqual(cli.read_bytes(), b"test cli")
            self.assertEqual([path.name for path in Path(directory).rglob("*") if path.is_file()], ["code"])


class LauncherTests(unittest.TestCase):
    def test_actual_subprocess_logs_and_failure_hide_token(self):
        # Use a real child process to exercise streaming, EOF and return codes.
        original_popen = subprocess.Popen
        token = "test-private-token"
        captured_commands = []
        def spawn(command, **kwargs):
            captured_commands.append(command)
            kwargs["cwd"] = Path(__file__).resolve().parents[1]
            return original_popen([sys.executable, "-c",
                                  "import sys; print('error test-private-token', flush=True); sys.exit(3)"], **kwargs)
        with patch.dict(os.environ, {"VSCODE_TUNNEL_ID": "test.asse", "VSCODE_TUNNEL_TOKEN": token}), \
             patch("platform.system", return_value="Linux"), \
             patch("subprocess.Popen", side_effect=spawn), redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(RuntimeError, "mã 3") as caught:
                vscode_tunnel.run_vscode_tunnel("code")
        self.assertNotIn(token, output.getvalue())
        self.assertNotIn(token, str(caught.exception))
        self.assertIn("[TOKEN ĐÃ ẨN]", output.getvalue())
        command = captured_commands[0]
        self.assertEqual(command[command.index("--cluster") + 1], "asse")
        self.assertEqual(command[command.index("--tunnel-id") + 1], "test")

    def test_startup_error_never_displays_secret_argv(self):
        with patch.dict(os.environ, {"VSCODE_TUNNEL_ID": "test.asse", "VSCODE_TUNNEL_TOKEN": "test-token"}), \
             patch("platform.system", return_value="Linux"), \
             patch("subprocess.Popen", side_effect=OSError("private test-token")), \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError) as caught:
                vscode_tunnel.run_vscode_tunnel("code")
        self.assertNotIn("test-token", str(caught.exception))

    def test_generated_notebooks_match_launcher_and_preserve_outputs_policy(self):
        expected_cells = update_notebooks.notebook_cells()
        for path in update_notebooks.ROOT.glob("*.ipynb"):
            with self.subTest(notebook=path.name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(notebook["cells"], expected_cells)
                code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
                self.assertNotIn("git clone", code)
                self.assertNotIn("SSH_PASSWORD", code)
                self.assertNotIn("NGROK_AUTHTOKEN", code)


if __name__ == "__main__":
    unittest.main()
