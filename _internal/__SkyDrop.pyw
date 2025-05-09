import tkinter as tk
from tkinterdnd2 import *
import os
import re
import pyexiv2
import webbrowser
import shutil
from PIL import Image, ImageTk
import time
import threading
import piexif

# Set the working directory to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Import filters from external file
try:
    from __flt import filters
except ImportError:
    filters = {}
    print("Error: __flt.py not found or invalid.")

# Import right-click menu function
try:
    from __rcm import quit_with_confirmation
except ImportError:
    print("Error: __rcm.py not found or invalid.")
    def quit_with_confirmation(event, window, check_thread, stop_event, filters):
        window.destroy()  # Fallback: just close the window

# Set up the Tkinter window with drag-and-drop support
window = TkinterDnD.Tk()
window.title("Model Launcher")
window.geometry("120x120")  # Initial size
window.attributes("-topmost", True)  # Always on top
window.overrideredirect(True)  # Remove window decorations for dragging

# Set default downloads folder
downloads_folder = os.path.expandvars(r"%USERPROFILE%\Downloads")

# Frame for borders (main UI, 2px black)
frame = tk.Frame(window, bg="black")
frame.pack(fill="both", expand=True, padx=2, pady=2)  # 2px black border

# Canvas for background image and widgets, black background
canvas = tk.Canvas(frame, width=116, height=116, highlightthickness=0, bg="black")
canvas.pack(fill="both", expand=True)

# Background image variables
bg_image = None
bg_image_id = None
current_image_path = os.path.join("_gfx", "skydrop.png")

# Thread control
check_thread = None
stop_event = threading.Event()

# Label variable (canvas text)
label = None

# Dragging functionality
def start_drag(event):
    window._drag_start_x = event.x
    window._drag_start_y = event.y

def drag_window(event):
    deltax = event.x - window._drag_start_x
    deltay = event.y - window._drag_start_y
    x = window.winfo_x() + deltax
    y = window.winfo_y() + deltay
    window.geometry(f"+{x}+{y}")

canvas.bind("<Button-1>", start_drag)
canvas.bind("<B1-Motion>", drag_window)

# Resizing functionality
def resize_window(event):
    x, y = event.x, event.y
    new_width = min(max(x, 120), 256)  # Min 120, Max 256
    new_height = min(max(y, 120), 256)  # Min 120, Max 256
    window.geometry(f"{new_width}x{new_height}")
    canvas.config(width=new_width-4, height=new_height-4)
    update_background_image(current_image_path)

canvas.bind("<B3-Motion>", resize_window)

# Bind right-click to the imported function
canvas.bind("<Button-3>", lambda event: quit_with_confirmation(event, window, check_thread, stop_event, filters))

