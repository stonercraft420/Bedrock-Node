import base64
import csv
import html
import io
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
import urllib.request
import asyncio
import sys
import platform
import stat

REQUIRED_PACKAGES = [
    "discord.py",
    "python-dotenv",
    "flask",
    "flask-socketio",
    "matplotlib",
    "numpy",
    "psutil",
    "colorama",
    "werkzeug",
]


def check_and_install_packages():
  for package in REQUIRED_PACKAGES:
    import_name = (
        "discord"
        if package == "discord.py"
        else "dotenv"
        if package == "python-dotenv"
        else package.replace("-", "_")
    )
    try:
      __import__(import_name)
    except ImportError:
      print(f"[SETUP] Missing required package '{package}'. Installing...")
      subprocess.check_call([sys.executable, "-m", "pip", "install", package])


check_and_install_packages()

import colorama
import secrets
import tkinter as tk
import webbrowser

from datetime import datetime, timedelta
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template_string, request, send_from_directory, session, url_for
from flask_socketio import SocketIO, emit
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import psutil
from tkinter import messagebox, ttk
from werkzeug.security import check_password_hash, generate_password_hash

logging.getLogger('werkzeug').setLevel(logging.ERROR)

DISCORD_ENABLED = True
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(SCRIPT_DIR, "server_vault")
if not os.path.exists(DATA_DIR):
  os.makedirs(DATA_DIR)

load_dotenv(os.path.join(DATA_DIR, "securekeys.env"), override=True)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
ADMIN_WEBHOOK_URL = os.getenv("ADMIN_WEBHOOK_URL", "").strip()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default_secret_key")
BAN_SECRET_CODE = os.getenv("BAN_SECRET_CODE", "BAN")

DISCORD_ENABLED = bool(DISCORD_BOT_TOKEN)
WEBHOOK_ENABLED = bool(ADMIN_WEBHOOK_URL)

VC_STATUS_ID = int(os.getenv("VC_STATUS_ID", 0))
VC_PLAYERS_ID = int(os.getenv("VC_PLAYERS_ID", 0))

FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

G, W, R, Y, C, B, PURPLE, END = (
    "\033[92m",
    "\033[97m",
    "\033[91m",
    "\033[93m",
    "\033[96m",
    "\033[1m",
    "\033[95m",
    "\033[0m",
)

colorama.init(autoreset=True)

app = Flask(__name__, static_folder='images', static_url_path='/images')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

app.config.update(
    SESSION_COOKIE_SECURE=True, 
    SESSION_COOKIE_HTTPONLY=True, 
    SESSION_COOKIE_SAMESITE="Lax", 
)

IS_WINDOWS = os.name == "nt"
SERVER_EXE = "bedrock_server.exe" if IS_WINDOWS else "bedrock_server"
BANNER_URL = "/images/banner.png"
BACKGROUND_URL = "/images/background.png"

BAN_HTML_TEMPLATE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="/icon.png">
<link rel="apple-touch-icon" href="/icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Bedrock Node">
<style>
body { 
    background: linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)), url("{{banner}}") fixed center; 
    background-size: cover; 
    color: #0f4; 
    font-family: sans-serif; 
    margin: 0; 
    padding: 20px; 
    display: flex; 
    justify-content: center; 
    align-items: center;
    min-height: 100vh;
    box-sizing: border-box;
}

.panel { 
    width: 100%; 
    max-width: 750px; 
    border: 1px solid #0f45; 
    padding: 25px; 
    border-radius: 20px; 
    background: rgba(0,12,0,0.95); 
    box-sizing: border-box; 
    position: relative; 
}

