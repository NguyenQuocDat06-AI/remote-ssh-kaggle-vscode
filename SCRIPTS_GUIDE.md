# Guide

Notebook duoc tao boi `update_notebooks.py` dung **Kaggle Jupyter Server**. No khong cai
dat OpenSSH, ngrok, Cloudflare hay VS Code/Dev Tunnel CLI trong Kaggle.

## Ket noi VS Code

1. Khoi dong phien tuong tac trong notebook Kaggle.
2. Chon **Run > Kaggle Jupyter Server**.
3. Sao chep **VS Code Compatible URL** trong muc **Manually Connect**.
4. Trong VS Code co extension Jupyter, mo `.ipynb`, chon Kernel Picker > **Existing
   Jupyter Server** > **Enter the URL of the running Jupyter server**, roi dan URL.

URL chua token truy cap session. Khong ghi no vao source, Secret, output hay commit Git.
Session ket thuc thi URL cung het hieu luc; lay URL moi khi bat session moi.

Luon dung luong nay de chay notebook Kaggle trong VS Code. Cac file SSH/ngrok cu trong
repository chi la tai lieu lich su va khong duoc ho tro cho Kaggle.

## Notebook maintenance

Chay lenh sau sau khi sua `update_notebooks.py`:

```powershell
python update_notebooks.py
python -m unittest discover -s tests -v
```

Kiem tra xac nhan ca hai notebook co cung huong dan, code cell hop le, khong co Secret/tunnel
command va khong co output da luu.
