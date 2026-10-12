"""Compatibility checks for the supported Kaggle notebook workflow."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NotebookMetadataTests(unittest.TestCase):
    def test_notebooks_are_clean_and_runnable(self):
        for path in ROOT.glob("*.ipynb"):
            with self.subTest(notebook=path.name):
                notebook = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotIn("dockerImageVersionId", notebook["metadata"].get("kaggle", {}))
                code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
                self.assertEqual([cell["id"] for cell in code_cells], ["verify-kaggle-kernel"])
                for cell in code_cells:
                    source = "".join(cell["source"])
                    compile(source, f"{path.name}:{cell['id']}", "exec")
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])

    def test_notebooks_are_not_configured_for_network_access(self):
        path = ROOT / "fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb"
        metadata = json.loads(path.read_text(encoding="utf-8"))["metadata"]["kaggle"]
        self.assertEqual(metadata["accelerator"], "none")
        self.assertFalse(metadata["isInternetEnabled"])
        self.assertFalse(metadata["isGpuEnabled"])


if __name__ == "__main__":
    unittest.main()