.close-btn {
    position: absolute;
    top: 15px;
    right: 15px;
    width: auto;
    padding: 5px 12px;
    background: #ff4444;
    color: #fff;
    font-size: 14px;
    text-decoration: none;
    font-family: monospace;
    font-weight: bold;
    border-radius: 5px;
    margin: 0;
}
.close-btn:hover { background: #ff2222; }

h2, h3 { text-align: center; color: #0f4; }
input { width: 100%; background: #000; color: #0f4; border: 1px solid #0f44; padding: 10px; border-radius: 10px; box-sizing: border-box; font-size: 14px; margin-bottom: 10px; }
button { width: 100%; padding: 10px; background: #0f4; color: #000; font-weight: bold; border: none; cursor: pointer; border-radius: 10px; font-size: 14px; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; font-family: monospace; }
th, td { border: 1px solid #0f43; padding: 8px; text-align: left; }
th { background: rgba(0,255,64,0.1); color: #0ff; }
.del-btn { background: #ff4444; color: #fff; padding: 5px 10px; border-radius: 5px; font-size: 12px; width: auto; margin: 0; }
</style></head><body>

<div class="panel">
    <a href="/" class="close-btn">[X]</a>
    <h2>Ban Matrix</h2>
    
    <h3>Add Target to Blacklist</h3>
    <form id="banForm" method="POST" onsubmit="interceptBan(event)">
        <input type="hidden" name="action" value="add">
        <input id="banName" name="name" placeholder="Exact Gamertag..." required autocomplete="off">
        <input id="banXuid" name="xuid" placeholder="Xbox XUID (Optional, blank if unknown)..." autocomplete="off">
        <input id="banReason" name="reason" placeholder="Reason (e.g. Griefing, Exploits)..." required autocomplete="off">
        <button type="submit">EXECUTE BAN</button>
    </form>

    <h3 style="margin-top:30px;">Active Blacklisted Records</h3>
    <table>
        <tr><th>Gamertag / Key</th><th>Reason</th><th>Admin</th><th>Date</th><th>Action</th></tr>
        {% if bans %}
            {% for key, info in bans.items() %}
            <tr>
                <td><b>{{ info.name }}</b><br><span style="font-size:10px;color:#888;">{{ key }}</span></td>
                <td>{{ info.reason }}</td>
                <td>{{ info.admin }}</td>
                <td>{{ info.date }}</td>
                <td>
                    <button type="button" class="del-btn" onclick="pardonPlayer('{{ key }}')">Pardon</button>
                </td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="5" style="text-align:center; color:#ffcc00;">No active bans found. Network clean.</td></tr>
        {% endif %}
    </table>
</div>

<!-- SECURE MODAL POPUP (SHARED FOR BAN & PARDON) -->
<div id="securityModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
    <div style="background:rgba(0,12,0,0.98); border:1px solid #0f45; padding:25px; border-radius:20px; width:100%; max-width:400px; text-align:center; box-sizing:border-box;">
        <h3 id="modalTitle" style="color:#0f4; margin-top:0;">SECURITY CHECK</h3>
        <p id="modalDesc" style="color:#0ff; font-size:13px; font-family:monospace; margin-bottom:15px;">Enter Secret Security Code:</p>
        <input type="password" id="modalCodeInput" placeholder="Secret Security Code..." style="margin-bottom:15px;" autocomplete="off">
        <div style="display:flex; gap:10px;">
            <button type="button" id="modalConfirmBtn" style="background:#0f4; color:#000; margin-top:0;">CONFIRM</button>
            <button type="button" onclick="closeSecurityModal()" style="background:#ff4444; color:#fff; margin-top:0;">CANCEL</button>
        </div>
    </div>
</div>

<script>
let currentMode = null; 
let targetKey = null;

function closeSecurityModal() {
    document.getElementById('securityModal').style.display = 'none';
    document.getElementById('modalCodeInput').value = '';
    currentMode = null;
    targetKey = null;
}

function interceptBan(e) {
    e.preventDefault();
    currentMode = 'ban';
    document.getElementById('modalTitle').innerText = 'BAN SECURITY CHECK';
    document.getElementById('modalDesc').innerText = 'Enter Secret Security Code to execute this ban:';
    document.getElementById('modalCodeInput').value = '';
    document.getElementById('securityModal').style.display = 'flex';
    document.getElementById('modalCodeInput').focus();
}

function pardonPlayer(key) {
    currentMode = 'pardon';
    targetKey = key;
    document.getElementById('modalTitle').innerText = 'PARDON SECURITY CHECK';
    document.getElementById('modalDesc').innerText = 'Enter Secret Security Code to pardon this player:';
    document.getElementById('modalCodeInput').value = '';
    document.getElementById('securityModal').style.display = 'flex';
    document.getElementById('modalCodeInput').focus();
}

document.getElementById('modalConfirmBtn').onclick = function() {
    const secCode = document.getElementById('modalCodeInput').value;
    if (!secCode) return;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/bans';

    if (currentMode === 'ban') {
        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = 'add';
        form.appendChild(actionInput);

        const nameInput = document.createElement('input');
        nameInput.type = 'hidden';
        nameInput.name = 'name';
        nameInput.value = document.getElementById('banName').value;
        form.appendChild(nameInput);

        const xuidInput = document.createElement('input');
        xuidInput.type = 'hidden';
        xuidInput.name = 'xuid';
        xuidInput.value = document.getElementById('banXuid').value;
        form.appendChild(xuidInput);

        const reasonInput = document.createElement('input');
        reasonInput.type = 'hidden';
        reasonInput.name = 'reason';
        reasonInput.value = document.getElementById('banReason').value;
        form.appendChild(reasonInput);
    } else if (currentMode === 'pardon') {
        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = 'remove';
        form.appendChild(actionInput);

        const keyInput = document.createElement('input');
        keyInput.type = 'hidden';
        keyInput.name = 'key';
        keyInput.value = targetKey;
        form.appendChild(keyInput);
    }

    const codeInput = document.createElement('input');
    codeInput.type = 'hidden';
    codeInput.name = 'sec_code';
    codeInput.value = secCode;
    form.appendChild(codeInput);

    document.body.appendChild(form);
    form.submit();
};
</script>
</body></html>
"""

LOG_DIR = os.path.join(DATA_DIR, "command_logs")
SERVER_LOG_DIR = os.path.join(DATA_DIR, "server_logs")
NOTES_FILE = os.path.join(DATA_DIR, "admin_notes.txt")
UNIQUE_PLAYERS_FILE = os.path.join(DATA_DIR, "unique_players.json")
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")
ADMIN_LOG_FILE = os.path.join(DATA_DIR, "admin_logins.txt")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "secureaccounts.json")


state_lock = threading.Lock()
chart_lock = threading.Lock()
notes_lock = threading.Lock()
blacklist_lock = threading.Lock()
chart_cache_lock = threading.Lock()
unique_players_lock = threading.Lock()

mc_process = None
is_running = False
is_restarting = False
seconds_left = 0
start_time = None
restart_timer_start = datetime.now()
last_actions = []
failed_attempts = {}
needs_backup = False
last_backup_date = None
is_backing_up = False
ONLINE_PLAYERS = set()
CHART_CACHE = {}

intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)

def start_playit_process():
  """Spawns playit as a background process cross-platform."""
  os_type = platform.system().lower()
  filename = "playit.exe" if os_type == "windows" else "playit"
  playit_path = os.path.abspath(os.path.join(DATA_DIR, filename))

  if os.path.exists(playit_path):
    try:
      print(f"{G}[PLAYIT] Launching Playit.gg Tunnel Agent...{END}")
      if os_type == "windows":
        subprocess.Popen(
            [playit_path],
            cwd=DATA_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
      else:
        subprocess.Popen(
            [playit_path],
            cwd=DATA_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
      print(f"{R}[PLAYIT ERROR] Could not launch playit: {e}{END}")

def download_cloudflared():
  """Detects OS and downloads the official cloudflared binary automatically."""
  os_type = platform.system().lower()

  if os_type == "windows":
    filename = "cloudflared.exe"
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  elif os_type == "linux":
    filename = "cloudflared"
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
  else:
    print(
        f"{R}[ERROR] Unsupported OS for automated cloudflared setup:"
        f" {platform.system()}{END}"
    )
    return None

  cf_path = os.path.join(DATA_DIR, filename)
  if os.path.exists(cf_path):
    print(f"{G}[CLOUDFLARE] {filename} already exists in server_vault.{END}")
    return cf_path

  print(
      f"\n{Y}[SETUP] Downloading Cloudflare Tunnel Client"
      f" ({platform.system()})...{END}"
  )

  try:

    def _progress(count, block_size, total_size):
      if total_size > 0:
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r{C}--> Downloading cloudflared: {percent}%{END}")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, cf_path, _progress)
    print(f"\n{G}[SUCCESS] Downloaded to: {cf_path}{END}\n")

    if os_type == "linux":
      st = os.stat(cf_path)
      os.chmod(cf_path, st.st_mode | stat.S_IEXEC)

    return cf_path
  except Exception as e:
    print(f"\n{R}[ERROR] Failed to download cloudflared: {e}{END}")
    return None


def start_cloudflare_process():
  """Spawns Cloudflare Tunnel if a token is present in environment."""
  token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
  if not token:
    return

  os_type = platform.system().lower()
  filename = "cloudflared.exe" if os_type == "windows" else "cloudflared"
  cf_path = os.path.abspath(os.path.join(DATA_DIR, filename))

  if os.path.exists(cf_path):
    try:
      print(f"{G}[CLOUDFLARE] Launching Cloudflare Web Tunnel...{END}")
      cmd = [cf_path, "tunnel", "run", "--token", token]
      if os_type == "windows":
        subprocess.Popen(
            cmd, cwd=DATA_DIR, creationflags=subprocess.CREATE_NEW_CONSOLE
        )
      else:
        subprocess.Popen(
            cmd,
            cwd=DATA_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
      print(f"{R}[CLOUDFLARE ERROR] Could not launch tunnel: {e}{END}")

def run_desktop_wizard(data_dir):
    root = tk.Tk()
    root.title("Bedrock Node Hub - Setup Wizard")
    root.geometry("620x560")
    root.configure(bg="#000c00")

    bg_color = "#000c00"
    fg_color = "#00ff66"
    accent_color = "#00ffcc"
    entry_bg = "#000000"

    state = {
        "game_choice": tk.StringVar(value="1"),
        "web_choice": tk.StringVar(value="1"),
        "cf_token": tk.StringVar(value=""),
        "admins": {}, 
        "ban_code": tk.StringVar(value="BAN123"),
        "bot_token": tk.StringVar(value=""),
        "webhook_url": tk.StringVar(value=""),
        "vc_status": tk.StringVar(value="0"),
        "vc_players": tk.StringVar(value="0")
    }

    current_step = tk.IntVar(value=1)

    container = tk.Frame(root, bg=bg_color)
    container.pack(fill="both", expand=True, padx=30, pady=(20, 0))

    btn_frame = tk.Frame(root, bg=bg_color)
    btn_frame.pack(fill="x", padx=30, pady=20)

    back_btn = tk.Button(btn_frame, text="< BACK", bg="#333333", fg="#ffffff", font=("Courier", 9, "bold"), width=10)
    next_btn = tk.Button(btn_frame, text="NEXT >", bg=fg_color, fg="#000000", font=("Courier", 9, "bold"), width=18)
    next_btn.pack(side="right")

    def next_action():
        step = current_step.get()
        
        if step < 6:
            current_step.set(step + 1)
            render_step()
        else:
            
            os.makedirs(data_dir, exist_ok=True)
            
            
            try:
                vault_shortcut = os.path.join(data_dir, "Bedrock Node Hub.url")
                with open(vault_shortcut, "w", encoding="utf-8") as sf:
                    sf.write("[InternetShortcut]\nURL=http://localhost:5000\n")

                user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
                desktop = os.path.join(user_profile, "Desktop")
                if not os.path.exists(desktop):
                    onedrive_path = os.environ.get("OneDrive")
                    if onedrive_path and os.path.exists(os.path.join(onedrive_path, "Desktop")):
                        desktop = os.path.join(onedrive_path, "Desktop")
                
                desktop_shortcut = os.path.join(desktop, "Bedrock Node Hub.url")
                with open(desktop_shortcut, "w", encoding="utf-8") as sf:
                    sf.write("[InternetShortcut]\nURL=http://localhost:5000\n")
            except Exception:
                pass
            
            if not state["admins"]:
                state["admins"]["owner"] = generate_password_hash("password123")

            with open(os.path.join(data_dir, "secureaccounts.json"), "w", encoding="utf-8") as f:
                json.dump(state["admins"], f, indent=4)

            use_playit = True if state["game_choice"].get() == "2" or state["web_choice"].get() == "2" else False

            flask_secret = secrets.token_hex(32)
            env_content = (
                "# --- BEDROCK NODE CONFIGURATION ---\n"
                f"USE_PLAYIT={'True' if use_playit else 'False'}\n"
                f"CLOUDFLARE_TUNNEL_TOKEN={state['cf_token'].get().strip()}\n\n"
                f"DISCORD_BOT_TOKEN={state['bot_token'].get().strip()}\n"
                f"ADMIN_WEBHOOK_URL={state['webhook_url'].get().strip()}\n"
                f"VC_STATUS_ID={state['vc_status'].get().strip() or '0'}\n"
                f"VC_PLAYERS_ID={state['vc_players'].get().strip() or '0'}\n\n"
                f"FLASK_PORT=5000\n"
                f"FLASK_SECRET_KEY={flask_secret}\n"
                f"BAN_SECRET_CODE={state['ban_code'].get().strip() or 'BAN123'}\n"
                f"SETTINGS_PASSWORD={state['settings_pw'].get().strip() or 'admin123'}\n"
            )

            with open(os.path.join(data_dir, "securekeys.env"), "w", encoding="utf-8") as f:
                f.write(env_content)

            root.destroy()
            open_as_app("http://localhost:5000")
    def prev_action():
        step = current_step.get()
        if step > 1:
            current_step.set(step - 1)
            render_step()

    back_btn.config(command=prev_action)
    next_btn.config(command=next_action)

    def render_step():
        for widget in container.winfo_children():
            widget.destroy()

        step = current_step.get()

        if step > 1:
            back_btn.pack(side="left")
        else:
            back_btn.pack_forget()

        next_btn.config(text="SAVE & LAUNCH NODE" if step == 6 else "NEXT >", command=next_action)

        if step == 1:
            tk.Label(container, text="[Step 1 of 6] Welcome to Bedrock Node Hub!", fg=accent_color, bg=bg_color, font=("Courier", 11, "bold")).pack(anchor="w", pady=(0, 5))
            
            welcome_text = (
                "Hello! This wizard will quickly configure your Minecraft Bedrock\n"
                "server management dashboard.\n\n"
                "📌 JUST HERE FOR AUTOMATED BACKUPS?\n"
                "If you don't need advanced features right now, you can simply\n"
                "click 'NEXT >' all the way through to use safe default settings.\n\n"
                "What you should know:\n"
                "• A 'server_vault' folder will be created inside your 'Bedrock Node'\n"
                "  folder. This is where your configs, metrics, and logs live.\n"
                "• The admin web dashboard will open automatically on launch, but\n"
                "  you can close it anytime if you aren't using it.\n"
                "• A shortcut link to the admin panel will be automatically saved\n"
                "  inside your 'server_vault' folder for easy access later."
            )
            tk.Label(container, text=welcome_text, fg="#aaffaa", bg=bg_color, font=("Courier", 8), justify="left").pack(anchor="w", pady=5)

            contact_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")
            contact_frame.pack(fill="x", pady=(5, 0), padx=2)

            tk.Label(contact_frame, text="Need Help or Want to Connect?", fg=accent_color, bg="#001800", font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
            
            contact_info = (
                "• Developer / Creator: Nutcrustys420\n"
                "• Community Discord: discord.gg/aSVPbEpkuA"
            )
            tk.Label(contact_frame, text=contact_info, fg="#ffcc00", bg="#001800", font=("Courier", 8), justify="left").pack(anchor="w", padx=8, pady=(0, 2))

            def open_wizard_discord():
                webbrowser.open("https://discord.gg/aSVPbEpkuA")

            tk.Button(contact_frame, text="[ Join Support Discord ]", command=open_wizard_discord, bg="#003322", fg=accent_color, font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=4)

        elif step == 2:
            tk.Label(container, text="[Step 2 of 6] How will players join your server?", fg=accent_color, bg=bg_color, font=("Courier", 11, "bold")).pack(anchor="w", pady=(0, 5))
            
            intro_text = """Choose Option 1 for local play/standard port forwarding,
            or Option 2 if you can't port forward."""
            tk.Label(container, text=intro_text, fg="#88cc88", bg=bg_color, font=("Courier", 8), justify="left").pack(anchor="w", pady=(0, 5))

            direct_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")
            playit_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")

            def toggle_connection_boxes():
                choice = state["game_choice"].get()
                if choice == "1":
                    playit_frame.pack_forget()
                    direct_frame.pack(fill="x", pady=5, padx=2)
                elif choice == "2":
                    direct_frame.pack_forget()
                    playit_frame.pack(fill="x", pady=5, padx=2)

            tk.Radiobutton(container, text="1. Direct Connection (LAN / Port Forwarding)", variable=state["game_choice"], value="1", command=toggle_connection_boxes, fg=fg_color, bg=bg_color, selectcolor=entry_bg, activebackground=bg_color, activeforeground=fg_color, font=("Courier", 9)).pack(anchor="w", pady=1)
            tk.Radiobutton(container, text="2. Playit.gg Tunnel (Starlink / Cellular / No Port Forwarding)", variable=state["game_choice"], value="2", command=toggle_connection_boxes, fg=fg_color, bg=bg_color, selectcolor=entry_bg, activebackground=bg_color, activeforeground=fg_color, font=("Courier", 9)).pack(anchor="w", pady=1)

            tk.Label(direct_frame, text="Direct Connection Guide:", fg=accent_color, bg="#001800", font=("Courier", 9, "bold")).pack(anchor="w", padx=5, pady=2)
            
            direct_guide = (
                "• Local LAN / Testing Only:\n"
                "  No additional setup needed! Players on your local Wi-Fi/network\n"
                "  can join using your internal IP (e.g., 192.168.x.x) on port 19132.\n\n"
                "• Internet Access (Port Forwarding):\n"
                "  To let players join from outside your home:\n"
                "  1. Open your router's web admin page (usually 192.168.1.1 or 192.168.0.1).\n"
                "  2. Locate the 'Port Forwarding' or 'Virtual Server' section.\n"
                "  3. Forward port 19132 to this computer's local IPv4 address.\n\n"
                "  ⚠️ Important Bedrock Details:\n"
                "  • Protocol: Make sure to select UDP (or Both/TCP+UDP if UDP isn't standalone).\n"
                "    Do not choose TCP only.\n"
                "  • Port Number: Use 19132 (ignore Java guides telling you to use 25565)."
            )
            tk.Label(direct_frame, text=direct_guide, fg="#aaffaa", bg="#001800", font=("Courier", 8), justify="left").pack(anchor="w", padx=5, pady=2)

            def open_video_guide():
                webbrowser.open("https://youtu.be/jxskGok7Z-E?si=TsY4vI-JRWZXiH1j")

            tk.Button(direct_frame, text="[ Watch Port Forwarding Video ]", command=open_video_guide, bg="#003322", fg=accent_color, font=("Courier", 8, "bold")).pack(anchor="w", padx=5, pady=4)

            tk.Label(playit_frame, text="Playit.gg Setup Instructions:", fg=accent_color, bg="#001800", font=("Courier", 9, "bold")).pack(anchor="w", padx=5, pady=2)
            
            playit_guide = (
                "  1. Download & install the Playit desktop app.\n"
                "  2. Open Playit and click the claim link to link your account.\n"
                "  3. Create a Bedrock tunnel (UDP port 19132) to get your shareable IP.\n"
                "  - On your Playit dashboard, go to Tunnels and click Add Tunnel.\n"
                "  - Set the Tunnel Type to Minecraft Bedrock (UDP).\n"
                "  - Point to your local server IP (usually 127.0.0.1) and local port 19132.\n"
                "  4. Copy Your Address: Once created, Playit will give you a public address\n"
                "  (e.g. something.ply.gg:12345). Give this shareable IP to your players\n"
                "  so they can connect!"
            )
            tk.Label(playit_frame, text=playit_guide, fg="#aaffaa", bg="#001800", font=("Courier", 8), justify="left").pack(anchor="w", padx=15, pady=2)

            def open_playit_site():
                webbrowser.open("https://playit.gg/download")

            tk.Button(playit_frame, text="[ Open Playit Download Page ]", command=open_playit_site, bg="#003322", fg=accent_color, font=("Courier", 8, "bold")).pack(anchor="w", padx=5, pady=4)

            toggle_connection_boxes()

        elif step == 3:
            tk.Label(container, text="[Step 3 of 6] Admin Web Dashboard & Access", fg=accent_color, bg=bg_color, font=("Courier", 10, "bold")).pack(anchor="w", pady=(0, 4))

            intro_web = (
                "How this works:\n"
                "• A Bedrock server console window will run your live server.\n"
                "• A Web Dashboard window will open automatically for all controls.\n"
                "  You can close it anytime; use it to manage the server remotely.\n"
                "• 📌 Quick-access shortcuts to the web panel will be automatically\n"
                "  saved inside your 'server_vault' folder and your Desktop!"
            )
            tk.Label(container, text=intro_web, fg="#88cc88", bg=bg_color, font=("Courier", 8), justify="left").pack(anchor="w", pady=(0, 4))

            local_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")
            playit_web_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")
            cf_frame = tk.Frame(container, bg="#001800", bd=1, relief="solid")

            def toggle_web_boxes():
                choice = state["web_choice"].get()
                local_frame.pack_forget()
                playit_web_frame.pack_forget()
                cf_frame.pack_forget()
                
                if choice == "1":
                    local_frame.pack(fill="x", pady=4, padx=2)
                elif choice == "2":
                    playit_web_frame.pack(fill="x", pady=4, padx=2)
                elif choice == "3":
                    cf_frame.pack(fill="x", pady=4, padx=2)

            tk.Radiobutton(container, text="1. Local Access Only (http://localhost:5000)", variable=state["web_choice"], value="1", command=toggle_web_boxes, fg=fg_color, bg=bg_color, selectcolor=entry_bg, activebackground=bg_color, activeforeground=fg_color, font=("Courier", 8)).pack(anchor="w", pady=1)
            tk.Radiobutton(container, text="2. Remote Access via Playit.gg Tunnel", variable=state["web_choice"], value="2", command=toggle_web_boxes, fg=fg_color, bg=bg_color, selectcolor=entry_bg, activebackground=bg_color, activeforeground=fg_color, font=("Courier", 8)).pack(anchor="w", pady=1)
            tk.Radiobutton(container, text="3. Secure Remote Access via Cloudflare Tunnel", variable=state["web_choice"], value="3", command=toggle_web_boxes, fg=fg_color, bg=bg_color, selectcolor=entry_bg, activebackground=bg_color, activeforeground=fg_color, font=("Courier", 8)).pack(anchor="w", pady=1)

            tk.Label(local_frame, text="Local Access Guide:", fg=accent_color, bg="#001800", font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=2)
            local_guide = (
                "• Manage from this computer or home Wi-Fi.\n"
                "• Use the desktop shortcut button above anytime."
            )
            tk.Label(local_frame, text=local_guide, fg="#aaffaa", bg="#001800", font=("Courier", 8), justify="left").pack(anchor="w", padx=8, pady=2)

            tk.Label(playit_web_frame, text="Playit.gg Remote Dashboard Guide:", fg=accent_color, bg="#001800", font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=2)
            playit_web_guide = (
                "• Free Tier (TCP Tunnel):\n"
                "  1. Go to your Playit dashboard and click 'Add Tunnel'.\n"
                "  2. Set Tunnel Type to TCP, point it to Local IP 127.0.0.1\n"
                "     and Local Port 5000.\n"
                "  3. You will get an address like: curlypig.ply.gg:23559.\n"
                "  Type that full address into your browser to log in remotely!\n"
                "• Premium / Domain: Set up a standard HTTP/HTTPS tunnel\n"
                "  for a clean URL without port numbers."
            )
            tk.Label(playit_web_frame, text=playit_web_guide, fg="#aaffaa", bg="#001800", font=("Courier", 7), justify="left").pack(anchor="w", padx=8, pady=2)

            def open_playit_dashboard():
                webbrowser.open("https://playit.gg/account/tunnels")

            tk.Button(playit_web_frame, text="[ Open Playit Tunnels Dashboard ]", command=open_playit_dashboard, bg="#003322", fg=accent_color, font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=4)

            tk.Label(cf_frame, text="Cloudflare Tunnel Setup:", fg=accent_color, bg="#001800", font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=2)
            cf_guide = (
                "• Requires your own custom domain (e.g., yourdomain.com).\n"
                "1. Go to: https://one.dash.cloudflare.com (Zero Trust Dashboard).\n"
                "2. Go to Networks -> Tunnels -> Click 'Create a tunnel'.\n"
                "3. Choose Cloudflared, name it, and copy your Tunnel Token below.\n"
                "4. Set Public Hostname to your domain and point it to HTTP localhost:5000.\n"
                "5. (Optional Security): Go to Access -> Applications to lock down\n"
                "   your panel behind a secure email login screen!"
            )
            tk.Label(cf_frame, text=cf_guide, fg="#aaffaa", bg="#001800", font=("Courier", 7), justify="left").pack(anchor="w", padx=8, pady=2)

            btn_row = tk.Frame(cf_frame, bg="#001800")
            btn_row.pack(fill="x", padx=8, pady=3)

            tk.Button(btn_row, text="[ Open CF Dashboard ]", command=lambda: webbrowser.open("https://one.dash.cloudflare.com"), bg="#003322", fg=accent_color, font=("Courier", 8, "bold")).pack(side="left", padx=(0, 5))
            
            def fetch_cf_now():
                msg = download_cloudflared()
                if msg:
                    messagebox.showinfo("Success", "Cloudflare client downloaded!")
                else:
                    messagebox.showerror("Error", "Download failed.")

            tk.Button(btn_row, text="[ Download Cloudflare Tunnel ]", command=fetch_cf_now, bg="#003311", fg=fg_color, font=("Courier", 8, "bold")).pack(side="left")

            tk.Label(cf_frame, text="Paste Tunnel Token Here:", fg=fg_color, bg="#001800", font=("Courier", 8)).pack(anchor="w", padx=8, pady=(4, 0))
            tk.Entry(cf_frame, textvariable=state["cf_token"], bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=("Courier", 8, "bold")).pack(anchor="w", padx=8, pady=4)

            toggle_web_boxes()

        elif step == 4:
            tk.Label(container, text="[Step 4 of 6] Admin Login & Security", fg=accent_color, bg=bg_color, font=("Courier", 11, "bold")).pack(anchor="w", pady=(0, 5))
            tk.Label(container, text="Create your Web Dashboard login credentials:", fg="#88cc88", bg=bg_color, font=("Courier", 9)).pack(anchor="w", pady=(0, 5))

            form_frame = tk.Frame(container, bg=bg_color)
            form_frame.pack(fill="x", pady=5)

            tk.Label(form_frame, text="Admin User:", fg=fg_color, bg=bg_color, font=("Courier", 9)).grid(row=0, column=0, sticky="w", pady=2)
            u_entry = tk.Entry(form_frame, bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=("Courier", 10), width=25)
            u_entry.grid(row=0, column=1, padx=10, pady=2)
            u_entry.insert(0, "owner")

            tk.Label(form_frame, text="Password:", fg=fg_color, bg=bg_color, font=("Courier", 9)).grid(row=1, column=0, sticky="w", pady=2)
            p_entry = tk.Entry(form_frame, bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=("Courier", 10), width=25)
            p_entry.grid(row=1, column=1, padx=10, pady=2)
            p_entry.insert(0, "password123")

            added_label = tk.Label(container, text=f"Admins Configured: {max(1, len(state['admins']))}", fg=accent_color, bg=bg_color, font=("Courier", 9, "bold"))
            added_label.pack(anchor="w", pady=5)

            def add_admin():
                u = u_entry.get().strip().lower()
                p = p_entry.get().strip()
                if not u or not p:
                    messagebox.showerror("Error", "Username and password cannot be blank!")
                    return
                state["admins"][u] = generate_password_hash(p)
                added_label.config(text=f"Admins Configured: {len(state['admins'])}")
                u_entry.delete(0, tk.END)
                p_entry.delete(0, tk.END)
                messagebox.showinfo("Success", f"Added admin '{u}'! You can add another or click Next.")

            tk.Button(container, text="+ ADD EXTRA ADMIN ACCOUNT", command=add_admin, bg="#004422", fg=fg_color, font=("Courier", 8, "bold")).pack(anchor="w", pady=2)

            tk.Label(container, text="Ban Security Password (Ban Matrix):", fg=fg_color, bg=bg_color, font=("Courier", 9)).pack(anchor="w", pady=(10, 0))
            tk.Label(container, text="(Safety pin required when banning players from the web panel)", fg="#88cc88", bg=bg_color, font=("Courier", 8)).pack(anchor="w")
            tk.Entry(container, textvariable=state["ban_code"], bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=("Courier", 10), width=25).pack(anchor="w", pady=2)

            state["settings_pw"] = tk.StringVar(value="admin123")
            tk.Label(container, text="Server Settings Password:", fg=fg_color, bg=bg_color, font=("Courier", 9)).pack(anchor="w", pady=(10, 0))
            tk.Label(container, text="(Required to unlock and modify Server Settings)", fg="#88cc88", bg=bg_color, font=("Courier", 8)).pack(anchor="w")
            tk.Entry(container, textvariable=state["settings_pw"], bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=("Courier", 10), width=25).pack(anchor="w", pady=2)

            def save_and_proceed():
                u = u_entry.get().strip().lower()
                p = p_entry.get().strip()
                if u and p and u not in state["admins"]:
                    state["admins"][u] = generate_password_hash(p)
                next_action()

            next_btn.config(command=save_and_proceed)

        elif step == 5:
            tk.Label(container, text="[Step 5 of 6] Discord Notifications (Optional)", fg=accent_color, bg=bg_color, font=("Courier", 10, "bold")).pack(anchor="w", pady=(0, 2))

            guide_text = (
                "PART 1: Text Alerts (Webhook URL)\n"
                "• Posts join/leave, unique player, and ban alerts.\n"
                "1. Go to Server Settings -> Integrations -> Webhooks -> New Webhook.\n"
                "2. Name it 'Server Alerts', pick a channel (#server-alerts), copy URL.\n\n"
                "PART 2: Live Status Voice Channels (Bot Token & IDs)\n"
                "• Automatically updates voice channel names with stats.\n"
                "1. Go to Discord Developer Portal -> Create App -> Bot -> Reset Token.\n"
                "2. Enable 'Server Members' & 'Message Content' Intents.\n"
                "3. Turn on User Settings -> Advanced -> Developer Mode.\n"
                "4. Create two voice channels: 'Status' and 'Players'.\n"
                "5. Right-click each, copy Channel ID, and paste below."
            )
            tk.Label(container, text=guide_text, fg="#aaffaa", bg=bg_color, font=("Courier", 8), justify="left").pack(anchor="w", pady=(0, 4))

            tk.Button(container, text="[ Open Discord Developer Portal ]", command=lambda: webbrowser.open("https://discord.com/developers/applications"), bg="#002244", fg=accent_color, font=("Courier", 8, "bold")).pack(anchor="w", pady=(0, 4))

            f_disc = tk.Frame(container, bg=bg_color)
            f_disc.pack(fill="x")

            tk.Label(f_disc, text="Webhook URL:", fg=fg_color, bg=bg_color, font=("Courier", 8)).grid(row=0, column=0, sticky="w", pady=1)
            tk.Entry(f_disc, textvariable=state["webhook_url"], bg=entry_bg, fg=fg_color, font=("Courier", 8), width=35).grid(row=0, column=1, padx=5, pady=1)

            tk.Label(f_disc, text="Bot Token:", fg=fg_color, bg=bg_color, font=("Courier", 8)).grid(row=1, column=0, sticky="w", pady=1)
            tk.Entry(f_disc, textvariable=state["bot_token"], bg=entry_bg, fg=fg_color, font=("Courier", 8), width=35).grid(row=1, column=1, padx=5, pady=1)

            tk.Label(f_disc, text="Status Voice ID:", fg=fg_color, bg=bg_color, font=("Courier", 8)).grid(row=2, column=0, sticky="w", pady=1)
            tk.Entry(f_disc, textvariable=state["vc_status"], bg=entry_bg, fg=fg_color, font=("Courier", 8), width=20).grid(row=2, column=1, sticky="w", padx=5, pady=1)

            tk.Label(f_disc, text="Players Voice ID:", fg=fg_color, bg=bg_color, font=("Courier", 8)).grid(row=3, column=0, sticky="w", pady=1)
            tk.Entry(f_disc, textvariable=state["vc_players"], bg=entry_bg, fg=fg_color, font=("Courier", 8), width=20).grid(row=3, column=1, sticky="w", padx=5, pady=1)

        elif step == 6:
            tk.Label(container, text="[Step 6 of 6] Ready to Launch!", fg=accent_color, bg=bg_color, font=("Courier", 12, "bold")).pack(anchor="w", pady=(0, 10))
            
            summary = (
                f"Your server is ready to start:\n\n"
                f"• Player Access: {'Playit.gg Tunnel' if state['game_choice'].get() == '2' else 'Direct Connection'}\n"
                f"• Web Dashboard: Option {state['web_choice'].get()}\n"
                f"• Admin Accounts: {max(1, len(state['admins']))} account(s)\n"
                f"• Discord Bot: {'Configured' if state['bot_token'].get() else 'Skipped'}\n\n"
                f"Click 'SAVE & LAUNCH NODE' below. Your browser will open automatically!"
            )
            tk.Label(container, text=summary, fg=fg_color, bg=bg_color, font=("Courier", 9), justify="left").pack(anchor="w", pady=10)

    render_step()
    root.mainloop()

def get_notes():
  with notes_lock:
    try:
      with open(NOTES_FILE, "r", encoding="utf-8") as f:
        return f.read()
    except Exception:
      return "No notes yet..."


def load_blacklist():
  """Loads blacklisted players safely using a thread lock."""
  with blacklist_lock:
    if not os.path.exists(BLACKLIST_FILE):
      return {}
    try:
      with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"Error loading blacklist: {e}")
      return {}


def save_blacklist(blacklist_dict):
  """Saves blacklisted players safely using a thread lock."""
  with blacklist_lock:
    try:
      with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist_dict, f, indent=4)
    except Exception as e:
      print(f"Error saving blacklist: {e}")


def send_admin_alert(message):
  """Pushes logs to the Admin Discord text channel if enabled."""
  if not WEBHOOK_ENABLED or not ADMIN_WEBHOOK_URL:
    return 

  try:
    payload = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        ADMIN_WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BedrockNodeHub",
        },
    )
    urllib.request.urlopen(req, timeout=5)
  except Exception as e:
    print(f"Admin Webhook Error: {e}")


@discord_client.event
async def on_ready():
  print(f"Discord Stats Bot logged in as {discord_client.user}")
  await asyncio.sleep(15)
  update_discord_stats.start()


last_sent_status = None
last_sent_players = None


@tasks.loop(minutes=5)
async def update_discord_stats():
  if not DISCORD_ENABLED:
    return
  global last_sent_status, last_sent_players, ONLINE_PLAYERS
  try:
    with state_lock:
      p_count = len(ONLINE_PLAYERS) if is_running else 0

    players_text = f"{p_count} / 30" if is_running else "0 / 30"
    status_name = "🟢 Status: Online" if is_running else "🔴 Status: Offline"
    players_name = f"👥 Players: {players_text}"

    if VC_STATUS_ID and status_name != last_sent_status:
      ch = discord_client.get_channel(VC_STATUS_ID)
      if ch:
        await ch.edit(name=status_name)
        last_sent_status = status_name
        await asyncio.sleep(6)

    if VC_PLAYERS_ID and players_name != last_sent_players:
      ch = discord_client.get_channel(VC_PLAYERS_ID)
      if ch:
        await ch.edit(name=players_name)
        last_sent_players = players_name
        await asyncio.sleep(6)

  except discord.HTTPException as e:
    if e.status == 429:
      print("Discord Rate Limit hit! Backing off for this cycle.")
    else:
      print(f"Discord HTTP Error: {e}")
  except Exception as e:
    print(f"Discord Stat Update Error: {e}")


def run_discord_bot():
  """Runs the Discord stats bot if a valid token is provided."""
  if not DISCORD_ENABLED or not DISCORD_BOT_TOKEN:
    print(f"{C}[INFO] Discord Bot disabled (no DISCORD_BOT_TOKEN set).{END}")
    return

  try:
    discord_client.run(DISCORD_BOT_TOKEN)
  except Exception as e:
    print(f"[ERROR] Discord Bot failed to start: {e}")


def restart_timer():
  """Restarts the server at fixed intervals: 2:00 AM, 2:00 PM, and 8:00 PM."""
  global restart_timer_start
  last_restart_key = None

  while True:
    now = datetime.now()
    target_hours = [2, 14, 20]

    if now.hour in target_hours and now.minute == 0:
      restart_key = (now.date(), now.hour)
      if last_restart_key != restart_key:
        last_restart_key = restart_key

        send_to_mc(
            "say Server restarting in 1 minute find a safe spot", "SYSTEM"
        )
        time.sleep(60)
        send_to_mc("stop", "AUTORESTART")

        restart_timer_start = datetime.now()
        time.sleep(65)
    else:
      if last_restart_key is not None and now.minute != 0:
        last_restart_key = None

    time.sleep(15)


def hourly_metrics_logger():
  """Creates a monthly archive folder, logs player counts, and aligns logging to top-of-the-hour marks."""
  archive_dir = os.path.join(DATA_DIR, "metrics_archive")

  while True:
    try:
      if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

      current_month_str = datetime.now().strftime("%Y-%m")
      log_file_path = os.path.join(
          archive_dir, f"metrics_{current_month_str}.csv"
      )

      needs_header = (
          not os.path.exists(log_file_path)
          or os.path.getsize(log_file_path) == 0
      )

      p_count = len(ONLINE_PLAYERS) if is_running else 0
      timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

      with open(log_file_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if needs_header:
          writer.writerow(["Timestamp", "Player_Count"])
        writer.writerow([timestamp, p_count])

    except Exception as e:
      print(f"Hourly metrics log error: {e}")

    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(
        minute=0, second=0, microsecond=0
    )
    sleep_seconds = (next_hour - now).total_seconds()
    time.sleep(sleep_seconds)


def load_accounts():
  """Loads admin credentials from secureaccounts.json."""
  if os.path.exists(ACCOUNTS_FILE):
    try:
      with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"Error loading accounts: {e}")
      return {}
  else:
    return {}


ACCOUNTS = load_accounts()


def log_admin_event(event_type, username, ip_address="Local"):
  """Logs admin logins/logouts to a .txt file and prints directly to console."""
  try:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"[{timestamp}] ADMIN {event_type} | User: {username} | IP:"
        f" {ip_address}\n"
    )

    with open(ADMIN_LOG_FILE, "a", encoding="utf-8") as f:
      f.write(log_entry)

    print(
        f"{C}[ADMIN HUB] {timestamp} -> User '{username}'"
        f" {event_type.lower()} (IP: {ip_address}){END}"
    )
  except Exception as e:
    print(f"Admin log error: {e}")


def track_unique_player(player_name, xuid):
  """Tracks unique players by their permanent XUID."""
  with unique_players_lock:
    try:
      if os.path.exists(UNIQUE_PLAYERS_FILE):
        with open(UNIQUE_PLAYERS_FILE, "r", encoding="utf-8") as f:
          unique_dict = json.load(f)
      else:
        unique_dict = {}

      key = xuid if xuid and xuid != "Unknown" else player_name

      if key not in unique_dict:
        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unique_dict[key] = {
            "current_name": player_name,
            "xuid": xuid,
            "first_joined": join_time,
        }
        with open(UNIQUE_PLAYERS_FILE, "w", encoding="utf-8") as f:
          json.dump(unique_dict, f, indent=4)

        send_admin_alert(
            f"🎉 **NEW UNIQUE PLAYER:** `{player_name}` joined for the very"
            f" first time! (Total unique players: {len(unique_dict)})"
        )
      else:
        if unique_dict[key].get("current_name") != player_name:
          unique_dict[key]["current_name"] = player_name
          with open(UNIQUE_PLAYERS_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_dict, f, indent=4)
    except Exception as e:
      print(f"Unique player tracking error: {e}")


def load_unique_player_dates():
  """Loads all first-join timestamps from unique players storage."""
  unique_dates = []
  with unique_players_lock:
    if os.path.exists(UNIQUE_PLAYERS_FILE):
      try:
        with open(UNIQUE_PLAYERS_FILE, "r", encoding="utf-8") as f:
          data = json.load(f)
          for key, info in data.items():
            first_joined = info.get("first_joined") or info.get("timestamp")
            if first_joined:
              try:
                dt_obj = datetime.strptime(first_joined, "%Y-%m-%d %H:%M:%S")
                unique_dates.append(dt_obj)
              except ValueError:
                pass
      except Exception as e:
        print(f"Error loading unique players for graph: {e}")
  return unique_dates


def backup_world():
  backup_dir = os.path.join(DATA_DIR, "daily_backup")
  if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

  timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  world_path = os.path.join(SERVER_DIR, "worlds")

  if os.path.exists(world_path):
    try:
      print(
          f"[{datetime.now().strftime('%H:%M:%S')}] Starting fast raw copy of"
          " worlds folder to backups... Please wait."
      )
      dest_folder = os.path.join(backup_dir, f"world_backup_{timestamp}")
      shutil.copytree(world_path, dest_folder)
      print(
          ">> World backup copy completed successfully:"
          f" world_backup_{timestamp}"
      )
      cleanup_old_backups(backup_dir, days_to_keep=3)
    except Exception as e:
      print(f">> Backup failed: {e}")
  else:
    print(f">> Backup failed: 'worlds' folder not found at {world_path}")


def cleanup_old_backups(backup_dir, days_to_keep=3):
  try:
    now = time.time()
    cutoff_seconds = days_to_keep * 86400

    for folder_name in os.listdir(backup_dir):
      folder_path = os.path.join(backup_dir, folder_name)
      if os.path.isdir(folder_path) and folder_name.startswith("world_backup_"):
        folder_mtime = os.path.getmtime(folder_path)
        if (now - folder_mtime) > cutoff_seconds:
          shutil.rmtree(folder_path)
          print(
              f">> Purged old backup: {folder_name} (older than"
              f" {days_to_keep} days)"
          )
  except Exception as e:
    print(f">> Error cleaning up old backups: {e}")


def nightly_backup_scheduler():
  global needs_backup, last_backup_date, mc_process, is_backing_up
  while True:
    now = datetime.now()
    if now.hour == 8 and now.minute == 0:
      today = now.date()
      if last_backup_date != today:
        last_backup_date = today
        is_backing_up = True

        print("Initiating scheduled backup sequence...")
        send_to_mc(
            "say Server backing up in 5 minutes for daily maintenance.",
            "SYSTEM",
        )
        time.sleep(270)
        send_to_mc(
            "say Server backing up in 30 seconds! Find a safe spot...",
            "SYSTEM",
        )
        time.sleep(30)
        send_to_mc("stop", "SYSTEM")

        if mc_process:
          mc_process.wait()

        time.sleep(5)
        backup_world()
        is_backing_up = False
    time.sleep(30)


def send_to_mc(cmd, source="SYSTEM", silent=False):
  global mc_process, last_actions
  t_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  t = datetime.now().strftime("%H:%M")

  if mc_process and mc_process.poll() is None:
    try:
      mc_process.stdin.write(cmd + "\n")
      mc_process.stdin.flush()

      if not silent:
        entry = f"{source}: {cmd}"
        try:
          if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
          log_file = os.path.join(
              LOG_DIR, f"commands_{datetime.now().strftime('%Y-%m-%d')}.txt"
          )
          with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{t_full}] {entry}\n")
        except Exception as e:
          print(f"Log Error: {e}")

        with state_lock:
          last_actions.append(
              f'<span style="color: #d8bfd8;">[{t}] {entry}</span>'
          )
          last_actions = last_actions[-500:]

        if source != "CONSOLE":
          print(f" {PURPLE}>>{END} {W}{source}{END}: {PURPLE}{cmd}{END}")
      return True
    except Exception as e:
      print(f"Pipe Error: {e}")
      return False
  return False


def stdout_reader():
  global mc_process, ONLINE_PLAYERS, last_actions
  while mc_process and mc_process.poll() is None:
    raw_line = mc_process.stdout.readline()
    if not raw_line:
      break
    raw_msg = raw_line.strip()
    clean = re.sub(r"^\x1b\[[0-9;]*m", "", raw_msg)

    skip_web_keywords = [
        "Session ID:",
        "Build ID:",
        "Branch:",
        "Commit ID:",
        "Configuration:",
        "Level Name:",
        "Profiler config",
        "No CDN config file",
        "Content logging to console",
        "Opening level",
        "Accepting clients",
        "Pack Stack",
        "Signed in to signaling",
        "Server started.",
        "Allow list is enabled",
        "Server Telemetry",
    ]
    should_skip_web = any(
        keyword.lower() in clean.lower() for keyword in skip_web_keywords
    )

    is_banned_player = False
    ban_kick_name = "Player"
    player_joined_name = None

    with state_lock:
      is_join_event = any(
          term in clean.lower()
          for term in
          ["player connected", "player spawned", "connected to server"]
      )
      is_leave_event = any(
          term in clean.lower()
          for term in ["player disconnected", "left the game"]
      )
      player_left_name = None

      if is_leave_event:
        try:
          m_leave = re.search(
              r"player (?:disconnected)[:\s]+([^,]+)", clean, re.IGNORECASE
          )
          if m_leave:
            p_name = m_leave.group(1).strip()
          else:
            parts = clean.split()
            p_name = None
            for i, part in enumerate(parts):
              if "left" in part.lower() and i > 0:
                p_name = parts[i - 1].strip()
                break

          if p_name and p_name in ONLINE_PLAYERS:
            ONLINE_PLAYERS.remove(p_name)
            player_left_name = p_name
            print(f"{Y}{clean}{END}")
        except Exception as e:
          print(f"Player leave parse error: {e}")

      elif is_join_event:
        try:
          p_name = "Unknown"
          p_xuid = "Unknown"

          m_conn = re.search(
              r"player (?:connected|spawned|connect)[:\s]+([^,]+)(?:,\s*|\s+)xuid[:\s]*(\d+)",
              clean,
              re.IGNORECASE,
          )
          if m_conn:
            p_name = m_conn.group(1).strip()
            p_xuid = m_conn.group(2).strip()
          else:
            m_xuid = re.search(r"xuid[:\s]*(\d+)", clean, re.IGNORECASE)
            if m_xuid:
              p_xuid = m_xuid.group(1).strip()

            parts = clean.split()
            for i, part in enumerate(parts):
              if "joined" in part.lower() and i > 0:
                p_name = parts[i - 1].strip()
                break

          if p_name.lower() == "player" or not p_name:
            p_name = "Unknown"

          blacklist = load_blacklist()
          is_banned = False

          if p_xuid in blacklist:
            is_banned = True
          else:
            for b_xuid, info in blacklist.items():
              if info.get("name", "").lower() == p_name.lower():
                is_banned = True
                break

          if is_banned:
            is_banned_player = True
            ban_kick_name = p_name if p_name != "Unknown" else "Player"
          else:
            if p_name != "Unknown":
              if p_name not in ONLINE_PLAYERS:
                ONLINE_PLAYERS.add(p_name)
                track_unique_player(p_name, p_xuid)
                player_joined_name = p_name

            print(f"{G}{clean}{END}")
        except Exception as e:
          print(f"Player parse error: {e}")
      else:
        if "error" in clean.lower() or "exception" in clean.lower():
          print(f"{R}{clean}{END}")
        else:
          print(clean)

    if is_banned_player:
      print(
          f"{R}>> Banned player {ban_kick_name} attempted to connect."
          f" Executing kick...{END}"
      )
      send_to_mc(
          f'kick "{ban_kick_name}" You are permanently banned from The'
          " Server.",
          "BAN_EXEC",
      )
      send_admin_alert(
          f"🚫 **BLOCK:** Banned player `{ban_kick_name}` tried to join and was"
          " automatically kicked."
      )

    if player_joined_name:
      send_admin_alert(f"👤 **PLAYER:** `{player_joined_name}` joined the server.")

    if player_left_name:
      send_admin_alert(f"🪦 **PLAYER:** `{player_left_name}` left the server.")

    if not should_skip_web:
      formatted_line = colorize_log(raw_line)
      with state_lock:
        last_actions.append(formatted_line)
        last_actions = last_actions[-500:]

      socketio.emit("console_log", {"line": formatted_line})


def websocket_stats_broadcaster():
  """Pushes server stats to all connected web clients every few seconds."""
  while True:
    time.sleep(3)
    try:
      uptime = (
          str(datetime.now() - start_time).split(".")[0]
          if start_time
          else "0:00:00"
      )

      now = datetime.now()
      target_hours = [2, 8, 14, 20]
      next_target = None
      for h in target_hours:
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate > now:
          next_target = candidate
          break
      if not next_target:
        next_target = (now + timedelta(days=1)).replace(
            hour=2, minute=0, second=0, microsecond=0
        )

      remaining = next_target - now
      restart_in = str(remaining).split(".")[0]

      with state_lock:
        p_count = len(ONLINE_PLAYERS) if is_running else 0
        players_str = f"{p_count} / 30" if is_running else "OFFLINE"

      disk_usage = shutil.disk_usage(SERVER_DIR)
      free_gb = round(disk_usage.free / (1024**3), 1)

      stats_payload = {
          "cpu": f"{psutil.cpu_percent()}%",
          "ram": f"{psutil.virtual_memory().percent}%",
          "disk": f"{free_gb} GB",
          "uptime": uptime,
          "status": "ONLINE" if is_running else "OFFLINE",
          "restart_in": restart_in,
          "players": players_str,
      }

      socketio.emit("update_stats", stats_payload)
    except Exception:
      pass

def open_as_app(url):
    """Opens the URL as a standalone app window with an isolated profile so Windows maps the taskbar icon correctly."""
    os_type = platform.system().lower()
    opened = False
    
    if os_type == "windows":
        app_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")
        ]
        
        profile_dir = os.path.join(DATA_DIR, "chrome_profile")
        
        for path in app_paths:
            if os.path.exists(path):
                try:
                    subprocess.Popen([
                        path, 
                        f"--app={url}", 
                        f"--user-data-dir={profile_dir}",
                        "--class=BedrockNode"
                    ])
                    opened = True
                    break
                except Exception:
                    pass
                    
    elif os_type == "darwin": 
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_path):
            try:
                subprocess.Popen([chrome_path, f"--app={url}"])
                opened = True
            except Exception:
                pass
    elif os_type == "linux":
        for browser in ["google-chrome", "chromium-browser", "microsoft-edge"]:
            try:
                subprocess.Popen([browser, f"--app={url}"])
                opened = True
                break
            except Exception:
                pass
                
    if not opened:
        webbrowser.open(url)

