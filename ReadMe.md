# Kaggle + VS Code Remote Tunnels

Kết nối VS Code trên Windows tới môi trường Kaggle bằng **Remote - Tunnels** và
token Dev Tunnel. Notebook tự chứa launcher; bạn có thể nhập file vào Kaggle và
chạy mà không cần clone repository.

## Chạy notebook mới

1. Nhập [notebook cá nhân](fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb) hoặc
   [notebook mẫu](notebook_example.ipynb) vào Kaggle.
2. Bật **Internet**. Chọn GPU trong Settings nếu cần GPU.
3. Trong **Add-ons > Secrets**, thêm và bật:

   | Tên Secret | Giá trị |
   |---|---|
   | `VSCODE_TUNNEL_ID` | ID đầy đủ, ví dụ `swift-field-gbd67x7.asse` |
   | `VSCODE_TUNNEL_TOKEN` | Token Dev Tunnel cấp cho ID đó |

4. Chạy ba cell code theo thứ tự: nạp launcher, tải VS Code CLI, khởi động tunnel.
   **Save & Run All** cũng chạy tunnel và giữ cell cuối hoạt động. Không cần restart.
5. Giữ cell cuối chạy. Với Save & Run All, theo dõi log của phiên đang chạy.

## Kết nối trên Windows

1. Cài extension **Remote - Tunnels** trong VS Code.
2. Nhấn **Ctrl+Shift+P > Remote Tunnels: Connect to Tunnel**.
3. Đăng nhập cùng tài khoản GitHub đã dùng để tạo Dev Tunnel.
4. Chọn máy **kaggle** sau khi log báo tunnel đã kết nối, rồi mở `/kaggle/working`.
5. Trong **Python: Select Interpreter**, chọn đường dẫn Python notebook đã in ra.

Bạn có thể sửa file, mở terminal và debug trên Kaggle. Cách này dùng VS Code
Remote Tunnels thay cho kết nối SSH bằng hostname/port; Windows không cần chạy
ngrok, Cloudflare hay VPS. Bạn cũng có thể mở link `vscode.dev` do CLI in ra.

## Tạo hoặc cấp lại token

Cài Dev Tunnels CLI trên Windows và đăng nhập GitHub một lần:

```powershell
winget install Microsoft.devtunnel
```

Mở PowerShell mới sau khi cài, rồi chạy:

```powershell
devtunnel user login -g -d
```

Nếu chưa có tunnel, tạo bằng `devtunnel create` và ghi lại Tunnel ID. Với tunnel
đã tạo trong phiên làm việc này, cấp token bằng:

```powershell
devtunnel token swift-field-gbd67x7.asse --scopes host --scopes manage --scopes connect
```

Lặp lại `--scopes` cho từng quyền. Token hiện có thời hạn khoảng **24 giờ**;
khi hết hạn, cấp lại với cùng ID và cập nhật `VSCODE_TUNNEL_TOKEN` trong Secrets.
Thời hạn tunnel 30 ngày không kéo dài thời hạn token. Token GitHub PAT không
thay thế được token Dev Tunnel.

## Python, GPU và các phiên mới

Launcher truyền môi trường Python/CUDA của notebook cho tiến trình VS Code.
Chọn interpreter đã in ra nếu VS Code tự chọn interpreter khác. Kiểm tra GPU:

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

GPU chỉ có khi đã bật Accelerator. Notebook dùng thư viện/driver sẵn có của
image Kaggle.

Interrupt cell cuối hoặc Stop Session để đóng tunnel. Sau mỗi phiên mới, chạy
lại cả ba cell. Dừng phiên tunnel cũ trước khi dùng cùng ID trong một phiên khác.
Giới hạn thời gian và quota GPU của Kaggle vẫn áp dụng.

## Xử lý lỗi

| Thông báo | Cách xử lý |
|---|---|
| Thiếu `VSCODE_TUNNEL_ID` hoặc `VSCODE_TUNNEL_TOKEN` | Thêm và bật cả hai Secrets cho notebook. |
| ID cần có vùng | Dùng ID đầy đủ, gồm hậu tố như `.asse`. |
| Token đã hết hạn hoặc lỗi `401/403` | Cấp lại token có các quyền `host`, `manage`, `connect`, đúng Tunnel ID; cập nhật Secret. |
| Không tải được VS Code CLI | Bật Internet và chạy lại cell tải CLI. |
| Không thấy máy trong VS Code | Chờ log kết nối; đăng nhập đúng tài khoản tạo tunnel và chọn extension Remote - Tunnels. |
| Debugger warning / SyntaxWarning của nbconvert | Các cảnh báo này không phải lỗi xác thực tunnel; xem thông báo sau đó trong log. |

## Source và kiểm tra

`vscode_tunnel.py` là launcher dùng thư viện chuẩn Python. `update_notebooks.py`
nhúng toàn bộ launcher vào cả hai notebook, xóa outputs/execution counts và giữ
cấu hình accelerator/data sources của notebook cá nhân.

```bash
python update_notebooks.py
python -m unittest discover -s tests -v
```

Các script OpenSSH/ngrok trước đây vẫn nằm trong repository cho người dùng
luồng cũ; xem [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md).

Tài liệu chính thức: [VS Code Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels),
[Dev Tunnels CLI](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/cli-commands),
[thời hạn token](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/security#tunnel-access).
