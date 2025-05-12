import psutil
import os
import subprocess
import pathlib
import json
import re
import time
import zipfile

def get_current_version():
    """Read the current version from curr.ver file."""
    try:
        curr_ver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'curr.ver')
        with open(curr_ver_path, 'r') as f:
            data = json.load(f)
            return data.get('curr_ver', '0.0')
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading curr.ver: {e}")
        return '0.0'

def check_update_zip(curr_ver):
    """Check for update zip file and return its path if version is higher."""
    cwd = os.path.dirname(os.path.abspath(__file__))
    update_zip_path = None
    zip_ver = None
    
    # Look for zip files with '_upd_v' in the name
    for file in os.listdir(cwd):
        if file.lower().endswith('.zip') and '_upd_v' in file.lower():
            # Extract version number from filename (e.g., sspro_upd_v1.13.zip -> 1.13)
            match = re.search(r'_upd_v([\d.]+)\.zip', file.lower())
            if match:
                zip_ver = match.group(1)
                # Compare versions
                if version_compare(zip_ver, curr_ver) > 0:
                    update_zip_path = os.path.join(cwd, file)
                    print(f"Found update package {file} (v{zip_ver}) newer than current version (v{curr_ver})")
                    return update_zip_path, zip_ver
    print("No more recent updater found.")
    return None, None

def unzip_update(zip_path, parent_dir):
    """Unzip the update zip file to the parent directory, overwriting if necessary."""
    if zip_path:
        if not os.path.exists(zip_path):
            print(f"Error: Zip file {zip_path} does not exist.")
            return
        print(f"Extracting to: {parent_dir}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract all files to parent_dir, overwriting existing files
                for member in zip_ref.namelist():
                    # Get the destination path
                    dest_path = os.path.join(parent_dir, member)
                    # Ensure directory structure exists
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    # Extract file, overwriting if it exists
                    with zip_ref.open(member) as source, open(dest_path, 'wb') as target:
                        target.write(source.read())
            print(f"Successfully extracted {os.path.basename(zip_path)} to {parent_dir}")
        except (zipfile.BadZipFile, OSError) as e:
            print(f"Failed to extract {os.path.basename(zip_path)}: {e}")

def version_compare(v1, v2):
    """Compare two version strings (e.g., '1.13' > '1.11')."""
    v1_parts = list(map(int, v1.split('.')))
    v2_parts = list(map(int, v2.split('.')))
    
    # Pad with zeros if lengths differ
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    for i in range(max_len):
        if v1_parts[i] > v2_parts[i]:
            return 1
        elif v1_parts[i] < v2_parts[i]:
            return -1
    return 0

def get_script_parent_directory():
    """Get the parent directory of the current script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = str(pathlib.Path(script_dir).parent)
    return parent_dir

def get_python_processes(script_parent_dir):
    """Get Python processes running from the parent directory, excluding __updater.py."""
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'cwd']):
        try:
            if proc.info['name'].lower() in ['python.exe', 'pythonw.exe']:
                cmdline = proc.info['cmdline'] if proc.info['cmdline'] else []
                cmdline_str = ' '.join(cmdline)
                
                if '__updater.py' in cmdline_str.lower():
                    continue
                
                try:
                    process_cwd = proc.info['cwd'].lower()
                    if process_cwd.startswith(script_parent_dir.lower()):
                        process_info = {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'directory': None,
                            'cmdline': cmdline,
                            'cmdline_str': cmdline_str,
                            'cwd': process_cwd
                        }
                        
                        try:
                            process_info['directory'] = os.path.dirname(proc.exe())
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            process_info['directory'] = 'Access Denied'
                        
                        python_processes.append(process_info)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return python_processes

def close_processes(processes):
    """Prompt to close processes and return closed ones."""
    if not processes:
        return []
    
    response = input("\nDo you want to close these processes? (y/n): ").strip().lower()
    closed_processes = []
    
    if response == 'y':
        for proc in processes:
            try:
                psutil.Process(proc['pid']).terminate()
                print(f"Terminated process {proc['name']} (PID: {proc['pid']})")
                closed_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Failed to terminate process {proc['name']} (PID: {proc['pid']}): {e}")
        # Wait briefly to ensure processes are fully terminated
        time.sleep(1)
    else:
        print("No processes were closed.")
    
    return closed_processes

def relaunch_processes(closed_processes):
    """Prompt to relaunch closed processes."""
    if not closed_processes:
        return
    
    response = input("\nDo you want to relaunch the closed processes? (y/n): ").strip().lower()
    if response == 'y':
        for proc in closed_processes:
            try:
                subprocess.Popen(proc['cmdline'], creationflags=subprocess.DETACHED_PROCESS)
                print(f"Relaunched process with command: {' '.join(proc['cmdline'])}")
            except Exception as e:
                print(f"Failed to relaunch process with command {' '.join(proc['cmdline'])}: {e}")
    else:
        print("No processes were relaunched.")

def main():
    # Get current version
    curr_ver = get_current_version()
    print(f"Current version: {curr_ver}")
    
    # Get parent directory
    script_parent_dir = get_script_parent_directory()
    print(f"\nDetecting running Python processes in parent directory: {script_parent_dir} (excluding '__updater.py')...\n")
    
    # Get list of Python processes
    processes = get_python_processes(script_parent_dir)
    
    if not processes:
        print("No matching Python processes found.")
    
    # Print details for each process
    for proc in processes:
        print(f"Process: {proc['name']}")
        print(f"PID: {proc['pid']}")
        print(f"Executable Directory: {proc['directory']}")
        print(f"Working Directory: {proc['cwd']}")
        print(f"Command Line: {proc['cmdline_str']}")
        print("-" * 50)
    
    # Check for update zip
    update_zip_path, zip_ver = check_update_zip(curr_ver)
    
    # If no newer update, wait for user input to exit
    if not update_zip_path:
        input("\nPress Enter to exit...")
        return
    
    # If newer update found, proceed with closing processes
    closed_processes = close_processes(processes)
    
    # Unzip update to parent directory
    unzip_update(update_zip_path, script_parent_dir)
    
    # Relaunch processes/eth
    relaunch_processes(closed_processes)

if __name__ == "__main__":
    main()
