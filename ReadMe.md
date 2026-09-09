<div align="center">

# Remote-SSH Kaggle using Visual Studio Code

**Connect to a Kaggle notebook over SSH from VS Code — password auth, no SSH keys required.**

Keep a 12-hour session running uninterrupted, use a real terminal and debugger,
and work with `.py` files instead of notebook cells.

<img src="imgs/architecture_ssh.png" alt="SSH architecture">

<img src="imgs/vscode_ssh_screen.png" alt="VS Code connected to Kaggle over SSH">

</div>

---

## Why

Kaggle's notebook interface is limiting once a project outgrows a few cells. Connecting over
SSH gives you the full VS Code experience against Kaggle's GPUs: integrated terminal,
breakpoint debugging, and a normal file-based project layout.

It also lets you stretch GPU quota. The default is 30 hours per week — if you stop the
notebook session near the end of hour 29 and SSH back in, you get roughly 12 more hours,
for about **42 hours a week**.

### Features

- 🔑 **Password authentication** — no SSH keypair to generate or upload
- 🧩 **Modular bash scripts** — easy to read, easy to customise
- ✨ **Oh My Posh included** — optional pretty terminal prompt
- ⚡ **Quick setup** — a handful of steps end to end

And plenty more to explore once you are in.

### How it works

The Kaggle notebook clones this repository and runs three small scripts — see
[SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) for the details of each:

| Script | Does |
|---|---|
| `install_ssh_server.sh` | Sets the root password and installs OpenSSH + ngrok |
| `add_ngrok_token.sh` | Registers your ngrok auth token |
| `run_ssh_server.sh` | Opens an ngrok TCP tunnel to port 22 |

---

## Contents

