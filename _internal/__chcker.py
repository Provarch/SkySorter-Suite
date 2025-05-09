import tkinter as tk
from tkinter import messagebox
import requests
import re
import webbrowser
import sys
from pathlib import Path
import json

# Load version information from curr.ver
try:
    script_dir = Path(__file__).parent
    version_file = script_dir / "curr.ver"
    
    with open(version_file, 'r', encoding='utf-8') as f:
        version_data = json.load(f)
    
    try:
        curr_ver = float(version_data["curr_ver"])
    except ValueError as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Invalid version number in 'curr.ver': {version_data['curr_ver']}")
        sys.exit(1)
except FileNotFoundError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", f"Version file 'curr.ver' not found in {script_dir}")
    sys.exit(1)
except (KeyError, json.JSONDecodeError) as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", f"Invalid 'curr.ver' file: {str(e)}")
    sys.exit(1)

# GitHub releases URL for updates
RELEASES_URL = "https://github.com/Provarch/SkySorterPro/releases"

# Popup size (width x height)
POPUP_SIZE = "250x100"

# Button style for popups
button_style = {
    "bg": "#1e1e1e",
    "fg": "white",
    "font": ("Consolas", 10),
    "bd": 0,
    "relief": "flat",
    "activebackground": "#444444",
    "activeforeground": "white"
}

# Offset values for popup positioning
NEW_VERSION_OFFSET_X = -410
NEW_VERSION_OFFSET_Y = 100
UP_TO_DATE_OFFSET_X = -410
UP_TO_DATE_OFFSET_Y = 100

