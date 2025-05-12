import requests
import re
import json
import sys
import shutil
from pathlib import Path
import tkinter as tk

# ---------------- CONFIG ---------------- #
REPO_API_URL = "https://api.github.com/repos/Provarch/SkySorter-Suite/contents?ref=main"
ZIP_PATTERN = r"sspro_upd_v([\d.]+)\.zip"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/vnd.github+json"
}
POPUP_SIZE = "300x120"
# ---------------------------------------- #

# Button style
button_style = {
    "bg": "#1e1e1e",
    "fg": "white",
    "font": ("Consolas", 10),
    "bd": 0,
    "relief": "flat",
    "activebackground": "#444444",
    "activeforeground": "white"
}

def get_current_version(ver_file):
    try:
        with open(ver_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return float(data["curr_ver"])
    except Exception as e:
        print(f"Error reading version file: {e}")
        sys.exit(1)

def show_custom_popup(latest_ver, zip_url, local_path):
    root = tk.Tk()
    root.withdraw()  # Hide root

    popup = tk.Toplevel()
    popup.title("Update Available")
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg="white")
    popup.geometry(POPUP_SIZE)

    drag_data = {"x": 0, "y": 0, "dragging": False}

    frame = tk.Frame(popup, bg="#1e1e1e")
    frame.pack(fill="both", expand=True, padx=2, pady=2)

    tk.Label(frame, text=f"Update v{latest_ver} available!", bg="#1e1e1e", fg="white",
             font=("Consolas", 10)).pack(pady=10)

    btn_frame = tk.Frame(frame, bg="#1e1e1e")
    btn_frame.pack()

    def update_action():
        try:
            with requests.get(zip_url, stream=True, timeout=15) as r:
                r.raise_for_status()
                with open(local_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            print(f"Downloaded update to: {local_path}")
        except Exception as e:
            print(f"Download failed: {e}")
        popup.destroy()
        root.quit()

    def cancel_action():
        print("Update cancelled.")
        popup.destroy()
        root.quit()

    tk.Button(btn_frame, text="Update", command=update_action, **button_style).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=cancel_action, **button_style).pack(side=tk.LEFT, padx=5)

    def start_drag(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y
        drag_data["dragging"] = True

    def stop_drag(event):
        drag_data["dragging"] = False

    def drag(event):
        if drag_data["dragging"]:
            x = popup.winfo_x() + (event.x - drag_data["x"])
            y = popup.winfo_y() + (event.y - drag_data["y"])
            popup.geometry(f"+{x}+{y}")

    frame.bind("<Button-1>", start_drag)
    frame.bind("<ButtonRelease-1>", stop_drag)
    frame.bind("<B1-Motion>", drag)

    root.mainloop()

def check_for_updates():
    script_dir = Path(__file__).parent
    version_file = script_dir / "curr.ver"
    curr_ver = get_current_version(version_file)

    try:
        response = requests.get(REPO_API_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        files = response.json()

        latest_ver = None
        latest_zip_name = None

        for file in files:
            if file['type'] == 'file' and file['name'].endswith('.zip'):
                match = re.match(ZIP_PATTERN, file['name'])
                if match:
                    try:
                        version = float(match.group(1))
                        if latest_ver is None or version > latest_ver:
                            latest_ver = version
                            latest_zip_name = file['name']
                    except ValueError:
                        continue

        if latest_ver is None:
            print("No update ZIPs found.")
            return

        if latest_ver > curr_ver:
            raw_url = f"https://raw.githubusercontent.com/Provarch/SkySorter-Suite/main/{latest_zip_name}"
            local_path = script_dir / latest_zip_name
            show_custom_popup(latest_ver, raw_url, local_path)
        else:
            print(f"You are up to date. (v{curr_ver})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_for_updates()