def local_console_bridge():
  """Reads input typed directly into the local server command prompt."""
  global is_running
  while True:
    if is_running:
      try:
        cmd = input()
        if cmd.strip():
          send_to_mc(cmd.strip(), "CONSOLE")
      except EOFError:
        break
    else:
      time.sleep(1)


def colorize_log(line):
  clean_line = html.escape(line.strip())
  if "Player connected:" in clean_line or "joined the game" in clean_line:
    return f'<span style="color: #55FF55; font-weight: bold;">{clean_line}</span>'
  elif "Player disconnected:" in clean_line or "left the game" in clean_line:
    return f'<span style="color: #FF5555; font-weight: bold;">{clean_line}</span>'
  elif "WARN" in clean_line or "WARNING" in clean_line:
    return f'<span style="color: #FFFF55;">{clean_line}</span>'
  elif "ERROR" in clean_line or "Unknown command" in clean_line:
    return f'<span style="color: #FF5555;">{clean_line}</span>'
  elif "CONSOLE:" in clean_line or "&gt;&gt;" in clean_line:
    return f'<span style="color: #D8BFD8;">{clean_line}</span>'
  elif "INFO" in clean_line:
    return f'<span style="color: #CCCCCC;">{clean_line}</span>'
  else:
    return f'<span style="color: #00FF00;">{clean_line}</span>'


