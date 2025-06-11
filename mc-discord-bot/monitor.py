import os
import asyncio
import paramiko
import discord
from mcstatus import JavaServer
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

load_dotenv()

# DISCORD
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# DIGITALOCEAN
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

# MINECRAFT
MC_SERVER_IP = os.getenv("MC_SERVER_IP")
MC_QUERY_PORT = int(os.getenv("MC_QUERY_PORT", "25565"))
MC_PATH = os.getenv("MC_PATH")
MC_STOP_CMD = f"screen -S mc -X stuff 'stop\\n'"

# TIMEZONE
TIMEZONE = os.getenv("TIMEZONE")

# State
no_players_for = 0
CHECK_INTERVAL = 60  # seconds
SHUTDOWN_AFTER = 300  # 5 minutes

allowed_hours= {}
for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]:
    s = os.getenv(f"ALLOWED_HOURS_{day}", "")
    allowed_hours[day] = [int(h) for h in s.split(",") if h.strip().isdigit()]

def get_current_hour():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%a").upper(), now.hour, now.minute

def is_within_allowed_hours():
    weekday, hour, _ = get_current_hour()
    return hour in allowed_hours.get(weekday, [])

async def send_discord_message(message):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            await channel.send(message)
            print(f"[Monitor] Discord message sent: {message}")
        else:
            print(f"[Monitor] Channel ID {DISCORD_CHANNEL_ID} not found.")
        await client.close()

    await client.start(DISCORD_TOKEN)

def run_ssh_command(command, use_mc_path=True):
    try:
        print(f"[Monitor] Running SSH command: {command}")
        key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, username=SSH_USER, pkey=key)

        full_cmd = f"cd {MC_PATH} && {command}" if use_mc_path else command
        stdin, stdout, stderr = ssh.exec_command(full_cmd)

        output = stdout.read().decode()
        error = stderr.read().decode()
        ssh.close()

        if output:
            print(f"[Monitor][SSH Output]: {output.strip()}")
        if error:
            print(f"[Monitor][SSH Error]: {error.strip()}")

        return output.strip()
    except Exception as e:
        print(f"[Monitor] SSH Error: {e}")
        return ""

async def monitor_loop():
    print("[Monitor] Waiting 60 seconds for Minecraft server to boot...")
    await asyncio.sleep(60)

    global no_players_for
    no_players_for = 0
    warned_about_shutdown = False

    server = JavaServer(MC_SERVER_IP, port=MC_QUERY_PORT)

    while True:
        try:
            # Check server status
            status = server.status()
            players = status.players.online
            print(f"[Monitor] Players online: {players}")

            if players == 0:
                no_players_for += CHECK_INTERVAL
            else:
                no_players_for = 0

            # Shutdown if no players for SHUTDOWN_AFTER
            if no_players_for >= SHUTDOWN_AFTER:
                print("[Monitor] No players for 5 minutes, shutting down server...")
                await send_discord_message("⚠️ No players detected. Server shutting down.")
                run_ssh_command(MC_STOP_CMD, use_mc_path=True)
                run_ssh_command("poweroff", use_mc_path=False)
                no_players_for = 0
                warned_about_shutdown = False
                await asyncio.sleep(300)
                continue

            # Time-based shutdown warning
            weekday, hour, minute = get_current_hour()
            if not is_within_allowed_hours():
                if not warned_about_shutdown and minute >= 50:
                    await send_discord_message("⚠️ Server will shut down in 10 minutes (end of scheduled hours).")
                    warned_about_shutdown = True
                elif minute == 0 and warned_about_shutdown:
                    print("[Monitor] Outside allowed hours. Shutting down.")
                    await send_discord_message("⏰ Server shutting down (outside allowed hours).")
                    run_ssh_command(MC_STOP_CMD, use_mc_path=True)
                    run_ssh_command("poweroff", use_mc_path=False)
                    no_players_for = 0
                    warned_about_shutdown = False
                    await asyncio.sleep(300)
                    continue
            else:
                warned_about_shutdown = False

        except Exception as e:
            print(f"[Monitor] Error checking server status: {e}")
            no_players_for = 0

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(monitor_loop())

