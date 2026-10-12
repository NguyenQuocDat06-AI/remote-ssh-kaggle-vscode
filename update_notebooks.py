"""Build Kaggle notebooks that use Kaggle's supported Jupyter Server connection."""

import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent


def cell(kind, source, cell_id):
    result = {
        "cell_type": kind,
        "id": cell_id,
        "metadata": {},
        "source": textwrap.dedent(source).strip().splitlines(keepends=True),
    }
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def notebook_cells():
    return [
        cell("markdown", """
            # Ket noi Kaggle voi VS Code bang Kaggle Jupyter Server

            Notebook nay khong khoi tao SSH, ngrok, Cloudflare, Dev Tunnel hoac bat ky
            remote tunnel nao. Kaggle cung cap **Kaggle Jupyter Server** de ket noi mot
            notebook tu VS Code theo cach chinh thuc.

            ## Ket noi tu VS Code

            1. Mo notebook trong Kaggle va bat mot phien tuong tac binh thuong. Chon CPU/GPU
               trong Settings theo nhu cau cua notebook.
            2. Trong thanh menu cua Kaggle, chon **Run > Kaggle Jupyter Server**.
            3. O **Manually Connect**, sao chep **VS Code Compatible URL**. URL nay co token;
               khong dua no vao Secrets, source code, GitHub hay chia se voi nguoi khac.
            4. Trong VS Code tren Windows, cai extension **Jupyter** va mo file `.ipynb` muon
               lam viec. Bam Kernel Picker o goc tren ben phai > **Existing Jupyter Server** >
               **Enter the URL of the running Jupyter server**, roi dan URL vua sao chep.
            5. Chon kernel Kaggle trong Kernel Picker va chay cell. Code se chay tren may Kaggle.

            Ket noi chi ton tai khi phien Kaggle dang hoat dong. Khi phien ket thuc, quay lai
            buoc 2 de lay URL moi. Che do nay cho phep sua va chay `.ipynb` tu VS Code; neu can
            mot may chu co terminal/SSH day du, hay dung VPS cua ban thay vi Kaggle.

            Tai lieu Kaggle: https://www.kaggle.com/docs/notebooks
        """, "instructions"),
        cell("code", """
            # Kiem tra nhanh: cell nay chay tren kernel Kaggle sau khi VS Code da ket noi.
            import platform
            import sys

            print("Python:", sys.executable)
            print("Platform:", platform.platform())
            try:
                import torch
                print("CUDA available:", torch.cuda.is_available())
            except ImportError:
                print("PyTorch is not installed in this image.")
        """, "verify-kaggle-kernel"),
    ]


def main():
    cells = notebook_cells()
    for filename in ("notebook_example.ipynb", "fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb"):
        path = ROOT / filename
        notebook = json.loads(path.read_text(encoding="utf-8"))
        notebook["cells"] = cells
        notebook["nbformat"] = 4
        notebook["nbformat_minor"] = 5
        notebook["metadata"]["language_info"] = {
            "name": "python",
            "file_extension": ".py",
            "mimetype": "text/x-python",
        }
        kaggle = notebook["metadata"].get("kaggle")
        if kaggle is not None:
            kaggle.pop("dockerImageVersionId", None)
            kaggle["isInternetEnabled"] = False
            kaggle["accelerator"] = "none"
            kaggle["isGpuEnabled"] = False
        path.write_text(
            json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Updated {filename}: use Kaggle Jupyter Server, no external tunnel.")


if __name__ == "__main__":
    main()
