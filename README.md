> ⚠️ **CRITICAL PREREQUISITE WARNING:** 
> Before launching Bedrock Node for the first time, you **must** have **Python (v3.10 or newer)** installed on your system. 
> If you don't have it installed yet, open **PowerShell** and run this command first in powershell:

> winget install Python.Python.3.12

> *(After running the command, close and reopen PowerShell. If you prefer downloading it manually from python.org, make sure to check the box for **"Add python.exe to PATH"**).*

---

# Bedrock Node Hub 🚀
A lightweight, open-source web dashboard and server management utility for Minecraft Bedrock dedicated servers. 

Designed for server administrators who want powerful automation, live metrics, and remote control without heavy, closed-source bloat.

---

## ✨ Key Features
- **Interactive Setup Wizard:** A clean graphical desktop wizard that configures your admin logins, security codes, and network tunnels on first launch.
- **Flask Web Dashboard:** Monitor CPU, RAM, disk space, uptime, and online players in real-time. Run console commands remotely from any device.
- **Ban Matrix:** Secure blacklisting system protected by a secondary security code with automated brute-force lockouts.
- **Automated Backups/restarts:** Scheduled daily raw world backups.
- **Crash Detection/Prevention:** Detects if the server goes down and starts a timer to restart it.
- **Discord Integration:** Push instant notifications for player joins/leaves, unique milestones, and bans, plus live status/player count voice channels.
- **Historical Metrics & Graphs:** Matplotlib-powered player statistics tracking across day, month, and year views.

---

## 📦 Installation & First Run

1. **Verify Python:** Ensure Python is installed (see the warning banner at the top if you haven't yet).
2. **Place the Folder:** Drop "Bedrock Node" folder directly into your root Bedrock server folder (right next to your `bedrock_server.exe` file).
3. **Launch:** Double-click `Bedrock Node.py`. 
   - *Note:* On first launch, the script will automatically detect and install any required Python packages (`flask`, `psutil`, `discord.py`, etc.) directly in your console.
4. **Configure:** The graphical **Setup Wizard** will open automatically. Walk through the steps to set up your administrator credentials, connection preferences, and optional Discord webhooks.
5. **Shortcuts:** Quick-access web panel shortcuts will be automatically saved inside your `server_vault` folder and on your Desktop.
6. **Access the Dashboard:** Once finished, your browser will open the local admin web panel automatically at `http://localhost:5000`.

---

## 🔒 Security Features & Hardening
Bedrock Node is built with multi-layered security protections:
- **Hashed Passwords:** Admin passwords use secure cryptographic hashing (Werkzeug security).
- **Session Isolation:** Flask cookies are hardened with HttpOnly, Secure, and SameSite=Lax flags.
- **Brute-Force Lockout:** IP-based rate limiting locks out unauthorized login attempts and Ban Matrix code entries after 3 failures.
- **Ban Matrix Security Pin:** Banning or pardoning players from the web panel requires a secondary secret security code.
- **Settings Wall:** Modifying critical integrations, bot tokens, or admin credentials requires a dedicated settings password.

---

## 📂 Data Structure & Server Vault
All sensitive tokens, configuration files, logs, and database metrics are safely isolated inside a dedicated folder called `server_vault`, which is automatically created inside your script directory:
- `securekeys.env` — Encrypted configuration parameters and tokens.
- `secureaccounts.json` — Hashed administrator login credentials.
- `blacklist.json` — Active Ban Matrix records.
- `unique_players.json` — Permanent tracking database for unique joins.
- `admin_notes.txt` — Persistent admin scratchpad & watchlist.
- `command_logs/` — Daily archives of all executed server commands.
- `metrics_archive/` — Monthly CSV logs for player counts & graphs.
- `daily_backup/` — Automated raw world backups with auto-purge.

---

## 📄 Terms & Distribution Policy
This source code is provided for transparency so you can inspect how it operates. However, **modification, re-hosting, or redistribution of this software is strictly prohibited.** All official updates and versions must be obtained directly from the author.

====================================================================
                        NEED HELP OR SUPPORT?
====================================================================
Bedrock Node is built with transparency and security in mind. If you 
encounter issues, run into bugs, or need assistance configuring 
your server, reach out via our official Discord community:

* **Creator:** Nutcrustys420
💬 Official Discord Support: https://discord.gg/aSVPbEpkuA

⚠️ DISCLAIMER:
Bedrock Node is provided as-is under our Source-Available license. 
We will never ask for your server passwords, private encryption 
keys, or admin credentials. Always download official updates directly 
from our primary release page.