def server_manager():
    global mc_process, is_running, is_restarting, seconds_left, start_time, is_backing_up
    while True:
        with state_lock:
            is_restarting = False

        os.system("cls" if os.name == "nt" else "clear")

        term_width = shutil.get_terminal_size((80, 24)).columns
        print(f"{G}{B}")

        if term_width >= 120:
            print(r" ██████╗   ███████╗  ██████╗   ██████╗   ██████╗    ██████╗   ██╗  ██╗  ███╗   ██╗  ██████╗   ██████╗   ███████╗")
            print(r" ██╔══██╗  ██╔════╝  ██╔══██╗  ██╔══██╗  ██╔═══██╗  ██╔════╝  ██║ ██╔╝  ████╗  ██║  ██╔═══██╗  ██╔══██╗  ██╔════╝")
            print(r" ██████╔╝  █████╗    ██║  ██║  ██████╔╝  ██║   ██║  ██║       █████╔╝   ██╔██╗ ██║  ██║   ██║  ██║  ██║  █████╗  ")
            print(r" ██╔══██╗  ██╔══╝    ██║  ██║  ██╔══██╗  ██║   ██║  ██║       ██╔═██╗   ██║╚██╗██║  ██║   ██║  ██║  ██║  ██╔══╝  ")
            print(r" ██████╔╝  ███████╗  ██████╔╝  ██║  ██║  ╚██████╔╝  ╚██████╗  ██║  ██╗  ██║ ╚████║  ╚██████╔╝  ██████╔╝  ███████╗")
            print(r" ╚═════╝   ╚══════╝  ╚═════╝   ╚═╝  ╚═╝   ╚═════╝    ╚═════╝  ╚═╝  ╚═╝  ╚═╝  ╚═══╝   ╚═════╝   ╚═════╝   ╚══════╝")
        elif term_width >= 75:
            print(r" ██████╗  ███████╗ ██████╗  ██████╗  ██████╗  ██╗  ██╗")
            print(r" ██╔══██╗ ██╔════╝ ██╔══██╗ ██╔══██╗ ██╔═══██╗ ██║ ██╔╝")
            print(r" ██████╔╝ █████╗   ██║  ██║ ██████╔╝ ██║   ██║ █████╔╝ ")
            print(r" ██╔══██╗ ██╔══╝   ██║  ██║ ██╔══██╗ ██║   ██║ ██╔═██╗ ")
            print(r" ██████╔╝ ███████╗ ██████╔╝ ██║  ██║ ╚██████╔╝ ██║  ██╗")
            print(r" ╚═════╝  ╚══════╝ ╚═════╝  ╚═╝  ╚═╝  ╚═════╝  ╚═╝  ╚═╝")
            print(r"          ███╗   ██╗ ██████╗  ██████╗  ███████╗")
            print(r"          ████╗  ██║ ██╔═══██╗██╔══██╗ ██╔════╝")
            print(r"          ██╔██╗ ██║ ██║   ██║██║  ██║ █████╗  ")
            print(r"          ██║╚██╗██║ ██║   ██║██║  ██║ ██╔══╝  ")
            print(r"          ██║ ╚████║ ╚██████╔╝██████╔╝ ███████╗")
            print(r"          ╚═╝  ╚═══╝  ╚═════╝ ╚═════╝  ╚══════╝")
        else:
            print(r" ┌──────────────────────────────────────────┐")
            print(r" │            B E D R O C K                 │")
            print(r" │              N O D E                     │")
            print(r" └──────────────────────────────────────────┘")

        print(f"{END}")

        bar_len = max(40, min(term_width - 2, 105))
        divider = "=" * bar_len
        title = "BEDROCK NODE HUB (v1)"

        print(f"{G}{B}{divider}{END}")
        print(f"{G}{B}{title:^{bar_len}}{END}")
        print(f"{G}{B}{divider}{END}")

        exe_path = os.path.join(SERVER_DIR, SERVER_EXE)

        env_vars = os.environ.copy()
        if not IS_WINDOWS:
          if os.path.exists(exe_path):
            st = os.stat(exe_path)
            os.chmod(exe_path, st.st_mode | 0o111) 
          env_vars["LD_LIBRARY_PATH"] = SERVER_DIR

        creationflags = 0
        startupinfo = None
        if IS_WINDOWS:
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        mc_process = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=SERVER_DIR,
            text=True,
            bufsize=1,
            env=env_vars,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )

        threading.Thread(target=stdout_reader, daemon=True).start()

        time.sleep(8)
        is_running, start_time = True, datetime.now()

        send_admin_alert("🟢 **SERVER STATUS:** Bedrock Node is now **ONLINE**.")

        mc_process.wait()
        if mc_process.stdin:
          mc_process.stdin.close()
        if mc_process.stdout:
          mc_process.stdout.close()

        is_running, is_restarting, start_time = False, True, None
        ONLINE_PLAYERS.clear()

        send_admin_alert("🔴 **SERVER STATUS:** Bedrock Node went **OFFLINE**.")

        if is_backing_up:
            print(
                f"{Y}>>{END} Backup in progress. Holding server offline until"
                " compression completes..."
            )
            while is_backing_up:
                time.sleep(3)

        countdown_time = 15
        for i in range(countdown_time, -1, -1):
            seconds_left = i
            os.system("cls" if os.name == "nt" else "clear")
            print(f"{R}{B}=================================================={END}")
            print(
                f"{R}{B}       REBOOTING IN: {Y}{i}{R} SECONDS                    "
                f"{END}"
            )
            print(f"{R}{B}=================================================={END}")
            time.sleep(1)

        with state_lock:
            is_restarting = False


