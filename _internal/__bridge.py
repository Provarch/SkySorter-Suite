import socket
import asyncio
import discord
import requests
from discord import Intents
import threading
import sys
import os
import configparser
from pathlib import Path
import time
import subprocess
import logging

# TCP server settings
HOST = "127.0.0.1"
PORT = 8888
INACTIVITY_TIMEOUT = 60

# Authorized server bot
AUTHORIZED_SERVER_BOT = "cmd-bot#0942"
AUTHORIZED_ENTITIES = {"cmd-bot#0942", "provarch"}

def get_script_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def setup_logging():
    """Set up logging to a file when running as a subprocess, or to stdout when standalone."""
    script_dir = get_script_directory()
    log_dir = Path(script_dir) / "_internal" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bridge.log"

    # Check if running as a subprocess (e.g., started by __client.py)
    is_subprocess = os.getppid() != os.getpid()  # Approximate check for subprocess

    logger = logging.getLogger('Bridge')
    logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicate logs
    logger.handlers.clear()

    if is_subprocess:
        # Log to file when running as a subprocess
        handler = logging.FileHandler(log_file, encoding='utf-8')
    else:
        # Log to stdout when running standalone
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    # Replace print with logger.info
    def log_print(*args, **kwargs):
        logger.info(' '.join(map(str, args)))

    # Override print globally for this module
    global print
    print = log_print

def load_config():
    file_id = "1wSUvcjljzQtSMMropOj6uGsoemLudz7I"
    try:
        metadata_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        response = requests.head(metadata_url, allow_redirects=True)
        content_disp = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[1].split(';')[0].strip('"\'')
            config_value = os.path.splitext(filename)[0]
            if not config_value:
                raise ValueError("Configuration value is empty")
            return config_value.strip()
        else:
            metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name&key=AIzaSyDtgx"
            response = requests.get(metadata_url)
            if response.status_code == 200:
                data = response.json()
                filename = data.get('name', '')
                config_value = os.path.splitext(filename)[0]
                return config_value.strip()
            else:
                raise ValueError("Could not retrieve filename from Google Drive")
    except Exception as e:
        print(f"Error retrieving configuration: {e}")
        sys.exit(1)

def is_bridge_running():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect((HOST, PORT))
            s.send("bridge_status".encode())
            response = s.recv(1024).decode()
            return response == "bridge_ready"
    except:
        return False

def start_bridge():
    if not is_bridge_running():
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())])
        for _ in range(30):
            if is_bridge_running():
                return True
            time.sleep(1)
        return False
    return True

class BridgeBot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        self.allowed_channels = []
        self.selected_channel = None
        self.queue = asyncio.Queue()
        self.is_ready = False
        self.tcp_clients = {}
        self.pending_tasks = {}
        self.uid = f"bridge_{os.getpid()}"
        self.channel_assigned = asyncio.Event()
        self.last_activity = time.time()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.fetch_allowed_channels()
        if not self.allowed_channels:
            print("Error: No channels available to send messages to.")
            await self.close()
            sys.exit(1)
        temp_channel = self.allowed_channels[0]
        request = f"uid:bridge_request:get_free_channel:{self.uid}"
        await temp_channel.send(request)
        await self.channel_assigned.wait()
        print(f"Selected channel for this session: {self.selected_channel.name} (ID: {self.selected_channel.id})")
        self.is_ready = True
        await self.process_queue()

    async def fetch_allowed_channels(self):
        for guild in self.guilds:
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages and permissions.view_channel:
                    self.allowed_channels.append(channel)

    async def process_queue(self):
        while True:
            message, client_addr = await self.queue.get()
            if self.selected_channel and self.is_ready:
                if message.startswith("uid:"):
                    uid = message.split(":", 2)[1]
                    task_number = message.split(":", 4)[3]
                    task_key = f"{uid}:{task_number}"
                    self.pending_tasks[task_key] = client_addr
                await self.selected_channel.send(message)
            self.queue.task_done()

    async def on_message(self, message):
        if message.author == self.user:
            return
        data = message.content
        print(f"Received Discord message: {data}")
        if data.startswith("uid:server:assign_channel:"):
            try:
                parts = data.split(":", 4)
                if len(parts) != 5 or parts[3] != self.uid:
                    return
                channel_id = int(parts[4])
                for channel in self.allowed_channels:
                    if channel.id == channel_id:
                        self.selected_channel = channel
                        self.channel_assigned.set()
                        print(f"Assigned channel by server: {channel.name} (ID: {channel_id})")
                        return
                print(f"Error: Assigned channel ID {channel_id} not in allowed channels")
            except Exception as e:
                print(f"Error processing channel assignment: {e}")
        if message.channel == self.selected_channel and data.startswith("uid:"):
            if str(message.author) not in AUTHORIZED_ENTITIES:
                print(f"Ignoring message from unauthorized bot/user: {message.author}")
                return
            try:
                parts = data.split(":", 4)
                if len(parts) < 4:
                    print(f"Message format incorrect, expected at least 'uid:SENDER:ACTION:CONTENT', got: {data}")
                    return
                uid = parts[1]
                action = parts[2]
                content = parts[3] if len(parts) > 3 else ""
                if action == "msg":
                    # Try matching with task:chck, task:start, or generic task
                    possible_keys = [f"{uid}:chck", f"{uid}:start", f"{uid}:task"]
                    task_key = None
                    for key in possible_keys:
                        if key in self.pending_tasks:
                            task_key = key
                            break
                    if not task_key:
                        print(f"No pending task found for msg with possible keys: {possible_keys}")
                        return
                elif action == "task":
                    task_key = f"{uid}:{content}"
                else:
                    print(f"Unsupported action: {action}")
                    return
                if task_key in self.pending_tasks:
                    client_addr = self.pending_tasks[task_key]
                    if client_addr in self.tcp_clients:
                        client = self.tcp_clients[client_addr]
                        try:
                            print(f"Relaying message to TCP client at {client_addr}: {data}")
                            client.send(data.encode())
                        except Exception as e:
                            print(f"Error sending response to TCP client at {client_addr}: {e}")
                        finally:
                            if action == "task":
                                del self.pending_tasks[task_key]
                    else:
                        print(f"TCP client {client_addr} not found for task {task_key}")
                else:
                    print(f"No pending task found with key: {task_key}")
            except Exception as e:
                print(f"Error processing Discord message: {e}")

