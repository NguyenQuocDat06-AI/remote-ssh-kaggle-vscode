# 🔧 Bash Scripts Guide

This repository uses modular bash scripts to set up SSH server on Kaggle with password authentication. Here's what each script does:

## 📁 Scripts Overview

### 1. `install_ssh_server.sh`
**Purpose:** Sets up SSH server with password authentication

**Usage:**
```bash
bash install_ssh_server.sh [PASSWORD]
```

**Parameters:**
- `PASSWORD` (optional): Your desired SSH password. Default is "kaggle" if not provided.

**What it does:**
1. Sets root password for SSH authentication
2. Downloads and installs ngrok (if not already installed)
3. Installs OpenSSH server
4. Configures SSH to allow:
   - Root login
   - Password authentication
   - Public key authentication (optional)
5. Restarts SSH service

**Example:**
```python
# In Kaggle notebook
ssh_password = "my_secure_password"
!bash install_ssh_server.sh $ssh_password
```

---

### 2. `add_ngrok_token.sh`
**Purpose:** Adds your ngrok authentication token

**Usage:**
```bash
bash add_ngrok_token.sh YOUR_NGROK_TOKEN
```

**Parameters:**
- `YOUR_NGROK_TOKEN`: Your ngrok authentication token from https://dashboard.ngrok.com/auth

**What it does:**
1. Configures ngrok with your authentication token
2. Saves token to ngrok configuration file

**Example:**
```python
# In Kaggle notebook
!bash add_ngrok_token.sh YOUR_NGROK_TOKEN
```

---

### 3. `run_ssh_server.sh`
**Purpose:** Starts ngrok tunnel to expose SSH server

**Usage:**
```bash
bash run_ssh_server.sh
```

**Parameters:** None

**What it does:**
1. Starts ngrok TCP tunnel on port 22 (SSH)
2. Uses Asia Pacific region (--region ap)
3. Displays connection information (hostname and port)

**Output:**
```
Forwarding: tcp://0.tcp.ap.ngrok.io:12345 -> localhost:22
```

Use the hostname (`0.tcp.ap.ngrok.io`) and port (`12345`) to connect via VS Code.

**Example:**
```python
# In Kaggle notebook
!bash run_ssh_server.sh
```

---

## 🛠️ Customization

### Change Default Password
Edit the `PASSWORD` line near the top of `install_ssh_server.sh`:
```bash
PASSWORD=${1:-"your_new_default_password"}
```

### Change Ngrok Region

> [!NOTE]
> Recent ngrok versions print `Flag --region has been deprecated, ngrok automatically
> chooses the region with lowest latency`. The flag is still accepted, but you normally
> no longer need to set it.

To pin a region anyway, edit the `ngrok` line in `run_ssh_server.sh`:
```bash
ngrok tcp 22 --region us  # or eu, ap, au, sa, jp, in
```

### Add Additional SSH Configuration
In `install_ssh_server.sh`, add your line alongside the other `sshd_config` writes —
anywhere above `sudo service ssh restart`:
```bash
echo "YourCustomConfig yes" | sudo tee -a /etc/ssh/sshd_config
```

> [!WARNING]
> Use `| sudo tee -a`, not `sudo echo ... >>`. With `sudo echo`, the redirect is performed
> by your *own* shell before `sudo` runs, so it fails on a root-owned file. The script
> itself already uses the `tee` form.