def load_metrics_data():
  """Loads and parses all monthly CSV logs safely (supporting 2 or 3 columns)."""
  archive_dir = os.path.join(DATA_DIR, "metrics_archive")
  parsed_rows = []

  if not os.path.exists(archive_dir):
    return parsed_rows

  for filename in os.listdir(archive_dir):
    if filename.startswith("metrics_") and filename.endswith(".csv"):
      file_path = os.path.join(archive_dir, filename)
      try:
        with open(file_path, mode="r", encoding="utf-8") as f:
          reader = csv.reader(f)
          header = next(reader, None)
          for row in reader:
            if len(row) >= 2:
              try:
                dt_str, p_count = row[0].strip(), int(row[1])
                dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                parsed_rows.append((dt_obj, p_count))
              except (ValueError, IndexError):
                continue
      except Exception as e:
        print(f"Error reading metrics file {filename}: {e}")

  parsed_rows.sort(key=lambda x: x[0])
  return parsed_rows


def filter_and_aggregate(parsed_data, view_mode, target_input):
  """Filters data by Day, Month, or Year and aggregates player metrics appropriately."""
  if not parsed_data:
    return [], [], []

  if target_input:
    if view_mode == "Day":
      filtered = [
          row
          for row in parsed_data
          if row[0].strftime("%Y-%m-%d") == target_input
      ]
    elif view_mode == "Month":
      filtered = [
          row for row in parsed_data if row[0].strftime("%Y-%m") == target_input
      ]
    elif view_mode == "Year":
      filtered = [
          row for row in parsed_data if row[0].strftime("%Y") == target_input
      ]
  else:
    latest_dt = max(row[0] for row in parsed_data)
    if view_mode == "Day":
      cutoff_dt = latest_dt - timedelta(days=7)
      filtered = [row for row in parsed_data if row[0] >= cutoff_dt]
    elif view_mode == "Month":
      current_month_str = latest_dt.strftime("%Y-%m")
      filtered = [
          row
          for row in parsed_data
          if row[0].strftime("%Y-%m") == current_month_str
      ]
    elif view_mode == "Year":
      current_year_str = latest_dt.strftime("%Y")
      filtered = [
          row
          for row in parsed_data
          if row[0].strftime("%Y") == current_year_str
      ]

  if not filtered:
    return [], [], []

  unique_dates = load_unique_player_dates()

  if view_mode == "Day":
    timestamps = [row[0].strftime("%Y-%m-%d %H:%M:%S") for row in filtered]
    active_players = [row[1] for row in filtered]

    unique_joins = []
    for row in filtered:
      dt_hour = row[0].replace(minute=0, second=0, microsecond=0)
      matches = sum(
          1
          for ud in unique_dates
          if ud.replace(minute=0, second=0, microsecond=0) == dt_hour
      )
      unique_joins.append(matches)

    return timestamps, active_players, unique_joins

  elif view_mode == "Month":
    days_map = {}
    for row in filtered:
      dt, p_count = row[0], row[1]
      day_str = dt.strftime("%Y-%m-%d")
      if day_str not in days_map:
        days_map[day_str] = []
      days_map[day_str].append(p_count)

    sorted_days = sorted(days_map.keys())
    timestamps = [f"{d} 00:00:00" for d in sorted_days]
    active_players = [
        round(sum(days_map[d]) / len(days_map[d]), 1) if days_map[d] else 0
        for d in sorted_days
    ]

    unique_joins = []
    for d_str in sorted_days:
      d_obj = datetime.strptime(d_str, "%Y-%m-%d")
      count = sum(1 for ud in unique_dates if ud.date() == d_obj.date())
      unique_joins.append(count)

    return timestamps, active_players, unique_joins

  elif view_mode == "Year":
    months_map = {}
    for row in filtered:
      dt, p_count = row[0], row[1]
      month_str = dt.strftime("%Y-%m")
      if month_str not in months_map:
        months_map[month_str] = []
      months_map[month_str].append(p_count)

    sorted_months = sorted(months_map.keys())
    timestamps = [f"{m}-01 00:00:00" for m in sorted_months]
    active_players = [
        round(sum(months_map[m]) / len(months_map[m]), 1) if months_map[m] else 0
        for m in sorted_months
    ]

    unique_joins = []
    for m_str in sorted_months:
      count = sum(1 for ud in unique_dates if ud.strftime("%Y-%m") == m_str)
      unique_joins.append(count)

    return timestamps, active_players, unique_joins

  return [], [], []


