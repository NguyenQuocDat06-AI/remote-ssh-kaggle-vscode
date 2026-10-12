"""Build self-contained VS Code Remote Tunnels notebooks from the launcher."""

import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent


def cell(kind, source, cell_id):
    result = {"cell_type": kind, "id": cell_id, "metadata": {},
              "source": textwrap.dedent(source).strip().splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def notebook_cells():
    return [
        cell("markdown", """
            # Kaggle kết nối VS Code bằng Remote Tunnels

            Notebook tự chứa toàn bộ launcher. Nhập file vào Kaggle và bật **Internet**.
            Chọn GPU trong Settings nếu cần GPU; notebook cũng chạy được với CPU.

            Trong **Add-ons > Secrets**, thêm và bật hai Secrets:

            | Tên | Giá trị |
            |---|---|
            | `VSCODE_TUNNEL_ID` | `swift-field-gbd67x7.asse` (ID đầy đủ của tunnel bạn đã tạo) |
            | `VSCODE_TUNNEL_TOKEN` | Chuỗi token Dev Tunnel được cấp cho tunnel đó |

            Cấp token trên Windows bằng:
            ```powershell
            devtunnel token swift-field-gbd67x7.asse --scopes host --scopes manage --scopes connect
            ```
            Token hiện có thời hạn khoảng **24 giờ**. Khi hết hạn, cấp lại bằng lệnh trên
            và cập nhật Secret. Thời hạn tunnel 30 ngày không kéo dài thời hạn token.

            Chạy ba cell code theo thứ tự, hoặc chọn **Save & Run All**. Cả chế độ
            tương tác và batch đều khởi động tunnel; cell cuối giữ trạng thái **Running**.
            Với Save & Run All, xem log của phiên đang chạy để biết trạng thái kết nối.
            Không cần restart sau khi cài đặt.

            Nguồn: https://github.com/NguyenQuocDat06-AI/remote-ssh-kaggle-vscode
            Hướng dẫn: https://code.visualstudio.com/docs/remote/tunnels
        """, "instructions"),
        cell("markdown", """
            ## 1. Nạp launcher

            Cell này định nghĩa các hàm chạy tunnel. Token chỉ được đọc từ Secrets
            khi chạy cell cuối, không được ghi vào source hay in trong log.
        """, "launcher-instructions"),
        cell("code", (ROOT / "vscode_tunnel.py").read_text(encoding="utf-8"), "launcher"),
        cell("markdown", """
            ## 2. Tải VS Code CLI

            Tải bản stable chính thức và kiểm tra CLI chạy được trên image Kaggle.
            Chạy lại bước này sau mỗi phiên mới. Python/CUDA dùng môi trường notebook hiện tại.
        """, "install-instructions"),
        cell("code", """
            CODE_CLI = install_vscode_cli(Path("/kaggle/working/.vscode-tunnel/bin"))
            print("Python của notebook:", sys.executable, flush=True)
        """, "install"),
        cell("markdown", """
            ## 3. Khởi động tunnel và kết nối từ Windows

            1. Trong VS Code trên Windows, cài extension **Remote - Tunnels**.
            2. Chạy cell bên dưới và chờ log báo tunnel đã kết nối. Tên máy có hậu tố của
               session Kaggle để không xung đột với phiên cũ.
            3. Nhấn **Ctrl+Shift+P > Remote Tunnels: Connect to Tunnel**.
            4. Đăng nhập cùng tài khoản **GitHub** đã dùng để tạo Dev Tunnel và chọn **kaggle**.
            5. Mở thư mục **/kaggle/working**. Trong **Python: Select Interpreter**, chọn đường dẫn
               Python đã in ở cell cài đặt.

            Kết nối đi qua VS Code Remote Tunnels. Bạn có thể mở terminal, sửa file và debug;
            notebook không yêu cầu ngrok, mật khẩu SSH, VPS, domain hoặc Cloudflare trên Windows.
            Bạn cũng có thể mở link `vscode.dev` mà CLI in ra.

            **Giữ cell cuối chạy** trong lúc làm việc. Interrupt/Stop sẽ đóng tunnel. Dừng mọi
            cell tunnel cũ trước khi mở phiên mới. Nếu log báo WebSocket bị reset liên tục, cell
            sẽ tự dừng sau bốn lần thay vì reconnect vô hạn.
            Giới hạn thời gian phiên và GPU của Kaggle vẫn áp dụng. Sau khi dừng phiên,
            chạy lại ba cell và dùng token chưa hết hạn. Dừng tunnel cũ trước khi chạy phiên mới
            với cùng Tunnel ID.

            Nếu gặp `401/403`, kiểm tra token có hết hạn, có đúng tunnel và có đủ quyền
            `host`, `manage`, `connect` không; cấp lại token nếu cần.

            Kiểm tra GPU trong terminal VS Code (chỉ có GPU nếu đã bật Accelerator):
            ```bash
            nvidia-smi
            python -c "import torch; print(torch.cuda.is_available())"
            ```
        """, "connect-instructions"),
        cell("code", """
            TUNNEL_NAME = session_tunnel_name()
            run_vscode_tunnel(CODE_CLI, name=TUNNEL_NAME)
        """, "tunnel"),
    ]


def main():
    cells = notebook_cells()
    for filename in ("notebook_example.ipynb", "fork-of-ssh-kaggle-visualstudiocode-9d17dd.ipynb"):
        path = ROOT / filename
        notebook = json.loads(path.read_text(encoding="utf-8"))
        notebook["cells"] = cells
        notebook["nbformat"] = 4
        notebook["nbformat_minor"] = 5
        notebook["metadata"]["language_info"] = {"name": "python", "file_extension": ".py",
                                                 "mimetype": "text/x-python"}
        kaggle = notebook["metadata"].get("kaggle")
        if kaggle is not None:
            kaggle.pop("dockerImageVersionId", None)
            kaggle["isInternetEnabled"] = True
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"Updated {filename}: standalone Remote Tunnels, no credentials or outputs.")


if __name__ == "__main__":
    main()