def tcp_server(bot_instance):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(1)
    print(f"TCP server listening on {HOST}:{PORT}")
    while True:
        try:
            client, addr = server.accept()
            print(f"Connection from {addr}")
            bot_instance.tcp_clients[addr] = client
            bot_instance.last_activity = time.time()
            try:
                while True:
                    data = client.recv(4096).decode()
                    if not data:
                        break
                    bot_instance.last_activity = time.time()
                    if data == "bridge_restart":
                        client.send("bridge_alive".encode())
                        print(f"Responded to bridge_restart from {addr} with bridge_alive")
                    elif data == "bridge_shutdown":
                        print(f"Received shutdown command from {addr}. Shutting down...")
                        client.send("bridge_closing".encode())
                        client.close()  # Explicitly close the client socket
                        os._exit(0)
                    elif data == "bridge_status":
                        if bot_instance.is_ready:
                            client.send("bridge_ready".encode())
                        else:
                            client.send("bridge_not_ready".encode())
                    elif data == "bridge_status_check":
                        if bot_instance.is_ready and bot_instance.selected_channel:
                            client.send("bridge_ready_with_channel".encode())
                        else:
                            client.send("bridge_running_not_ready".encode())
                    elif data == "say_hello":
                        client.send("hello".encode())
                        print(f"Responded to say_hello from {addr} with 'hello'")
                    else:
                        if data.startswith("uid:"):
                            parts = data.split(":", 4)
                            if len(parts) >= 4:
                                uid = parts[1]
                                action = parts[2]
                                task_number = parts[3] if len(parts) > 3 else ""
                                # Use uid:task for 'start' tasks to match msg responses
                                if action == "task" and task_number == "start":
                                    task_key = f"{uid}:task"
                                else:
                                    task_key = f"{uid}:{task_number}" if action == "task" else f"{uid}:task"
                                bot_instance.pending_tasks[task_key] = addr
                        asyncio.run_coroutine_threadsafe(bot_instance.queue.put((data, addr)), bot_instance.loop)
                        client.send("received".encode())
            except ConnectionError as e:
                if str(e).find("10054") == -1:  # Ignore WinError 10054
                    print(f"Connection error with client {addr}: {e}")
            except Exception as e:
                print(f"Error in TCP server: {e}")
            finally:
                if addr in bot_instance.tcp_clients:
                    del bot_instance.tcp_clients[addr]
                client.close()
                
        except socket.timeout:
            if time.time() - bot_instance.last_activity > INACTIVITY_TIMEOUT:
                print(f"No TCP activity for {INACTIVITY_TIMEOUT} seconds. Shutting down...")
                os._exit(0)
        except Exception as e:
            print(f"Error in TCP server: {e}")
            break

async def main():
    # setup_logging()  # Commented out to disable log creation
    CONFIG_VALUE = load_config()
    intents = Intents.default()
    intents.messages = True
    intents.message_content = True
    bot = BridgeBot(intents=intents)
    tcp_thread = threading.Thread(target=tcp_server, args=(bot,), daemon=True)
    tcp_thread.start()
    await bot.start(CONFIG_VALUE)

if __name__ == "__main__":
    asyncio.run(main())