def generate_plot_image(
    timestamps, active_players, unique_joins, view_mode, target_input
):
  if not timestamps:
    return ""

  plt.rcParams.update({
      "figure.facecolor": "#000c00",
      "axes.facecolor": "#000c00",
      "savefig.facecolor": "#000c00",
      "savefig.edgecolor": "none",
      "axes.edgecolor": "#0f44",
      "axes.labelcolor": "#0f4",
      "xtick.color": "#0f4",
      "ytick.color": "#0f4",
      "text.color": "#0f4",
  })

  fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
  x_indexes = np.arange(len(timestamps))

  formatted_labels = []
  for ts in timestamps:
    try:
      dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
      if view_mode == "Day":
        time_str = dt.strftime("%m/%d %H:%M")
      elif view_mode == "Month":
        time_str = dt.strftime("%b %d")
      else:
        time_str = dt.strftime("%b %Y")
      formatted_labels.append(time_str)
    except ValueError:
      formatted_labels.append(ts)

  bar_width = 0.35
  color_p = "#00ff66"
  color_u = "#ff00ff"

  ax.bar(
      x_indexes - bar_width / 2,
      active_players,
      width=bar_width,
      color=color_p,
      alpha=0.85,
      label="Active Players",
  )
  ax.bar(
      x_indexes + bar_width / 2,
      unique_joins,
      width=bar_width,
      color=color_u,
      alpha=0.85,
      label="Unique Joins",
  )

  ax.set_ylabel("Player Count", color=color_p)
  ax.set_xlabel(f"Timeline ({view_mode})", color="#0f4")
  ax.set_xticks(x_indexes)
  ax.set_xticklabels(formatted_labels, rotation=35, ha="right")
  ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12, integer=True))

  ax.set_ylim(bottom=0)
  ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
  ax.grid(True, color="#0f42", linestyle="--", alpha=0.5)

  title_suffix = f" [{target_input}]" if target_input else " (Latest)"
  ax.set_title(
      f"Bedrock Node Player Metrics - {view_mode} View{title_suffix}",
      color="#0f4",
      pad=15,
      fontweight="bold",
  )

  legend = ax.legend(
      loc="upper right", fontsize=8, facecolor="#000c00", edgecolor="#0f44"
  )
  for text in legend.get_texts():
    text.set_color("#0f4")

  plt.tight_layout()

  buf = io.BytesIO()
  plt.savefig(buf, format="png", bbox_inches="tight")
  buf.seek(0)
  chart_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
  plt.close(fig)

  return chart_b64

@app.route("/background.png")
def serve_background():
    return send_from_directory(DATA_DIR, "background.png")

@app.route("/banner.png")
def serve_banner():
  return send_from_directory(DATA_DIR, "banner.png")

@app.route("/icon.png")
def serve_icon():
  return send_from_directory(DATA_DIR, "icon.png")


@app.route("/manifest.json")
def serve_manifest():
  return jsonify({
      "name": "Bedrock Node",
      "short_name": "Bedrock Node",
      "start_url": "/",
      "display": "standalone",
      "background_color": "#000c00",
      "theme_color": "#000c00",
      "icons": [{"src": "/icon.png", "sizes": "512x512", "type": "image/png"}],
  })


@app.route("/bans", methods=["GET", "POST"])
def manage_bans():
  if not session.get("logged_in"):
    return redirect(url_for("login"))

  load_dotenv(os.path.join(DATA_DIR, "securekeys.env"), override=True)
  expected_code = os.getenv("BAN_SECRET_CODE", "BAN")

  if request.method == "POST":
    action = request.form.get("action")
    sec_code = request.form.get("sec_code", "").strip()

    if sec_code != expected_code:
      failures = session.get("ban_fail_count", 0) + 1
      session["ban_fail_count"] = failures
      username = session.get("username", "Unknown Admin")

      if failures >= 3:
        send_admin_alert(
            f"🚨 **BRUTE FORCE LOCKOUT:** `{username}` failed the Ban Matrix"
            " security code 3 times and was forcefully logged out."
        )
        session.clear()
        return redirect(url_for("login"))

      send_admin_alert(
          "⚠️ **SECURITY WARNING:** Incorrect security code attempted in Ban"
          f" Matrix by `{username}` (Attempt {failures}/3)."
      )
      return (
          """
            <body style='background:#000;color:#f44;font-family:monospace;padding:50px;text-align:center;'>
                <h1>ACCESS DENIED: Invalid Security Code.</h1>
                <p>Attempts remaining: {}</p>
                <a href='/bans' style='color:#0ff;'>Return to Ban Matrix</a>
            </body>
            """.format(3 - failures),
          403,
      )

    session["ban_fail_count"] = 0

    if action == "add":
      name = request.form.get("name", "").strip()
      xuid = request.form.get("xuid", "").strip()
      reason = request.form.get("reason", "No reason provided").strip()

      if name:
        blacklist = load_blacklist()
        key = xuid if xuid else name.lower()
        blacklist[key] = {
            "name": name,
            "reason": reason,
            "admin": session.get("username", "Admin"),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_blacklist(blacklist)

        if any(p.lower() == name.lower() for p in ONLINE_PLAYERS):
          send_to_mc(
              f'kick "{name}" You have been banned: {reason}', "BAN_TECH"
          )

        send_admin_alert(
            f"🔨 **BAN ADDED:** `{name}` was manually blacklisted by"
            f" `{session.get('username')}`."
        )

    elif action == "remove":
      key = request.form.get("key", "").strip()
      blacklist = load_blacklist()
      if key in blacklist:
        removed_name = blacklist[key].get("name", key)
        del blacklist[key]
        save_blacklist(blacklist)
        send_admin_alert(
            f"🔓 **UNBANNED:** `{removed_name}` was removed from the blacklist"
            f" by `{session.get('username')}`."
        )

    return redirect(url_for("manage_bans"))

  blacklist = load_blacklist()
  return render_template_string(
      BAN_HTML_TEMPLATE, bans=blacklist, banner=BACKGROUND_URL
  )


@app.route("/metrics-data", methods=["POST"])
def metrics_data():
  if not session.get("logged_in"):
    return jsonify({"error": "Unauthorized"}), 401

  view_mode = request.form.get("view_mode", "Day")
  target_input = request.form.get("target_input", "").strip()

  cache_key = (view_mode, target_input)
  now = datetime.now()

  with chart_cache_lock:
    if cache_key in CHART_CACHE:
      cached_item = CHART_CACHE[cache_key]
      if now - cached_item["timestamp"] < timedelta(hours=1):
        return jsonify({"chart_url": cached_item["chart_url"]})

  parsed_data = load_metrics_data()
  timestamps, active_players, unique_joins = filter_and_aggregate(
      parsed_data, view_mode, target_input
  )

  chart_url = None
  if timestamps:
    with chart_lock:
      chart_url = generate_plot_image(
          timestamps, active_players, unique_joins, view_mode, target_input
      )

    if chart_url:
      with chart_cache_lock:
        CHART_CACHE[cache_key] = {"chart_url": chart_url, "timestamp": now}

  return jsonify({"chart_url": chart_url})


@app.route("/api/logs")
def get_logs():
  with state_lock:
    current_actions = list(last_actions)
  response = jsonify({"actions": current_actions})
  response.headers.add("Access-Control-Allow-Origin", "*")
  return response


@app.route("/settings", methods=["GET", "POST"])
def manage_settings():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    load_dotenv(os.path.join(DATA_DIR, "securekeys.env"), override=True)
    expected_settings_pw = os.getenv("SETTINGS_PASSWORD", "admin123")
    
    if not session.get("settings_unlocked"):
        if request.method == "POST":
            entered_pw = request.form.get("settings_pw", "")
            if entered_pw == expected_settings_pw:
                session["settings_unlocked"] = True
                return redirect(url_for("manage_settings"))
            else:
                return render_template_string(
                    """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/png" href="/icon.png"><style>body{background:#000 url("{{b}}") center fixed;background-size:cover;color:#f44;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.box{background:rgba(0,0,0,0.9);padding:30px;border:1px solid #f44;border-radius:15px;text-align:center;}input{width:100%;padding:10px;margin:5px 0;background:#000;color:#f44;border:1px solid #f44;box-sizing:border-box;font-size:16px;}button{width:100%;padding:10px;background:#f44;color:#000;font-weight:bold;border:none;margin-top:10px;cursor:pointer;font-size:16px;}</style></head><body><div class="box"><h2>SETTINGS LOCKED</h2><p style="color:#ffcc00;font-size:13px;">Incorrect password. Try again:</p><form method="POST"><input name="settings_pw" type="password" placeholder="Password..." required autofocus><button>UNLOCK</button></form><br><a href="/" style="color:#0ff;font-size:12px;text-decoration:none;">[ Return to Dashboard ]</a></div></body></html>""",
                    b=BACKGROUND_URL
                )
        
        return render_template_string(
            """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/png" href="/icon.png"><style>body{background:#000 url("{{b}}") center fixed;background-size:cover;color:#0f4;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.box{background:rgba(0,0,0,0.9);padding:30px;border:1px solid #0f4;border-radius:15px;text-align:center;}input{width:100%;padding:10px;margin:5px 0;background:#000;color:#0f4;border:1px solid #0f4;box-sizing:border-box;font-size:16px;}button{width:100%;padding:10px;background:#0f4;color:#000;font-weight:bold;border:none;margin-top:10px;cursor:pointer;font-size:16px;}</style></head><body><div class="box"><h2>SETTINGS LOCKED</h2><p style="color:#88cc88;font-size:13px;">Enter Settings Password:</p><form method="POST"><input name="settings_pw" type="password" placeholder="Password..." required autofocus><button>UNLOCK</button></form><br><a href="/" style="color:#0ff;font-size:12px;text-decoration:none;">[ Return to Dashboard ]</a></div></body></html>""",
            b=BACKGROUND_URL
        )
    
    env_path = os.path.join(DATA_DIR, "securekeys.env")
    expected_code = os.getenv("BAN_SECRET_CODE", "BAN123")
    
    if request.method == "POST":
      bot_token = request.form.get("bot_token", "").strip()
      webhook_url = request.form.get("webhook_url", "").strip()
      vc_status = request.form.get("vc_status", "0").strip()
      vc_players = request.form.get("vc_players", "0").strip()
      cf_token = request.form.get("cf_token", "").strip()

      new_ban_code = request.form.get("ban_code", "").strip()
      ban_code = new_ban_code if new_ban_code else expected_code

      new_admin_pw = request.form.get("new_admin_pw", "").strip()
      if new_admin_pw:
        current_user = session.get("username", "owner")
        current_accounts = load_accounts()
        if current_user in current_accounts:
          current_accounts[current_user] = generate_password_hash(new_admin_pw)
          with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_accounts, f, indent=4)

      new_admin_user = request.form.get("new_admin_user", "").strip().lower()
      new_admin_pass = request.form.get("new_admin_pass", "").strip()
      if new_admin_user and new_admin_pass:
        current_accounts = load_accounts()
        current_accounts[new_admin_user] = generate_password_hash(new_admin_pass)
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
          json.dump(current_accounts, f, indent=4)
        send_admin_alert(
            f"👤 **ADMIN CREATED:** New admin account `{new_admin_user}` was"
            f" added by `{session.get('username')}`."
        )

      flask_secret = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
      use_playit = os.getenv("USE_PLAYIT", "False")
      current_settings_pw = os.getenv("SETTINGS_PASSWORD", "admin123")

      env_content = (
          "# --- BEDROCK NODE CONFIGURATION ---\n"
          f"USE_PLAYIT={use_playit}\n"
          f"CLOUDFLARE_TUNNEL_TOKEN={cf_token}\n\n"
          f"DISCORD_BOT_TOKEN={bot_token}\n"
          f"ADMIN_WEBHOOK_URL={webhook_url}\n"
          f"VC_STATUS_ID={vc_status}\n"
          f"VC_PLAYERS_ID={vc_players}\n\n"
          f"FLASK_PORT=5000\n"
          f"FLASK_SECRET_KEY={flask_secret}\n"
          f"BAN_SECRET_CODE={ban_code}\n"
          f"SETTINGS_PASSWORD={current_settings_pw}\n"
      )

      with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

      send_admin_alert(
          "⚙️ **SETTINGS UPDATED:** Server configuration parameters were"
          " modified via the web dashboard."
      )
      return redirect(url_for("home"))
        
    return render_template_string(
        """
        <!DOCTYPE html><html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" type="image/png" href="/icon.png">
        <style>
        body { background: linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)), url("{{banner}}") fixed center; background-size: cover; color: #0f4; font-family: sans-serif; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box; margin:0;}
        .panel { width: 100%; max-width: 600px; border: 1px solid #0f45; padding: 25px; border-radius: 20px; background: rgba(0,12,0,0.95); box-sizing: border-box; position: relative; }
        .close-btn { position: absolute; top: 15px; right: 15px; padding: 5px 12px; background: #ff4444; color: #fff; text-decoration: none; font-family: monospace; font-weight: bold; border-radius: 5px; }
        .warning-box { background: rgba(255, 170, 0, 0.1); border: 1px solid #ffaa0055; padding: 12px; border-radius: 10px; margin-bottom: 20px; font-size: 12px; font-family: monospace; color: #ffcc00; text-align: center; line-height: 1.4; }
        h2 { text-align: center; color: #0f4; margin-top: 0; }
        input { width: 100%; background: #000; color: #0f4; border: 1px solid #0f44; padding: 10px; border-radius: 10px; box-sizing: border-box; font-size: 14px; margin-bottom: 12px; }
        label { font-size: 13px; font-family: monospace; color: #88cc88; display: block; margin-bottom: 4px; }
        button { width: 100%; padding: 12px; background: #0f4; color: #000; font-weight: bold; border: none; cursor: pointer; border-radius: 10px; font-size: 14px; margin-top: 10px; }
        </style></head><body>
        <div class="panel">
            <a href="/" class="close-btn">[X]</a>
            <h2>Server Settings & Integrations</h2>
            
            <div class="warning-box">
                ⚠️ <b>NOTICE:</b> You must stop and restart the script for token or ID changes to take effect!
            </div>

            <form method="POST">
                <label>Discord Bot Token:</label>
                <input name="bot_token" value="{{ config.bot_token }}" autocomplete="off">
                
                <label>Admin Webhook URL (#server-alerts):</label>
                <input name="webhook_url" value="{{ config.webhook_url }}" autocomplete="off">
                
                <label>Status Voice Channel ID:</label>
                <input name="vc_status" value="{{ config.vc_status }}" autocomplete="off">
                
                <label>Players Voice Channel ID:</label>
                <input name="vc_players" value="{{ config.vc_players }}" autocomplete="off">
                
                <label>Cloudflare Tunnel Token:</label>
                <input name="cf_token" value="{{ config.cf_token }}" autocomplete="off">
                
                <label>Ban Matrix Security Code (Leave blank to keep current):</label>
                <input type="password" name="ban_code" placeholder="••••••••" autocomplete="off">
                
                <label>Change Web Dashboard Password (Leave blank to keep current):</label>
                <input type="password" name="new_admin_pw" placeholder="New Password..." autocomplete="off">
                
                <hr style="border: 0; border-top: 1px solid #0f44; margin: 20px 0;">
                <h3 style="color: #0f4; font-size: 15px; margin-bottom: 10px; text-align: center;">Add New Admin Account</h3>
                
                <label>New Admin Username:</label>
                <input name="new_admin_user" placeholder="Username..." autocomplete="off">
                
                <label>New Admin Password:</label>
                <input type="password" name="new_admin_pass" placeholder="Password..." autocomplete="off">
                
                <button type="submit">SAVE CHANGES</button>
            </form>
        </div>
        </body></html>
        """,
        banner=BACKGROUND_URL,
        config={
            "bot_token": os.getenv("DISCORD_BOT_TOKEN", ""),
            "webhook_url": os.getenv("ADMIN_WEBHOOK_URL", ""),
            "vc_status": os.getenv("VC_STATUS_ID", "0"),
            "vc_players": os.getenv("VC_PLAYERS_ID", "0"),
            "cf_token": os.getenv("CLOUDFLARE_TUNNEL_TOKEN", ""),
            "ban_code": "",
        },
    )

