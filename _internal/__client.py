import os
import socket
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import imagehash
from PIL import Image
import platform
import uuid
from pathlib import Path
import hashlib
import time
from __process_cmd import process_cmd
from __get_contents import get_archive_contents
from __bridge import start_bridge, is_bridge_running
import subprocess

# Supported archive and image extensions
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# TCP socket settings
HOST = "127.0.0.1"
PORT = 8888
TIMEOUT = 20

def check_bridge_status() -> Tuple[bool, bool]:
    """Check if a bridge is running and fully operational by sending a test message."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Short timeout for initial check
            s.connect((HOST, PORT))
            # Send a test message to query status
            s.send("bridge_status_check".encode())
            response = s.recv(1024).decode()
            if response == "bridge_ready_with_channel":
                print("✅ Bridge is running and has an assigned channel.")
                return True, True  # Running and ready
            elif response == "bridge_running_not_ready":
                print("ℹ️ Bridge is running but not yet assigned a channel.")
                return True, False  # Running but not ready
            else:
                print(f"⚠️ Unexpected bridge response: {response}")
                return False, False
    except ConnectionRefusedError:
        #print("ℹ️ No bridge detected at {HOST}:{PORT}.")
        return False, False
    except Exception as e:
        print(f"⚠️ Error checking bridge status: {e}")
        return False, False

def ensure_bridge_ready(timeout_seconds: int = 30):
    """Ensure a bridge is running and fully operational, starting one if necessary."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        is_running, is_ready = check_bridge_status()
        if is_running and is_ready:
            return True
        elif not is_running:
            print()
            print("Starting a new bridge instance...")
            if not start_bridge():
                print("❌ Failed to start bridge.")
                return False
            time.sleep(3)  # Give bridge time to start
        else:  # Running but not ready
            print("Waiting for bridge to become fully operational...")
            time.sleep(1)
    print(f"❌ Bridge did not become fully operational within {timeout_seconds} seconds.")
    return False

def get_script_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

# Define CREATE_NO_WINDOW for Windows to suppress console windows
CREATE_NO_WINDOW = 0x08000000

def generate_uid() -> str:
    """Generate a 16-character hashed ID."""
    # Try WMIC first
    try:
        result = subprocess.check_output(
            ["wmic", "cpu", "get", "ProcessorId"],
            universal_newlines=True,
            creationflags=CREATE_NO_WINDOW
        )
        cpu_id = result.strip().split("\n")[-1].strip()
        if not cpu_id:
            raise ValueError("Empty hashed ID source returned")
        hashed_id = hashlib.sha256(cpu_id.encode()).hexdigest()
        return hashed_id[:16]
    except Exception as e:
        print(f"⚠️ WMIC failed: {e}. Falling back to PowerShell.")

    # Try PowerShell
    try:
        result = subprocess.check_output(
            ["powershell", "-Command", "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty ProcessorId"],
            universal_newlines=True,
            creationflags=CREATE_NO_WINDOW
        )
        cpu_id = result.strip()
        if not cpu_id:
            raise ValueError("Empty ProcessorId returned from PowerShell")
        hashed_id = hashlib.sha256(cpu_id.encode()).hexdigest()
        return hashed_id[:16]
    except Exception as e:
        print(f"⚠️ PowerShell failed: {e}. Falling back to UUID-based ID.")

    # Fallback to UUID-based ID
    unique_id = str(uuid.uuid4()).replace("-", "")
    hashed_id = hashlib.sha256(unique_id.encode()).hexdigest()
    return hashed_id[:16]

