# Bedrock-Node

ATTENTION both the PY and the exe must be inside of a Bedrock Node folder in your server directory. if you download the Zips remove the Bedrock Node folder from the zips after you unpack them and put them in your server folder. check releases for official vs

Discord link for contacting me reporting bugs asking questions about installation 
https://discord.com/invite/VF2b9Gg7Xg

An automated server management wrapper and admin web dashboard for Minecraft Bedrock Dedicated Servers (BDS). Featuring real-time console streaming, automated backups/restarts, crash detection, hourly player analytics, and a secure Ban Matrix.

---

### 🚀 Quick Start / Download

| Distribution | Link | Description |
| :--- | :--- | :--- |
| **Windows Executable (`.exe`)** | **[Download Latest Release](https://github.com/stonercraft420/Bedrock-Node/releases/latest/download/Bedrock.Node.exe.zip)** | **Recommended.** Standalone release with no Python installation required. |
| **Python Source (`.py`)** | **[Download Source Code (Zip)](https://github.com/stonercraft420/Bedrock-Node/releases/latest)** | Opens the latest release page to grab the source zip or compiled assets. |

---

### Key Features

- **Web Control Panel**: Real-time server status, console output, and administrative web controls.
- **Automated Backups**: Scheduled server backups with automatic retention management.
- **Crash Recovery**: Auto-detects server crashes and restarts the process automatically.
- **Player Analytics**: Tracks player activity and logs hourly metrics.
- **Ban Matrix**: Streamlined player moderation and list management.

---

## Setup & Usage

**ATTENTION:** Both the `.py` source code, the `requirements.txt` file, and the `.exe` must be kept inside a **Bedrock Node** folder within your main server directory. If you download the Zips, remove the inner `Bedrock Node` folder after unpacking and place it directly into your server folder.

### Option 1: Running the Executable (.exe)
1. Download `Bedrock-Node.exe` from the Releases Page.
2. Place the **Bedrock Node** folder from the release zip directly into your Minecraft Bedrock Server directory.
3. Run `Bedrock-Node.exe` and access the dashboard in your web browser (`http://localhost:5000`).

### Option 2: Running from Source (.py)
1. Clone or download this repository and unzip the source files.
2. **Install Python:** Ensure you have Python v3.12 or newer installed. If you don't have it yet, open PowerShell and run:
   ```powershell
   winget install Python.Python.3.12

(Close and reopen your terminal after installing).
3. Download the Python source zip, unzip it, take the Bedrock Node folder nested inside out, and place that folder directly into your server directory.
4. Open a command prompt inside that Bedrock Node folder and install the required packages:
  ```powershell
  pip install -r requirements.txt
  ```

(close powershell)  
5. Run your script (Bedrock Node.py) to launch the setup wizard and start the server.