@app.route("/shutdown", methods=["POST"])
def shutdown():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    send_admin_alert("🛑 **SYSTEM SHUTDOWN:** Graceful shutdown initiated via web dashboard.")
    
    send_to_mc("stop", "SHUTDOWN")
    
    global mc_process
    if mc_process and mc_process.poll() is None:
        try:
            mc_process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            if IS_WINDOWS:
                subprocess.run("taskkill /F /IM bedrock_server.exe /IM playit.exe /IM cloudflared.exe /T", shell=True, capture_output=True)
            else:
                subprocess.run("pkill -9 bedrock_server; pkill -9 playit; pkill -9 cloudflared", shell=True, capture_output=True)
    
    if IS_WINDOWS:
        subprocess.run("taskkill /F /IM playit.exe /IM cloudflared.exe /T", shell=True, capture_output=True)
    else:
        subprocess.run("pkill -9 playit; pkill -9 cloudflared", shell=True, capture_output=True)

    threading.Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/server-status")
def server_status():
  global ONLINE_PLAYERS
  with state_lock:
    p_count = len(ONLINE_PLAYERS) if is_running else 0
  response = jsonify({"online": is_running, "players": p_count, "max": 30})
  response.headers.add("Access-Control-Allow-Origin", "*")
  response.headers.add("Access-Control-Allow-Methods", "GET")
  return response


@app.route("/api/stats")
def stats():
  global ONLINE_PLAYERS
  uptime = (
      str(datetime.now() - start_time).split(".")[0]
      if start_time
      else "0:00:00"
  )

  now = datetime.now()
  target_hours = [2, 8, 14, 20]

  next_target = None
  for h in target_hours:
    candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
    if candidate > now:
      next_target = candidate
      break
  if not next_target:
    next_target = (now + timedelta(days=1)).replace(
        hour=2, minute=0, second=0, microsecond=0
    )

  remaining = next_target - now
  restart_in = str(remaining).split(".")[0]

  with state_lock:
    if is_running:
      p_count = len(ONLINE_PLAYERS)
      players_str = f"{p_count} / 30"
    else:
      ONLINE_PLAYERS.clear()
      players_str = "OFFLINE"

  disk_usage = shutil.disk_usage(SERVER_DIR)
  free_gb = round(disk_usage.free / (1024**3), 1)

  response = jsonify({
      "cpu": f"{psutil.cpu_percent()}%",
      "ram": f"{psutil.virtual_memory().percent}%",
      "disk": f"{free_gb} GB",
      "uptime": uptime,
      "status": "ONLINE" if is_running else "OFFLINE",
      "restart_in": restart_in,
      "players": players_str,
  })

  response.headers.add("Access-Control-Allow-Origin", "*")
  response.headers.add("Access-Control-Allow-Methods", "GET")
  return response


@app.route("/login", methods=["GET", "POST"])
def login():
  global failed_attempts
  
  current_accounts = load_accounts()
    
  ip = request.remote_addr
  if failed_attempts.get(ip, 0) >= 3:
    return (
        "<body"
        " style='background:#000;color:#f00;font-family:monospace;padding:50px;'><h1>LOCKED"
        " OUT</h1></body>"
    ), 403

  if request.method == "POST":
    u, p = request.form.get("user", "").lower(), request.form.get("pw", "")

    if u in current_accounts and check_password_hash(current_accounts[u], p):
      session["logged_in"] = True
      session["username"] = u
      failed_attempts[ip] = 0
      log_admin_event("LOGIN", u, ip)
      return redirect(url_for("home"))
    else:
      failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
      time.sleep(2)
      return render_template_string(
          """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/png" href="/icon.png"><link rel="apple-touch-icon" href="/icon.png"><link rel="manifest" href="/manifest.json"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Bedrock Node"><style>body{background:#000 url("{{b}}") center fixed;background-size:cover;color:#f44;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.box{background:rgba(0,0,0,0.9);padding:30px;border:1px solid #f44;border-radius:15px;text-align:center;}input{width:100%;padding:10px;margin:5px 0;background:#000;color:#f44;border:1px solid #f44;box-sizing:border-box;font-size:16px;}button{width:100%;padding:10px;background:#f44;color:#000;font-weight:bold;border:none;margin-top:10px;cursor:pointer;font-size:16px;}</style></head><body><div class="box"><h2>ACCESS DENIED</h2><p>Attempt {{a}} of 3</p><form method="POST"><input name="user" placeholder="USER"><input name="pw" type="password" placeholder="PASS"><button>RETRY</button></form></div></body></html>""",
          b=BACKGROUND_URL,
          a=failed_attempts[ip],
      )

  return render_template_string(
      """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/png" href="/icon.png"><link rel="apple-touch-icon" href="/icon.png"><link rel="manifest" href="/manifest.json"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Bedrock Node"><style>body{background:#000 url("{{b}}") center fixed;background-size:cover;color:#0f4;font-family:monospace;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;}.box{background:rgba(0,0,0,0.9);padding:30px;border:1px solid #0f4;border-radius:15px;text-align:center;} h2 { text-align: center; } input{width:100%;padding:10px;margin:5px 0;background:#000;color:#0f4;border:1px solid #0f4;box-sizing:border-box;font-size:16px;}button{width:100%;padding:10px;background:#0f4;color:#000;font-weight:bold;border:none;margin-top:10px;cursor:pointer;font-size:16px;}.footer{margin-top:15px;font-size:11px;color:#0f48;letter-spacing:0.5px;line-height:1.4;}</style></head><body><div class="box"><h2>Bedrock Node Hub</h2><form method="POST"><input name="user" placeholder="USER"><input name="pw" type="password" placeholder="PASS"><button>ENTER</button></form><div class="footer">© 2026 Nutcrustys420™. All Rights Reserved.<br>Tested & powered by Stonercraft420</div></div></body></html>""",
      b=BACKGROUND_URL,
  )