def find_model_files(file_path: Path) -> Tuple[Optional[Path], List[Path]]:
    """Find corresponding model_archive and all related model_preview files with numeric suffixes."""
    if file_path.suffix.lower() in ARCHIVE_EXTENSIONS:
        model_archive = file_path
        base_name = model_archive.stem
        model_previews = []
        
        for ext in IMAGE_EXTENSIONS:
            preview = file_path.with_suffix(ext)
            if preview.exists():
                model_previews.append(preview)
            
            for i in range(10):
                numbered_preview = model_archive.parent / f"{base_name} {i}{ext}"
                if numbered_preview.exists():
                    model_previews.append(numbered_preview)
        
        return model_archive, model_previews if model_previews else []
    
    elif file_path.suffix.lower() in IMAGE_EXTENSIONS:
        model_preview = file_path
        base_name = model_preview.stem
        model_previews = [model_preview]
        
        base_match = re.match(r'^(.*?)(\s+\d+)?$', base_name)
        if base_match:
            base_name = base_match.group(1)
        
        for ext in ARCHIVE_EXTENSIONS:
            model_archive = model_preview.parent / f"{base_name}{ext}"
            if model_archive.exists():
                for img_ext in IMAGE_EXTENSIONS:
                    for i in range(10):
                        numbered_preview = model_archive.parent / f"{base_name} {i}{img_ext}"
                        if numbered_preview.exists() and numbered_preview not in model_previews:
                            model_previews.append(numbered_preview)
                return model_archive, model_previews
        return None, model_previews
    
    return None, []

def send_to_server(client_socket: socket.socket, model_archive: Path, model_ids: List[Optional[str]], model_hashes: List[Optional[str]], uid: str, task_number: str) -> Tuple[Optional[str], Optional[str]]:
    """Send uid, task_number, model_ids, and multiple model_hashes to the server via TCP socket and wait for matching response."""
    # Initial formatting with all model_ids and model_hashes
    model_ids_to_send = model_ids if model_ids else []
    model_hashes_to_send = model_hashes if model_hashes else []
    
    model_ids_str = ','.join(model_ids_to_send) if model_ids_to_send else 'none'
    model_hashes_str = ','.join(model_hashes_to_send) if model_hashes_to_send else 'none'
    message = f"uid:{uid}:task:{task_number}:model_ids={model_ids_str}|model_hashes={model_hashes_str}"
    
    # Check if message exceeds Discord's 2000-character limit
    if len(message) > 2000:
        print(f"⚠️ Warning: Initial message exceeds Discord limit (2000 chars): {len(message)} chars. Reducing to 2 model_ids and 2 hashes.")
        model_ids_to_send = model_ids[:2] if model_ids else []
        model_hashes_to_send = model_hashes[:2] if model_hashes else []
        
        model_ids_str = ','.join(model_ids_to_send) if model_ids_to_send else 'none'
        model_hashes_str = ','.join(model_hashes_to_send) if model_hashes_to_send else 'none'
        message = f"uid:{uid}:task:{task_number}:model_ids={model_ids_str}|model_hashes={model_hashes_str}"
        
        if len(message) > 2000:
            print(f"⚠️ Warning: Reduced message still exceeds 2000 chars ({len(message)}). Sending minimal data.")
            model_ids_str = model_ids[0] if model_ids else 'none'
            model_hashes_str = model_hashes[0] if model_hashes else 'none'
            message = f"uid:{uid}:task:{task_number}:model_ids={model_ids_str}|model_hashes={model_hashes_str}"

    try:
        #print(f"Sending to bridge: {message}")
        client_socket.send(message.encode())
    except Exception as e:
        print(f"❌ Error sending to bridge: {e}")
        return None, None
    
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        try:
            response = client_socket.recv(4096).decode()
            if not response:
                print("Connection closed by bridge.")
                return None, None
            
            expected_prefix = f"uid:{uid}:"
            if response.startswith(expected_prefix):
                if response.startswith(f"{expected_prefix}task:{task_number}:cmd:"):
                    exif_cmd = response.split(f"{expected_prefix}task:{task_number}:cmd:", 1)[1]
                    return None, exif_cmd
                elif response.startswith(f"{expected_prefix}task:{task_number}:error:limit_exceeded"):
                    print(f"❌ Usage limit exceeded: No further tasks will be sent to the bridge.")
                    return "limit_exceeded", None
                elif response.startswith(f"{expected_prefix}task:{task_number}:error:"):
                    print(f"⚠️ Server error response: {response}")
                    return None, None
                elif response.startswith(f"{expected_prefix}msg:"):
                    return response, None
                else:
                    print(f"⚠️ Unexpected response format for task {task_number}: {response}")
                    return None, None
            elif response == "received":
                continue
            else:
                print(f"⚠️ Ignoring response for different task: {response}")
                continue
        except socket.timeout:
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
            return None, None
    
    print(f"⚠️ Timeout: No matching cmd response received within {TIMEOUT} seconds for uid:{uid}:task:{task_number}")
    return None, None