# Vertical offset for text (in pixels)
TEXT_OFFSET_Y = 30  # You can change this value as needed
def show_label(event):
    canvas.itemconfig(label, text="LMB = Drag\nRMB = Options", state="normal")
    canvas.coords(label, canvas.winfo_width() // 2, (canvas.winfo_height() // 2) + TEXT_OFFSET_Y)

def hide_label(event):
    canvas.itemconfig(label, text="Drag a preview here", state="normal")
    canvas.coords(label, canvas.winfo_width() // 2, (canvas.winfo_height() // 2) + TEXT_OFFSET_Y)

canvas.bind("<Enter>", show_label)
canvas.bind("<Leave>", hide_label)

def update_background_image(filepath):
    global bg_image, bg_image_id, current_image_path, label
    try:
        # Ensure the file path is relative to the script's directory
        if not os.path.isabs(filepath):
            filepath = os.path.join(script_dir, filepath)
        img = Image.open(filepath)
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width, canvas_height = 116, 116
        img = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        bg_image = ImageTk.PhotoImage(img)
        if bg_image_id is not None:
            canvas.delete(bg_image_id)
        bg_image_id = canvas.create_image(0, 0, image=bg_image, anchor="nw")
        canvas.image = bg_image  # Prevent garbage collection
        current_image_path = filepath
        if label is not None:  # Only lift label if it exists
            canvas.lift(label)
        window.update()
    except Exception as e:
        print(f"Error setting background image: {str(e)}")

# Set default background image (skydrop.png) and initialize UI
def initialize_ui():
    global label
    # Create text centered on the canvas with vertical offset
    label = canvas.create_text(
        canvas.winfo_width() // 2,
        (canvas.winfo_height() // 2) + TEXT_OFFSET_Y,  # Apply vertical offset
        text="Drag a preview here",
        font=("Arial", 8),
        fill="white",
        state="normal"
    )
    update_background_image(os.path.join("_gfx", "skydrop.png"))  # Set background after label is created

window.after(100, initialize_ui)  # Run after 100ms to ensure window is rendered

def set_exif_acquired(image_path):
    try:
        # Load existing EXIF data
        exif_dict = piexif.load(image_path)
    except:
        # If no EXIF data exists, start with an empty dict
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Set the Copyright field to "Acquired"
    exif_dict["0th"][piexif.ImageIFD.Copyright] = "Acquired".encode()
    
    # Convert to bytes and update the image
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, image_path)
    print(f"Set Copyright to 'Acquired' for {image_path}")

def check_and_move_archive(model_id, parent_folder, image_path):
    archive_extensions = ['.rar', '.7z', '.zip']
    while not stop_event.is_set():  # Check until stopped
        for filename in os.listdir(downloads_folder):
            if model_id in filename and any(filename.endswith(ext) for ext in archive_extensions):
                downloaded_file = os.path.join(downloads_folder, filename)
                target_path = os.path.join(parent_folder, filename)
                try:
                    shutil.move(downloaded_file, target_path)
                    print(f"Moved: {downloaded_file} to {target_path}")
                    set_exif_acquired(image_path)  # Set "Acquired" before opening
                    os.startfile(target_path)
                    return
                except Exception as e:
                    print(f"Error moving/launching: {str(e)}")
                    return
        print(f"Checking for archive with model_id '{model_id}' in {downloads_folder}...")
        time.sleep(2)  # Check every 2 seconds

def process_image(filepath):
    global check_thread, stop_event
    try:
        # Set the dragged image as background
        update_background_image(filepath)

        # Extract model_id using regex
        sky_regex = r"(\d{2,8}\.\w{12,13})"
        filename = os.path.basename(filepath)
        match = re.search(sky_regex, filename)
        
        if not match:
            print(f"No model_id found in: {filename}")
            return
        
        model_id = match.group(1)
        parent_folder = os.path.dirname(filepath)
        print(f"Model ID: {model_id}")

        # Step 1: Check for existing archive in parent folder
        archive_extensions = ['.rar', '.7z', '.zip']
        for ext in archive_extensions:
            archive_path = os.path.join(parent_folder, f"{model_id}{ext}")
            if os.path.exists(archive_path):
                print(f"Found archive: {archive_path}")
                set_exif_acquired(filepath)  # Set "Acquired" before opening
                os.startfile(archive_path)
                return
        
        # Step 2: Extract and launch URL from Exif if no archive in parent folder
        with pyexiv2.Image(filepath) as img:
            model_url = img.read_exif().get('Exif.Image.XPComment', None)
            if model_url:
                cleaned_url = ''.join(c for c in model_url if c.isprintable() and c != '\0')
                if cleaned_url.startswith('http'):
                    print(f"Launching URL: {cleaned_url}")
                    webbrowser.open(cleaned_url)
                else:
                    print(f"Invalid URL: {cleaned_url}")
                    return
            else:
                print("No URL found in Exif")
                return
        
        # Step 3: Stop previous thread and start new archive checking thread
        if check_thread and check_thread.is_alive():
            stop_event.set()  # Signal previous thread to stop
            check_thread.join()  # Wait for it to finish
        stop_event.clear()  # Reset stop event for new thread
        check_thread = threading.Thread(target=check_and_move_archive, args=(model_id, parent_folder, filepath))
        check_thread.daemon = True  # Thread stops when main program exits
        check_thread.start()
    
    except Exception as e:
        print(f"Error: {str(e)}")

# Drag and drop event handler for images
def drop_image(event):
    filepath = event.data.strip('{}')
    process_image(filepath)

# Bind drop events (only for files)
window.drop_target_register(DND_FILES)
window.dnd_bind('<<Drop>>', drop_image)

# Start the Tkinter loop
window.mainloop()