@app.route("/logout")
def logout():
  username = session.get("username", "Unknown")
  ip = request.remote_addr

  if session.get("logged_in"):
    log_admin_event("LOGOUT", username, ip)

  session.clear()
  return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def home():
  if not session.get("logged_in"):
    return redirect(url_for("login"))
  if is_restarting:
    return render_template_string(
        """<body style="background:#000;color:#f44;text-align:center;padding-top:100px;font-family:monospace;"><h1>REBOOTING</h1><div style="font-size:80px;">{{s}}</div><script>setInterval(()=>location.reload(),5000)</script></body>""",
        s=seconds_left,
    )
  if request.method == "POST":
    if "note" in request.form:
      with notes_lock:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
          f.write(request.form.get("note", ""))
    else:
      c = request.form.get("c", "").strip()
      if c:
        send_to_mc(c, session["username"].upper())
    return redirect(url_for("home"))

  return render_template_string(
      """
    <!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="/icon.png">
    <link rel="apple-touch-icon" href="/icon.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Bedrock Node">

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>

    <style>
    body { 
        background: linear-gradient(rgba(0,0,0,0.85),rgba(0,0,0,0.85)), url("{{banner}}") fixed center; 
        background-size: cover; 
        color: #0f4; 
        font-family: sans-serif; 
        margin: 0; 
        padding: 20px; 
        padding-top: 80px; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        gap: 20px; 
        position: relative; 
    }

    .top-bar {
        width: 100%;
        background: rgba(0, 12, 0, 0.98);
        border-bottom: 1px solid #0f45;
        padding: 10px 20px;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        box-sizing: border-box;
        position: fixed;
        top: 0;
        left: 0;
        z-index: 1000;
        gap: 15px;
    }

    .logout-btn {
        color: #ff4444;
        text-decoration: none;
        font-family: monospace;
        font-size: 14px;
        border: 1px solid #ff444455;
        padding: 8px 15px;
        border-radius: 8px;
        background: rgba(0,0,0,0.85);
        font-weight: bold;
    }

    .logout-btn:hover { background: #ff4444; color: #000; }

    .dropdown { 
        position: relative; 
        display: inline-block; 
    }

    .dropbtn {
        background: #0f4;
        color: #000;
        padding: 8px 15px;
        font-weight: bold;
        border: none;
        cursor: pointer;
        border-radius: 8px;
        font-size: 14px;
        margin: 0;
    }

    .dropdown-content {
        display: none;
        position: absolute;
        right: 0;
        top: 100%;
        /* REMOVED margin-top and added padding-top to create an invisible hover bridge */
        padding-top: 8px; 
        background-color: transparent; /* Makes the padding area transparent but hoverable */
        min-width: 200px;
        z-index: 1001;
    }

    /* Inner box wrapper to keep your border and background intact */
    .dropdown-inner {
        background-color: rgba(0, 12, 0, 0.98);
        border: 1px solid #0f45;
        border-radius: 8px;
        overflow: hidden;
    }

    .dropdown-content a, .dropdown-content button {
        color: #0f4;
        padding: 12px 16px;
        text-decoration: none;
        display: block;
        background: none;
        border: none;
        border-bottom: 1px solid #0f42;
        width: 100%;
        text-align: left;
        font-family: sans-serif;
        font-size: 14px;
        cursor: pointer;
        margin: 0;
        border-radius: 0;
    }
    
    .dropdown-content a:hover, .dropdown-content button:hover { background-color: rgba(0, 255, 68, 0.1); }
    .dropdown:hover .dropdown-content { display: block; }

    .panel { 
        width: 100%; 
        max-width: 900px; 
        border: 1px solid #0f45; 
        padding: 25px; 
        border-radius: 20px; 
        background: rgba(0,12,0,0.95); 
        box-sizing: border-box; 
    }
    h2 { text-align: center; margin-top: 0; font-size: 22px; }
    input, textarea { width: 100%; background: #000; color: #0f4; border: 1px solid #0f44; padding: 12px; border-radius: 10px; box-sizing: border-box; font-size: 16px; }
    textarea { height: 450px; resize: none; }
    button { width: 100%; padding: 12px; background: #0f4; color: #000; font-weight: bold; border: none; cursor: pointer; margin-top: 10px; border-radius: 10px; font-size: 16px; }
    .l { background: #000; height: 450px; overflow-y: auto; padding: 10px; font-family: monospace; font-size: 13px; margin-top: 15px; border: 1px solid #0f42; border-radius: 10px; display: flex; flex-direction: column; }

    .stats-bar { 
        display: flex; 
        flex-direction: column; 
        font-size: 14px; 
        margin-bottom: 20px; 
        gap: 10px; 
        background: rgba(0, 0, 0, 0.4); 
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #0f42;
    }
    .stats-row { 
        display: flex; 
        justify-content: space-around; 
        flex-wrap: wrap; 
        gap: 15px; 
    }
    .stats-row-center { 
        display: flex; 
        justify-content: center; 
        text-align: center; 
        margin-top: 4px; 
        width: 100%; 
        font-size: 15px; 
    }

    .quick-actions {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
    }

    .btn-restart {
        width: 100%;
        margin-top: 0;
        background: #ffaa00;
        color: #000;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 12px;
        cursor: pointer;
        font-size: 14px;
    }

    .btn-placeholder {
        flex: 1;
        margin-top: 0;
        background: rgba(0, 255, 68, 0.05);
        color: #0f48;
        border: 1px dashed #0f44;
        border-radius: 10px;
        padding: 12px;
        cursor: not-allowed;
        font-size: 14px;
    }

    @media (max-width: 768px) {
        body { padding: 10px; gap: 15px; }
        .panel { width: 100%; max-width: 100%; padding: 15px; }
    }
    </style></head><body>

    <div class="top-bar">
        <div class="dropdown">
            <button class="dropbtn">ADMIN TOOLS ▼</button>
            <div class="dropdown-content">
                <div class="dropdown-inner">
                    <button type="button" onclick="openMetricsModal()">View Graphs</button>
                    <button type="button" onclick="openNotesModal()">Admin Notes</button>
                    <a href="/bans">Manage Bans</a>
                    <a href="/settings">Server Settings</a>
                    <button type="button" onclick="openContactModal()">Contact & Support</button>
                </div>
            </div>
        </div>
        <a href="/logout" class="logout-btn">LOGOUT</a>
    </div>
    
    <div class="panel">
        <h2>Bedrock Node Hub</h2>
    
        <div class="stats-bar">
            <div class="stats-row">
                <span>CPU: <b id="cpu">...</b></span>
                <span>RAM: <b id="ram">...</b></span>
                <span>DISK: <b id="disk">...</b></span>
                <span style="color:#0ff">RST IN: <b id="rst">...</b></span>
            </div>
            <div class="stats-row-center">
                <span>PLAYERS: <b id="players">...</b></span>
            </div>
        </div>

        <div class="quick-actions">
            <button type="button" class="btn-restart" onclick="openRestartModal()" style="flex: 1; margin-top: 0;">RESTART SERVER</button>
            <button type="button" onclick="openStopModal()" style="flex: 1; margin-top: 0; background: #ff4444; color: #fff; font-weight: bold; border: none; border-radius: 10px; padding: 12px; cursor: pointer; font-size: 14px;">STOP SERVER</button>
            <button type="button" class="btn-placeholder" style="flex: 1; margin-top: 0;">SLOT 3</button>
        </div>

        <div class="l" id="logBox">{% for a in actions %}<div>{{a | safe}}</div>{% endfor %}</div>

        <form method="POST" style="margin-top: 15px;">
            <input name="c" placeholder="Admin Command..." autocomplete="off" autofocus>
            <button type="submit">RUN</button>
        </form>

        <div style="margin-top: 20px; text-align: center; font-size: 11px; color: #0f48; font-family: monospace; line-height: 1.4;">
            © 2026 Nutcrustys420™. All Rights Reserved.<br>
            Tested & powered by Stonercraft420
        </div>
    </div>

    <div id="restartModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
        <div style="background:rgba(0,12,0,0.98); border:1px solid #0f45; padding:25px; border-radius:20px; width:100%; max-width:400px; text-align:center; box-sizing:border-box;">
            <h3 style="color:#0f4; margin-top:0;">RESTART SYSTEM</h3>
            <p style="color:#0ff; font-size:13px; font-family:monospace; margin-bottom:20px;">Are you sure you want to restart Bedrock Node?</p>
            <div style="display:flex; gap:10px;">
                <button type="button" id="restartConfirmBtn" style="background:#0f4; color:#000; margin-top:0;">YES</button>
                <button type="button" onclick="closeRestartModal()" style="background:#ff4444; color:#fff; margin-top:0;">NO</button>
            </div>
        </div>
    </div>

    <div id="notesModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
        <div style="background:rgba(0,12,0,0.98); border:1px solid #0f45; padding:25px; border-radius:20px; width:100%; max-width:700px; position:relative; box-sizing:border-box; display:flex; flex-direction:column;">
            <button type="button" onclick="closeNotesModal()" style="position:absolute; top:15px; right:15px; width:auto; padding:5px 12px; background:#ff4444; color:#fff; font-size:14px; margin:0;">[X]</button>
            <h2 style="text-align:center; color:#0f4; margin-top:0;">ADMIN NOTES</h2>
            <form method="POST" style="display:flex; flex-direction:column; flex: 1; margin-top:10px;">
                <textarea name="note" placeholder="Server notes, tasks, player watchlist..." style="height:350px; margin-bottom:15px;">{{notes}}</textarea>
                <button type="submit">SAVE NOTES</button>
            </form>
        </div>
    </div>

    <div id="metricsModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; overflow-y:auto; padding:20px; box-sizing:border-box;">
        <div style="background:rgba(0,12,0,0.98); border:1px solid #0f45; padding:25px; border-radius:20px; width:100%; max-width:900px; position:relative; box-sizing:border-box;">
            <button type="button" onclick="closeMetricsModal()" style="position:absolute; top:15px; right:15px; width:auto; padding:5px 12px; background:#ff4444; color:#fff; font-size:14px; margin:0;">[X]</button>
            <h2 style="text-align:center; color:#0f4; margin-top:0;">BEDROCK NODE METRICS DASHBOARD</h2>
            
            <form id="metricsForm" onsubmit="loadMetricsChart(event)" style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-bottom:20px;">
                <select id="modal_view_mode" style="background:#000; color:#0f4; border:1px solid #0f44; padding:10px; border-radius:10px; flex:1; min-width:150px;">
                    <option value="Day">Day View (Hourly)</option>
                    <option value="Month">Month View (Daily)</option>
                    <option value="Year">Year View (Monthly)</option>
                </select>
                <input id="modal_target_input" placeholder="Filter (YYYY-MM-DD)" style="background:#000; color:#0f4; border:1px solid #0f44; padding:10px; border-radius:10px; flex:1; min-width:150px;">
                <button type="submit" style="width:auto; padding:10px 20px; margin:0;">LOAD GRAPH</button>
            </form>

            <div id="modalChartContainer" style="display:flex; justify-content:center; min-height:300px; align-items:center;">
                <p style="color:#ffcc00; font-family:monospace;">Click 'Load Graph' to view server metrics...</p>
            </div>
        </div>
    </div>

    <div id="stopModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
        <div style="background:rgba(0,12,0,0.98); border:1px solid #ff444455; padding:25px; border-radius:20px; width:100%; max-width:400px; text-align:center; box-sizing:border-box;">
            <h3 style="color:#ff4444; margin-top:0;">STOP ENTIRE SCRIPT</h3>
            <p style="color:#ffcc00; font-size:13px; font-family:monospace; margin-bottom:20px;">Are you sure? This will shut down the server and close the entire application.</p>
            <div style="display:flex; gap:10px;">
                <button type="button" id="stopConfirmBtn" style="background:#ff4444; color:#fff; margin-top:0;">YES, STOP</button>
                <button type="button" onclick="closeStopModal()" style="background:#0f4; color:#000; margin-top:0;">CANCEL</button>
            </div>
        </div>
    </div>

    <div id="contactModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; padding:20px; box-sizing:border-box;">
        <div style="background:rgba(0,12,0,0.98); border:1px solid #0f45; padding:25px; border-radius:20px; width:100%; max-width:450px; text-align:center; box-sizing:border-box; position:relative;">
            <button type="button" onclick="closeContactModal()" style="position:absolute; top:15px; right:15px; width:auto; padding:5px 12px; background:#ff4444; color:#fff; font-size:14px; margin:0;">[X]</button>
            <h3 style="color:#0f4; margin-top:0;">Support & Contact</h3>
            <p style="color:#ffcc00; font-size:13px; font-family:monospace; line-height:1.5;">
                <b>Creator:</b> Nutcrustys420<br>
                <b>Community:</b> Stonercraft420<br><br>
                Need help, want to report an issue, or check for updates? Join our community Discord server:
            </p>
            <a href="https://discord.gg/aSVPbEpkuA" target="_blank" style="display:block; background:#003322; color:#00ff66; padding:12px; border-radius:10px; text-decoration:none; font-weight:bold; font-family:monospace; margin-bottom:15px; border:1px solid #0f44;">[ Open Support Discord ]</a>
            <button type="button" onclick="closeContactModal()" style="background:#0f4; color:#000; margin-top:0;">CLOSE</button>
        </div>
    </div>

    <script>

    function openStopModal() { document.getElementById('stopModal').style.display = 'flex'; }
    function closeStopModal() { document.getElementById('stopModal').style.display = 'none'; }

    document.getElementById('stopConfirmBtn').onclick = function() {
        fetch('/shutdown', { method: 'POST' })
        .then(() => {
            document.body.innerHTML = '<div style="background:#000;color:#ff4444;height:100vh;display:flex;justify-content:center;align-items:center;font-family:monospace;font-size:24px;">SYSTEM SHUTDOWN COMPLETE</div>';
        });
    };

    function openNotesModal() { document.getElementById('notesModal').style.display = 'flex'; }
    function closeNotesModal() { document.getElementById('notesModal').style.display = 'none'; }

    function openRestartModal() { document.getElementById('restartModal').style.display = 'flex'; }
    function closeRestartModal() { document.getElementById('restartModal').style.display = 'none'; }

    function openContactModal() { document.getElementById('contactModal').style.display = 'flex'; }
    function closeContactModal() { document.getElementById('contactModal').style.display = 'none'; }

    function openMetricsModal() {
        document.getElementById('metricsModal').style.display = 'flex';
        loadMetricsChart(); 
    }
    function closeMetricsModal() {
        document.getElementById('metricsModal').style.display = 'none';
    }

    document.getElementById('restartConfirmBtn').onclick = function() {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/';

        const cmdInput = document.createElement('input');
        cmdInput.type = 'hidden';
        cmdInput.name = 'c';
        cmdInput.value = 'stop';
        form.appendChild(cmdInput);

        document.body.appendChild(form);
        form.submit();
    };

    window.addEventListener('beforeunload', () => {
        localStorage.setItem('scrollPos', window.scrollY);
    });

    window.addEventListener('load', () => {
        const scrollPos = localStorage.getItem('scrollPos');
        if (scrollPos) window.scrollTo(0, parseInt(scrollPos));

        const logBox = document.getElementById('logBox');
        if (logBox) logBox.scrollTop = logBox.scrollHeight;
    });

    const socket = io();

    socket.on('connect', () => {
        console.log("Connected to Bedrock Node via WebSockets!");
    });

    socket.on('update_stats', (d) => {
        document.getElementById('cpu').innerText = d.cpu; 
        document.getElementById('ram').innerText = d.ram;
        document.getElementById('disk').innerText = d.disk;
        document.getElementById('players').innerText = d.players;
        document.getElementById('rst').innerText = d.restart_in;
    });

    socket.on('console_log', (data) => {
        const logBox = document.getElementById('logBox');
        const isScrolledToBottom = logBox.scrollHeight - logBox.clientHeight <= logBox.scrollTop + 50;
        
        logBox.innerHTML += `<div>${data.line}</div>`;

        if (isScrolledToBottom) {
            logBox.scrollTop = logBox.scrollHeight;
        }
    });

    function loadMetricsChart(e) {
        if (e) e.preventDefault();
        const viewMode = document.getElementById('modal_view_mode').value;
        const targetInput = document.getElementById('modal_target_input').value;
        const container = document.getElementById('modalChartContainer');
        
        container.innerHTML = '<p style="color:#0ff; font-family:monospace;">Generating graph...</p>';
        
        fetch('/metrics-data', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: `view_mode=${viewMode}&target_input=${targetInput}`
        })
        .then(r => r.json())
        .then(data => {
            if (data.chart_url) {
                container.innerHTML = `<img src="data:image/png;base64,${data.chart_url}" style="max-width:100%; border-radius:10px; border:1px solid #0f43;">`;
            } else {
                container.innerHTML = '<p style="color:#ffcc00; font-family:monospace;">-> Notice: No data found for that specific filter range.</p>';
            }
        });
    }
    </script>
</body></html>""",
      banner=BACKGROUND_URL,
      actions=last_actions,
      notes=get_notes(),
  )

if __name__ == "__main__":
    env_path = os.path.join(DATA_DIR, "securekeys.env")
    accounts_path = os.path.join(DATA_DIR, "secureaccounts.json")

    if not os.path.exists(env_path) or not os.path.exists(accounts_path):
        print("No configuration found. Launching desktop setup wizard GUI...")
        run_desktop_wizard(DATA_DIR)
        print("Wizard complete. Starting Bedrock Node Hub...")
    else:
        print("Configuration found. Starting Bedrock Node Hub...")

        threading.Thread(target=lambda: (time.sleep(2), open_as_app("http://localhost:5000")), daemon=True).start()

    ACCOUNTS = load_accounts()

    if os.name == "nt":
        subprocess.run(
            "taskkill /F /IM bedrock_server.exe /IM playit.exe /IM cloudflared.exe /T",
            shell=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            "pkill -9 bedrock_server; pkill -9 playit; pkill -9 cloudflared",
            shell=True,
            capture_output=True,
        )

    try:
        threading.Thread(target=server_manager, daemon=True).start()
        threading.Thread(target=local_console_bridge, daemon=True).start()
        threading.Thread(target=restart_timer, daemon=True).start()
        threading.Thread(target=nightly_backup_scheduler, daemon=True).start()
        threading.Thread(target=run_discord_bot, daemon=True).start()
        threading.Thread(target=hourly_metrics_logger, daemon=True).start()
        threading.Thread(target=websocket_stats_broadcaster, daemon=True).start()

        socketio.run(app, host="0.0.0.0", port=FLASK_PORT)

    except Exception as e:
        print(e)