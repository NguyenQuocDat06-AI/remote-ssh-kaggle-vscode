"""Regression checks for the supported Kaggle Jupyter Server notebooks."""

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import update_notebooks


class NotebookTests(unittest.TestCase):
    def test_generated_notebooks_match_template(self):
        expected_cells = update_notebooks.notebook_cells()
        for path in ROOT.glob("*.ipynb"):
            with self.subTest(notebook=path.name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(notebook["cells"], expected_cells)
                self.assertEqual(notebook["metadata"]["language_info"]["name"], "python")
                for cell in notebook["cells"]:
                    if cell["cell_type"] == "code":
                        source = "".join(cell["source"])
                        compile(source, f"{path.name}:{cell['id']}", "exec")
                        self.assertEqual(cell["outputs"], [])
                        self.assertIsNone(cell["execution_count"])

    def test_notebooks_do_not_start_external_remote_access(self):
        forbidden = (
            "code tunnel",
            "devtunnel",
            "ngrok",
            "cloudflared",
            "ssh",
            "VSCODE_TUNNEL",
            "kaggle_secrets",
        )
        for path in ROOT.glob("*.ipynb"):
            with self.subTest(notebook=path.name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                text = "\n".join(
                    "".join(cell["source"])
                    for cell in notebook["cells"]
                    if cell["cell_type"] == "code"
                ).lower()
                for term in forbidden:
                    self.assertNotIn(term.lower(), text)

    def test_personal_notebook_defaults_to_cpu_and_offline(self):
        path = ROOT / "fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb"
        metadata = json.loads(path.read_text(encoding="utf-8"))["metadata"]["kaggle"]
        self.assertEqual(metadata["accelerator"], "none")
        self.assertFalse(metadata["isGpuEnabled"])
        self.assertFalse(metadata["isInternetEnabled"])


if __name__ == "__main__":
    unittest.main()
