# MC-Server-With-DC-Bot-Management

This project enables **fully automated management of a Minecraft server via Discord**. It uses two droplets:

- 💬 `dc-server-bot` – Discord bot + monitor services
- 🟩 `mc-server` – Minecraft Fabric server

Features:
- Players can start the MC server via `!serverstart` and stop it with `!serverstop` on Discord.
- The monitor automatically shuts the server down after 5 minutes of inactivity.
- Server is only active during allowed hours per day.
- Graceful shutdown with a warning Discord message.
- Services managed using `systemd`.

## 🌐 Requirements

- 2 Ubuntu-based virtual machines (e.g., DigitalOcean, Hetzner)
- A domain or static IPs
- Python 3.10+
- A Discord bot token & channel
- SSH key-based login between droplets

## 🛠 Setup Steps

### 1. Create Two Droplets

- **Bot droplet (`dc-server-bot`)**
- **Minecraft server droplet (`mc-server`)**

Give them fixed IPs or assign internal networking if supported.

### 2. Set Up SSH Access

On `dc-server-bot`, generate SSH key and upload to `mc-server`:

```bash
ssh-keygen -t rsa -b 4096
ssh-copy-id root@<MC_SERVER_IP>
```

### 3. Install Dependencies (on dc-server-bot)
```bash
sudo apt update
sudo apt install python3-pip python3-venv screen git
python3 -m venv botenv
source botenv/bin/activate
```

# Install required Python packages
```bash
pip install -r requirements.txt
```

### 4. Clone Repo (on dc-server-bot)
git clone https://github.com/MASTERmaxiPL/mc-discord-bot.git
cd mc-discord-bot

### 5. Configure .env
```
# Discord Config
DISCORD_TOKEN=your_token_here
DISCORD_CHANNEL_ID=channel_id_here

# Minecraft Server IP (public or private)
MC_SERVER_IP=
MC_QUERY_PORT=25565
MC_PATH=/root/fabric-server
MC_STOP_CMD=screen -S mc -X stuff 'stop\n'

# SSH Access to MC Server
SSH_HOST=
SSH_USER=root
SSH_KEY_PATH=/root/.ssh/id_rsa

# Allowed Hours per Day
ALLOWED_HOURS_MON=
ALLOWED_HOURS_TUE=
ALLOWED_HOURS_WED=
ALLOWED_HOURS_THU=
ALLOWED_HOURS_FRI=
ALLOWED_HOURS_SAT=
ALLOWED_HOURS_SUN=

# Timezone
TIMEZONE=Your_Timezone
```

### 6. Configure systemd Services
Create 2 files in /etc/systemd/system/:

/etc/systemd/system/mc-bot.service
```
[Unit]
Description=Minecraft Discord Bot
After=network.target

[Service]
WorkingDirectory=/root/mc-discord-bot
ExecStart=/root/botenv/bin/python bot.py
Restart=always
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/root/mc-discord-bot/.env

[Install]
WantedBy=multi-user.target
```

/etc/systemd/system/mc-monitor.service
```
[Unit]
Description=Minecraft Server Monitor
After=network.target

[Service]
WorkingDirectory=/root/mc-discord-bot
ExecStart=/root/botenv/bin/python monitor.py
Restart=always
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/root/mc-discord-bot/.env

[Install]
WantedBy=multi-user.target
```

Then reload and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mc-bot.service
sudo systemctl enable mc-monitor.service
sudo systemctl start mc-bot.service
sudo systemctl start mc-monitor.service
```

## 📈 Monitoring & Logs
Check logs:
```bash
sudo journalctl -u mc-bot -f
sudo journalctl -u mc-monitor -f
```
## 🔁 Updating Code or .env
```bash
sudo systemctl restart mc-bot.service
sudo systemctl restart mc-monitor.service
```