# Popup for "New Version Available" with Update/Cancel options
def show_new_version_popup(latest_ver, dialog_x=None, dialog_y=None):
    new_version_dialog = tk.Toplevel()
    new_version_dialog.overrideredirect(True)
    new_version_dialog.attributes("-topmost", True)
    new_version_dialog.configure(bg="white")
    
    drag_data = {"x": 0, "y": 0, "dragging": False}
    
    if dialog_x is not None and dialog_y is not None:
        new_version_dialog.geometry(f"{POPUP_SIZE}+{dialog_x + NEW_VERSION_OFFSET_X}+{dialog_y + NEW_VERSION_OFFSET_Y}")
    else:
        new_version_dialog.geometry(POPUP_SIZE)
    
    inner_frame = tk.Frame(new_version_dialog, bg="#1e1e1e")
    inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    tk.Label(inner_frame, 
             text=f"New skySorter version {latest_ver} available!", 
             bg="#1e1e1e", fg="white", font=("Consolas", 10), justify="center").pack(pady=5)
    
    button_frame = tk.Frame(inner_frame, bg="#1e1e1e", highlightbackground="white", highlightthickness=2)
    button_frame.pack(pady=5)
    
    def update_action():
        webbrowser.open(RELEASES_URL)
        new_version_dialog.destroy()
    
    def cancel_action():
        new_version_dialog.destroy()
    
    tk.Button(button_frame, text="Update", command=update_action, **button_style).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancel", command=cancel_action, **button_style).pack(side=tk.LEFT, padx=5)
    
    def start_drag(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y
        drag_data["dragging"] = True
    
    def stop_drag(event):
        drag_data["dragging"] = False
    
    def drag(event):
        if drag_data["dragging"]:
            x = new_version_dialog.winfo_x() + (event.x - drag_data["x"])
            y = new_version_dialog.winfo_y() + (event.y - drag_data["y"])
            new_version_dialog.geometry(f"+{x}+{y}")
    
    inner_frame.bind("<Button-1>", start_drag)
    inner_frame.bind("<ButtonRelease-1>", stop_drag)
    inner_frame.bind("<B1-Motion>", drag)

# Popup for errors
def show_error_popup(message, dialog_x=None, dialog_y=None):
    error_dialog = tk.Toplevel()
    error_dialog.overrideredirect(True)
    error_dialog.attributes("-topmost", True)
    
    if dialog_x is not None and dialog_y is not None:
        error_dialog.geometry(f"{POPUP_SIZE}+{dialog_x+133}+{dialog_y+133}")
    else:
        error_dialog.geometry(POPUP_SIZE)
    
    error_dialog.configure(bg="white")
    
    inner_frame = tk.Frame(error_dialog, bg="#1e1e1e")
    inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    tk.Label(inner_frame, 
             text=message, 
             bg="#1e1e1e", fg="white", font=("Consolas", 10), justify="center").pack(pady=10)
    
    button_frame = tk.Frame(inner_frame, bg="#1e1e1e", highlightbackground="white", highlightthickness=2)
    button_frame.pack(pady=5)
    tk.Button(button_frame, text="OK", command=error_dialog.destroy, **button_style).pack()

# Popup for "Up to Date" with dragging
def show_up_to_date_popup(dialog_x=None, dialog_y=None):
    up_to_date_dialog = tk.Toplevel()
    up_to_date_dialog.overrideredirect(True)
    up_to_date_dialog.attributes("-topmost", True)
    up_to_date_dialog.configure(bg="white")
    
    drag_data = {"x": 0, "y": 0, "dragging": False}
    
    if dialog_x is not None and dialog_y is not None:
        up_to_date_dialog.geometry(f"{POPUP_SIZE}+{dialog_x + UP_TO_DATE_OFFSET_X}+{dialog_y + UP_TO_DATE_OFFSET_Y}")
    else:
        up_to_date_dialog.geometry(POPUP_SIZE)
    
    inner_frame = tk.Frame(up_to_date_dialog, bg="#1e1e1e")
    inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
    
    tk.Label(inner_frame, 
             text=f"skySorter is up to date \n (v{curr_ver}).", 
             bg="#1e1e1e", fg="white", font=("Consolas", 10), justify="center").pack(pady=10)
    
    button_frame = tk.Frame(inner_frame, bg="#1e1e1e", highlightbackground="white", highlightthickness=2)
    button_frame.pack(pady=5)
    tk.Button(button_frame, text="OK", command=up_to_date_dialog.destroy, **button_style).pack()
    
    def start_drag(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y
        drag_data["dragging"] = True
    
    def stop_drag(event):
        drag_data["dragging"] = False
    
    def drag(event):
        if drag_data["dragging"]:
            x = up_to_date_dialog.winfo_x() + (event.x - drag_data["x"])
            y = up_to_date_dialog.winfo_y() + (event.y - drag_data["y"])
            up_to_date_dialog.geometry(f"+{x}+{y}")
    
    inner_frame.bind("<Button-1>", start_drag)
    inner_frame.bind("<ButtonRelease-1>", stop_drag)
    inner_frame.bind("<B1-Motion>", drag)

# Version checking function using GitHub API
def check_version(dialog_x=None, dialog_y=None):
    api_url = "https://api.github.com/repos/Provarch/SkySorterPro/contents/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'application/vnd.github+json'}
    
    try:
        # Check repository contents
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        files = response.json()
        
        zip_pattern = r'sspro_upd_v([\d.]+)\.zip'
        latest_ver = None
        
        for file in files:
            if file['type'] == 'file' and file['name'].endswith('.zip'):
                match = re.search(zip_pattern, file['name'])
                if match:
                    try:
                        version = float(match.group(1))
                        if latest_ver is None or version > latest_ver:
                            latest_ver = version
                    except ValueError:
                        continue
        
        # If no zip files found, check releases
        if latest_ver is None:
            releases_url = "https://api.github.com/repos/Provarch/SkySorterPro/releases"
            response = requests.get(releases_url, headers=headers, timeout=10)
            response.raise_for_status()
            releases = response.json()
            
            for release in releases:
                for asset in release.get('assets', []):
                    match = re.search(zip_pattern, asset['name'])
                    if match:
                        try:
                            version = float(match.group(1))
                            if latest_ver is None or version > latest_ver:
                                latest_ver = version
                        except ValueError:
                            continue
        
        if latest_ver is None:
            show_error_popup("No matching zip files found in GitHub repository or releases", dialog_x, dialog_y)
            return
        
        if latest_ver > curr_ver:
            show_new_version_popup(latest_ver, dialog_x, dialog_y)
        else:
            show_up_to_date_popup(dialog_x, dialog_y)
            
    except requests.RequestException as e:
        show_error_popup(f"Error accessing GitHub API: {str(e)}", dialog_x, dialog_y)
    except Exception as e:
        show_error_popup(f"Unexpected error: {str(e)}", dialog_x, dialog_y)

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    dialog_x = int(sys.argv[1]) if len(sys.argv) > 1 else None
    dialog_y = int(sys.argv[2]) if len(sys.argv) > 2 else None
    check_version(dialog_x, dialog_y)
    root.mainloop()