- [1. Prerequisites](#1-prerequisites)
- [2. Set up the Kaggle notebook](#2-set-up-the-kaggle-notebook)
- [3. Configure SSH in VS Code](#3-configure-ssh-in-vs-code)
- [4. Using it](#4-using-it)
- [Tips and tricks](#tips-and-tricks)
- [Conclusion](#conclusion)

---

## 1. Prerequisites

- Install **Visual Studio Code**: https://code.visualstudio.com/
- Create an **Ngrok** account: https://ngrok.com/

---

## 2. Set up the Kaggle notebook

- **2.1** Open the notebook: [Notebook Example](https://www.kaggle.com/hongtrung/ssh-kaggle-visualstudiocode)
    — or upload `notebook_example.ipynb` from this repository.

- **2.2** Choose `Copy & Edit`:

    ![](imgs/coppy_notebook.png)

- **2.3** In the right-hand sidebar, pick one of these two GPUs:

    ![](imgs/choose_gpu.png)

    > ⚠️ **Warning:** TPU is not supported.

- **2.4** Under `persistence`, select `Files only` so your files survive each Stop Session:

    ![](imgs/persistence.png)

- **2.5** Go to [Ngrok](https://ngrok.com/) → Your Authtoken → press copy:

    ![](imgs/get_ngork.png)

- **2.6** In cell 3 (the setup cell), set your SSH password and paste your Ngrok token:

    ```python
    ssh_password = "kaggle"  # Change this to your desired password

    # Run bash scripts
    !bash install_ssh_server.sh $ssh_password
    !bash add_ngrok_token.sh YOUR_NGROK_TOKEN  # Replace with your actual token
    ```

- **2.7** In the last cell (cell 4 — runs `bash run_ssh_server.sh`), note the `HostName` and
    `Port` from the ngrok output, e.g. `0.tcp.ap.ngrok.io` and `17520`. You need both in step **3.6**.

    ![](imgs/last_cell.png)

---

## 3. Configure SSH in VS Code

- **3.1** Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>X</kbd>, search for SSH, and install
    these two extensions:

    ![](imgs/ssh_extention.png)

- **3.2** For background on how Remote-SSH works, see the
    [VS Code Remote-SSH docs](https://code.visualstudio.com/docs/remote/ssh).

- **3.3** Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → `Remote-SSH: Connect to Host…`

    ![](imgs/remote_ssh.png)

- **3.4** Press `Configure SSH Host…`

    ![](imgs/choose_config.png)

- **3.5** Select `~/.ssh/config` — usually the first entry in the list.

    ![](imgs/choose_config_file.png)

- **3.6** Add this block to the config file:

    ```ssh-config
    Host Kaggle
        HostName 0.tcp.ap.ngrok.io
        Port 17520
        User root
    ```

    | Field | Value | Where it comes from |
    |---|---|---|
    | `Host` | `Kaggle` | Any name you like |
    | `HostName` | `0.tcp.ap.ngrok.io` | Step **2.7** |
    | `Port` | `17520` | Step **2.7** |
    | `User` | `root` | Always `root` |

- **3.7** Press <kbd>Ctrl</kbd>+<kbd>S</kbd>, then
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> → `Remote-SSH: Connect to Host…`

    ![](imgs/remote_ssh.png)

- **3.8** Pick the host you just named — `Kaggle`:

    ![](imgs/connect_ssh.png)

- **3.9** When prompted, enter the password you set in step **2.6** (default: `kaggle`).

- **3.10** Press `continue`:

    ![](imgs/press_continue.png)

    > 💡 **Tip:** If VS Code asks you to choose the operating system, select `linux`.

- **3.11** The bottom-left corner confirms the connection:

    ![](imgs/connected.png)

---

## 4. Using it

- **4.1** Press <kbd>Ctrl</kbd>+<kbd>K</kbd> <kbd>O</kbd>, enter the path `/kaggle`, press `ok`.

    ![](imgs/choose_dir.png)

- **4.2** Open a terminal with <kbd>Ctrl</kbd>+<kbd>J</kbd>. The system python already
    carries the full Kaggle stack (torch, numpy, …), so you can start working right away.
    `uv` is preinstalled for anything you need to add:

    ```bash
    uv pip install --system <package>
    ```

    Prefer an isolated environment? Create it with `--system-site-packages` so it can still
    see the preinstalled Kaggle packages:

    ```bash
    uv venv --system-site-packages .venv
    source .venv/bin/activate
    uv pip install <package>
    ```

    > ⚠️ **Warning:** a plain `uv venv`, without `--system-site-packages`, starts empty —
    > `import torch` fails inside it. And outside a virtual environment `uv pip install`
    > needs the `--system` flag, otherwise it exits with `No virtual environment found`.

- **4.3** Activate CUDA. The image already ships the driver — it is simply missing from
    the SSH shell's environment, because that shell does not inherit the notebook kernel's
    paths. Two exports fix it instantly, with no download:

    ```bash
    export PATH=/opt/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:$LD_LIBRARY_PATH
    ```

    They apply to the current shell only — append them to `/root/.bashrc` if you open
    several terminals, and redo them after each Stop Session.

    > 📝 **Fallback:** if those paths move in a future Kaggle image, installing the driver
    > utilities works too — it just downloads a few hundred MB, and also has to be repeated
    > after every Stop Session: `sudo apt install nvidia-utils-515 -y`

- **4.4** Check the GPU is visible:

    ```bash
    nvidia-smi
    ```

    ![](imgs/check_gpu.png)

    > 💡 **Tip:** If `nvidia-smi` reports no devices, the session has no GPU attached at all — check
    > the `Accelerator` setting from step **2.3**.

- **4.5** After each Stop Session, you only need to redo a subset:

    1. Run cell 4 to get the new hostname and port
    2. Update your SSH config with them (step **3.6**)
    3. Reconnect from VS Code (steps **3.7** → **3.8** → **3.9**)
    4. Carry on working (steps **4.1** → **4.2** → **4.3** → **4.4**)

---

## Tips and tricks

- To stretch GPU quota, stop the notebook session and SSH back in before you hit the
  30-hour weekly limit — that gets you up to ~42 hours a week.
- Use the integrated terminal rather than notebook cells for anything shell-shaped.
- Set breakpoints and use the VS Code debugger instead of `print` debugging.
- Keep code in `.py` files and import across them, like a normal project.

### Where your files live

The `Data` panel on the right has two sections, and they map to different paths with
different rules:

| Section | Path | Writable | Size limit |
|---|---|---|---|
| **Input** | `/kaggle/input/...` | ❌ Read-only | ~107 GB private, unlimited public |
| **Output** | `/kaggle/working/...` | ✅ Your workspace | ~20 GB |

![](imgs/file_relationship.png)

---

## Conclusion

With Remote-SSH Kaggle and Visual Studio Code you get the full weight of Kaggle's GPUs
behind a development environment you actually enjoy using — a real terminal, a real
debugger, and a normal project layout. Set it up once and the only thing you repeat
between sessions is step **4.5**.
