# Kaggle + VS Code

Ket noi notebook Kaggle voi VS Code bang **Kaggle Jupyter Server**. Day la cach
Kaggle huong dan cho VS Code; repository khong con khoi tao SSH, ngrok,
Cloudflare hay VS Code/Dev Tunnels trong phien Kaggle.

## Su dung

1. Tai [notebook ca nhan](fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb) hoac
   [notebook mau](notebook_example.ipynb) len Kaggle.
2. Mo notebook trong Kaggle va khoi dong mot phien tuong tac. Chon CPU hoac GPU trong
   Settings theo cong viec cua ban.
3. Chon **Run > Kaggle Jupyter Server** trong menu Kaggle.
4. Trong muc **Manually Connect**, sao chep **VS Code Compatible URL**. URL chua token
   truy cap, vi vay khong luu no vao notebook, Kaggle Secrets, GitHub hay chia se voi
   nguoi khac.
5. Trong VS Code, cai extension **Jupyter**, mo file `.ipynb`, sau do bam Kernel Picker
   o goc tren ben phai > **Existing Jupyter Server** > **Enter the URL of the running
   Jupyter server**. Dan URL o buoc 4 va chon kernel Kaggle.

Cell kiem tra trong notebook se in Python runtime va trang thai CUDA. Cac cell chay tren
Kaggle, trong khi ban sua `.ipynb` bang VS Code tren Windows.

Ket noi het han khi phien Kaggle dung. Khoi dong lai phien va lay URL moi tu menu tren.
Kaggle gioi han thoi gian/quota CPU va GPU theo tai khoan cua ban.

Kaggle chi ho tro luong nay cho notebook. Neu ban can terminal, Remote-SSH, truy cap toan
bo he thong file hay mot may chu chay lien tuc, hay dung VPS cua ban.

## Ve notebook cu bi `Queued`

Notebook phien ban cu khoi chay mot external remote tunnel. Dung phien do va khong thu cap
token tunnel moi. Trong repository, notebook moi khong con co lenh nay. Metadata cua notebook
duoc dat CPU va Internet tat; bat Internet hay GPU trong Settings chi khi notebook cua ban can.

Kaggle huong dan ket noi VS Code qua Jupyter Server trong
[tai lieu Notebooks](https://www.kaggle.com/docs/notebooks). Cach ket noi tu VS Code bang
Kernel Picker duoc mo ta trong [tai lieu VS Code Jupyter](https://code.visualstudio.com/docs/datascience/jupyter-notebooks).

## Cap nhat notebook va kiem tra

```powershell
python update_notebooks.py
python -m unittest discover -s tests -v
```

`update_notebooks.py` tao lai ca hai notebook, xoa outputs/execution counts va giu metadata
Kaggle an toan cho notebook mau. Cac script SSH/ngrok cu van duoc giu lai nhu lich su cua
repository, nhung khong duoc notebook hay tai lieu nay su dung.
