import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import requests
import paramiko
from datetime import datetime
import asyncio
import subprocess
import pytz
from mcstatus import JavaServer

# Load .env file
load_dotenv(dotenv_path="/root/mc-discord-bot/.env")

# DISCORD
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# DIGITALOCEAN
DO_API_TOKEN = os.getenv("DO_API_TOKEN")

DROPLET_ID = os.getenv("DROPLET_ID")
DROPLET_IP = os.getenv("DROPLET_IP")

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

# MINECRAFT
MC_SERVER_IP = os.getenv("MC_SERVER_IP")
MC_QUERY_PORT = int(os.getenv("MC_QUERY_PORT", "25565"))
MC_PATH = os.getenv("MC_PATH")
MC_START_CMD = os.getenv("MC_COMMAND")

# TIMEZONE
TIMEZONE = os.getenv("TIMEZONE")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

local_tz = pytz.timezone(TIMEZONE)

def get_current_local_hour_and_day():
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    now_local = now_utc.astimezone(local_tz)
    current_hour = now_local.hour
    current_day = now_local.strftime("%a").upper()  # e.g. 'MON', 'TUE', 'FRI'
    return current_hour, current_day

# Helper to get allowed hours based on weekday
def get_allowed_hours(curr_day):
    key = f"ALLOWED_HOURS_{curr_day}"
    hours = os.getenv(key, "")
    return list(map(int, hours.split(','))) if hours else []

# Helper to send message to a specific channel
async def send_channel_message(message):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(message)

# Start droplet via DO API
def start_droplet():
    url = f"https://api.digitalocean.com/v2/droplets/{DROPLET_ID}/actions"
    headers = {
        "Authorization": f"Bearer {DO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"type": "power_on"}
    requests.post(url, json=data, headers=headers)

# Run SSH command on MC server
def run_ssh_command(command):
    try:
        key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, pkey=key)

        # Uruchom serwer w tle – ważne!
        full_cmd = f"cd {MC_PATH} && nohup {command} > /dev/null 2>&1 &"
        print("FULL CMD:", full_cmd)
        print("MC_PATH:", MC_PATH)
        print("MC_COMMAND:", MC_START_CMD)
        ssh.exec_command(full_cmd)

        ssh.close()
        return "✅ Serwer jest uruchamiany w tle."
    except Exception as e:
        return f"SSH Error: {e}"

# Command: !serverstart
@bot.command()
async def serverstart(ctx):
    try:
        server = JavaServer(MC_SERVER_IP, port=MC_QUERY_PORT)
        status = server.status()
        await ctx.send("⛔ Server is already running.")
        return
    except Exception:
        pass
    curr_hour, curr_day = get_current_local_hour_and_day()
    allowed_hours = get_allowed_hours(curr_day)
    print(f"Alowwed {allowed_hours}")
    if curr_hour not in allowed_hours:
        await ctx.send("⛔ Server can’t be started at this hour.")
        return

    await ctx.send("🟢 Starting Minecraft server...")
    start_droplet()
    await asyncio.sleep(60)  # Wait ~1 min for droplet boot
    output = run_ssh_command(MC_START_CMD)
    await ctx.send(f"✅ Server started.\n```\n{output}\n```")
    subprocess.Popen(["python3", "/root/mc-discord-bot/monitor.py"])

# Command: !serverstop
@bot.command()
async def serverstop(ctx):
    await ctx.send("🛑 Stopping Minecraft server...")
    run_ssh_command("pkill -f fabric-server-launch.jar")

    # Optional: shut down droplet
    requests.post(
        f"https://api.digitalocean.com/v2/droplets/{DROPLET_ID}/actions",
        headers={"Authorization": f"Bearer {DO_API_TOKEN}", "Content-Type": "application/json"},
        json={"type": "shutdown"}
    )
    await ctx.send("💤 Server has been shut down.")

# OPTIONAL: Auto-check empty server logic (scaffold)
@tasks.loop(minutes=5)
async def check_empty_server():
    # You can later implement RCON or query to check player count
    pass

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await send_channel_message("🟢 Bot is online!")

bot.run(DISCORD_TOKEN)

