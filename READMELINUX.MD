# 🐧 Running Bedrock Node on Linux (Ubuntu / Debian)

Bedrock Node is built with cross-platform support out of the box. It automatically handles Linux-specific binary paths (`LD_LIBRARY_PATH`), process management, and headless execution. 

Follow this guide to get your server panel running smoothly on a Linux VPS or dedicated server.

---

## 1. System Dependencies (Required)
Mojangs official Linux Bedrock Dedicated Server binary (`bedrock_server`) requires specific system C libraries to execute without crashing. 

Run the following command in your terminal to install them:
  ```bash
  sudo apt update
  sudo apt install -y python3 python3-pip libcurl4 libssl-dev ca-certificate
  ```
2. Install Python Dependencies
Navigate to your project directory and install the required Python packages using your requirements.txt:
  ```bash
  pip install -r requirements.txt
  ```

3. Configuration Setup (Desktop vs. Headless VPS)
Bedrock Node features an automated Tkinter Setup Wizard for first-time installations. Choose the method that matches your environment:

Option A: Running on a Linux Desktop (GUI)
If your Linux machine has a graphical desktop interface, install Tkinter so the wizard window can render:
  ```bash
  sudo apt install -y python3-tk
  ```

Then launch the script normally:
  ```bash
  python3 "Bedrock Node.py"
  ```

Option B: Running on a Headless VPS (Terminal Only / No GUI)
If your VPS doesnt have a monitor or graphical interface, Tkinter cannot render the wizard. To bypass this:

Run Bedrock Node once on your local Windows PC to complete the setup wizard and generate your server_vault/ folder (securekeys.env and secureaccounts.json).

Upload the server_vault/ folder to your Linux server in the same directory as Bedrock Node.py.

Start the node (it will detect your existing configuration and start up cleanly):
  ```bash
  python3 "Bedrock Node.py"
  ```
4. Bedrock Server Files
Ensure you place the official Linux Bedrock Dedicated Server files (downloaded and unzipped from Mojang) in the directory directly above Bedrock Node so the script can locate the executable at ../bedrock_server[cite: 1].

5. Firewall & Ports
Make sure your Linux firewall (e.g., ufw) allows incoming traffic on the required ports:

UDP 19132 — Minecraft Bedrock game port (unless using Playit.gg / Cloudflare Tunnel).

TCP 5000 — Bedrock Node Web Dashboard (unless using a reverse proxy or Cloudflare Tunnel).

Example using UFW:
 ```bash 
  sudo ufw allow 19132/udp
  sudo ufw allow 5000/tcp
  sudo ufw reload
  ```