def query_usage_limit(client_socket: socket.socket, uid: str, alias: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Query the user's usage limit from the server, using alias if provided."""
    query_message = f"uid:{uid}:task:chck:{alias if alias else 'none'}"
    task_id = "chck"
    
    try:
        client_socket.send(query_message.encode())
    except Exception as e:
        print(f"❌ Error sending usage query to bridge: {e}")
        return True, None
    
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        try:
            response = client_socket.recv(4096).decode()
            if not response:
                print("Connection closed by bridge.")
                return True, None
            
            expected_prefix = f"uid:{uid}:"
            if response.startswith(expected_prefix):
                if response.startswith(f"{expected_prefix}msg:"):
                    print(f"Received limit response: {response}")
                    if "Limit exceeded" in response or "error:limit_exceeded" in response:
                        return False, response
                    return True, response
                elif response.startswith(f"{expected_prefix}task:{task_id}:error:limit_exceeded"):
                    print(f"❌ Usage limit exceeded: {response}")
                    return False, response
                elif response.startswith(f"{expected_prefix}task:{task_id}:error:"):
                    print(f"⚠️ Server error response: {response}")
                    return True, None
                else:
                    print(f"⚠️ Unexpected response format for task {task_id}: {response}")
                    continue
            elif response == "received":
                continue
            else:
                print(f"⚠️ Ignoring response for different task: {response}")
                continue
        except socket.timeout:
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
            return True, None
    
    print(f"⚠️ Timeout: No matching response received within {TIMEOUT} seconds for uid:{uid}:task:{task_id}")
    return True, None
    
    print(f"⚠️ Timeout: No matching response received within {TIMEOUT} seconds for uid:{uid}:task:{task_id}")
    return True, None

def process_source_folder(source_folder: str, destination_folder: str = None, alias: str = None, max_preview_hashes: int = 3):
    """Process archives in the source folder and send requests to the bridge.
    
    Args:
        source_folder: Source directory containing model archives
        destination_folder: Optional destination directory
        max_preview_hashes: Maximum number of preview hashes to generate (default: 3)
    """
    source_path = Path(source_folder)
    dest_path = Path(destination_folder) if destination_folder else source_path
    
    if not source_path.exists() or not source_path.is_dir():
        print(f"❌ Error: Invalid source folder: {source_folder}")
        return
    if destination_folder and (not dest_path.exists() or not dest_path.is_dir()):
        print(f"❌ Error: Invalid destination folder: {destination_folder}")
        return

    print(f"✅ Processing source folder: {source_folder}")
    if destination_folder:
        print(f"✅ Destination folder: {destination_folder}")

    if alias:
        print(f"✅ Using alias: {alias}")
    uid = generate_uid()
    task_number = 0

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
        client.settimeout(TIMEOUT)
        #print(f"Connected to bridge at {HOST}:{PORT}")
    except ConnectionRefusedError:
        print("❌ Error: Bridge is not running. Please start __bridge.py first.")
        return

    # Query usage limit
    can_proceed, limit_response = query_usage_limit(client, uid, alias)
    if not can_proceed:
        print(f"❌ Aborting: {limit_response}")
        client.close()
        return
    if limit_response:
        print(f"Usage limit: {limit_response}")

    files = sorted([f for f in source_path.iterdir() if f.suffix.lower() in ARCHIVE_EXTENSIONS])
    file_index = 0

    while file_index < len(files):
        file_path = files[file_index]
        print(f"--------------------------------------------------------------------")
        print(f"Working on {file_path}")

        model_archive, model_previews = find_model_files(file_path)
        if not model_archive:
            file_index += 1
            continue

        # Get model IDs
        model_ids = []
        archive_basename = model_archive.stem
        filename_match = re.compile(r'\b(\d{3,8}\.\w{12,13})').search(archive_basename)
        if filename_match:
            model_ids.append(filename_match.group(0))

        contents, corrected_path_str = get_archive_contents(str(model_archive))
        model_archive = Path(corrected_path_str)
        if contents:
            for content in contents:
                content_match = re.compile(r'\b(\d{3,8}\.\w{12,13})').search(content)
                if content_match:
                    model_id = content_match.group(0)
                    if model_id not in model_ids:
                        model_ids.append(model_id)

        # Get model hashes from previews
        model_hashes = []
        main_preview = None
        if model_previews:
            sorted_previews = sorted(model_previews, 
                                   key=lambda p: int(re.search(r'(\d+)$', p.stem).group(1) 
                                                   if re.search(r'(\d+)$', p.stem) else '-1'))
            main_preview = sorted_previews[0]
            
            available_previews = len(sorted_previews)
            previews_to_process = min(max_preview_hashes, available_previews)
            
            for preview in sorted_previews[:previews_to_process]:
                if preview.exists():
                    try:
                        with Image.open(preview) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            phash = str(imagehash.phash(img, hash_size=16))
                            dhash = str(imagehash.dhash(img, hash_size=16))
                            model_hashes.append(f"{phash}_{dhash}")
                    except Exception as e:
                        print(f"⚠️ Error generating hash from preview {preview}: {e}")

        model_hash = model_hashes[0] if model_hashes else None

        if not model_ids and not model_hashes:
            print(f"⚠️ No model IDs or hashes found for {model_archive}. Skipping.")
            file_index += 1
            continue

        task_str = f"{task_number:03d}"
        # Send both model_ids and all collected model_hashes
        response, exif_cmd = send_to_server(client, model_archive, model_ids, model_hashes, uid, task_str)
        
        if response == "limit_exceeded":
            client.close()            
            return
        elif exif_cmd:
            try:
                valid_id, valid_prv_path, full_cmd, exif_result = process_cmd(exif_cmd, source_path, model_archive, model_previews, dest_path)
                if valid_id:
                    if valid_prv_path is None and full_cmd is None and exif_result is None:
                        print(f"  ℹ️ Duplicate Model detected for {valid_id}. Files moved to __duplicates folder.")
                    elif full_cmd and exif_result:
                        print(f"  ✅ Processed {valid_id} successfully.")
                    else:
                        print(f"  ⚠️ Failed to process {valid_id}: Could not execute EXIF command or generate full command.")
                else:
                    print("  ⚠️ Could not extract valid_id from exif_cmd.")
            except Exception as e:
                print(f"❌ Error processing {model_archive}: {e}. Skipping to next file.")
            file_index += 1
            task_number += 1
        else:
            print("  ⚠️ No valid cmd response received for this task.")
            file_index += 1
            task_number += 1

            
    # Query usage limit at the end
    can_proceed, limit_response = query_usage_limit(client, uid, alias)
    if limit_response:
        print(f"Final usage limit: {limit_response}")
    else:
        print("⚠️ No final limit response received.")

    client.close()
    print("✅ Finished processing source folder.")

if __name__ == "__main__":
    # Replace the original bridge check with the new logic
    if not ensure_bridge_ready():
        print("❌ Aborting: Could not ensure a fully operational bridge.")
        sys.exit(1)

    if len(sys.argv) == 1:  # No arguments
        source_folder = input("Enter source folder path: ").strip()
        process_source_folder(source_folder)
    elif len(sys.argv) == 2:  # One argument (source or alias)
        arg = sys.argv[1]
        if '\\' in arg or '/' in arg:  # Check for path separators
            source_folder = arg
            process_source_folder(source_folder)
        else:
            alias = arg
            source_folder = input("Enter source folder path: ").strip()
            process_source_folder(source_folder, alias=alias)
    elif len(sys.argv) == 3:  # Two arguments (source and destination, or source and alias)
        arg1, arg2 = sys.argv[1], sys.argv[2]
        if '\\' in arg2 or '/' in arg2:  # Second arg is a path
            source_folder, destination_folder = arg1, arg2
            process_source_folder(source_folder, destination_folder)
        else:  # Second arg is an alias
            source_folder, alias = arg1, arg2
            process_source_folder(source_folder, alias=alias)
    elif len(sys.argv) == 4:  # Three arguments (source, destination, alias)
        source_folder, destination_folder, alias = sys.argv[1], sys.argv[2], sys.argv[3]
        process_source_folder(source_folder, destination_folder, alias)
    else:
        print("❌ Usage: client.py [source_folder] [destination_folder (optional)] [alias (optional)]")
        sys.exit(1)
