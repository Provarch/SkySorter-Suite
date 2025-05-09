import tkinter as tk
from PIL import Image, ImageTk
import os
import webbrowser

# Global variable to track the active dialog
active_dialog = None

def quit_with_confirmation(event, window, check_thread, stop_event, filters):
    global active_dialog
    
    # Close any existing dialog
    if active_dialog is not None:
        active_dialog.destroy()
    
    dialog = tk.Toplevel(window)
    dialog.overrideredirect(True)  # Frameless window
    dialog.geometry(f"410x700+{window.winfo_x()+0}+{window.winfo_y()+120}")
    dialog.configure(bg="white")  # White background for border
    
    # Store the dialog as the active one
    active_dialog = dialog
    
    # Ensure the dialog reference is cleared when closed
    def on_dialog_close():
        global active_dialog
        active_dialog = None
        dialog.destroy()
    
    dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
    
    # Inner frame for content with black background and 2px padding for white border
    inner_frame = tk.Frame(dialog, bg="black")
    inner_frame.pack(fill="both", expand=True, padx=2, pady=2)  # 2px white border effect
    
    # Dragging functionality for the right-click menu
    def start_drag(event):
        dialog._drag_start_x = event.x
        dialog._drag_start_y = event.y

    def drag_dialog(event):
        deltax = event.x - dialog._drag_start_x
        deltay = event.y - dialog._drag_start_y
        x = dialog.winfo_x() + deltax
        y = dialog.winfo_y() + deltay
        dialog.geometry(f"+{x}+{y}")

    inner_frame.bind("<Button-1>", start_drag)
    inner_frame.bind("<B1-Motion>", drag_dialog)
    
    # Right-click to close the menu
    inner_frame.bind("<Button-3>", lambda e: on_dialog_close())
    
    button_style = {"bg": "black", "fg": "white", "font": ("Arial", 10), 
                    "bd": 1, "relief": "solid", "activebackground": "#444444", "activeforeground": "white"}
    
    def on_yes():
        stop_event.set()  # Stop any running thread
        if check_thread and check_thread.is_alive():
            check_thread.join()  # Wait for thread to finish
        on_dialog_close()  # Clear the active dialog
        window.destroy()  # Then destroy main window

    def on_no():
        on_dialog_close()  # Clear the active dialog
    
    # Picasa button functionality
    def on_picasa():
        picasa_path = r"C:\Program Files (x86)\Google\Picasa3\Picasa3.exe"
        installer_path = os.path.join(os.path.dirname(__file__), "picasa-3-9-141-259.exe")
        
        if os.path.exists(picasa_path):
            os.startfile(picasa_path)
            on_dialog_close()
        else:
            # Show installation prompt
            install_dialog = tk.Toplevel(dialog)
            install_dialog.overrideredirect(True)
            install_dialog.geometry(f"300x180+{window.winfo_x()+50}+{window.winfo_y()+250}")
            install_dialog.configure(bg="white")
            
            inner_install_frame = tk.Frame(install_dialog, bg="black")
            inner_install_frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            tk.Label(inner_install_frame, 
                    text=f"Picasa not found.\nInstall Picasa 3 at:\n{picasa_path}?", 
                    bg="black", fg="white", font=("Arial", 10), justify="center").pack(pady=10)
            
            def start_install():
                if os.path.exists(installer_path):
                    os.startfile(installer_path)
                else:
                    print(f"Installer not found at: {installer_path}")
                install_dialog.destroy()
                on_dialog_close()
            
            tk.Button(inner_install_frame, text="Install", command=start_install, **button_style).pack(side="left", padx=20, pady=5)
            tk.Button(inner_install_frame, text="Cancel", command=install_dialog.destroy, **button_style).pack(side="right", padx=20, pady=5)
    
    # YouTube button functionality
    def on_youtube():
        webbrowser.open("https://www.youtube.com/@provarch")
        on_dialog_close()
    
    # Sky Droplet button functionality
    def on_sky_droplet():
        webbrowser.open("https://www.patreon.com/c/Provarch")
        on_dialog_close()
    
    # Guide button functionality
    def on_guide():
        guide_dialog = tk.Toplevel(dialog)
        guide_dialog.overrideredirect(True)
        guide_dialog.geometry(f"500x400+{window.winfo_x()+50}+{window.winfo_y()+250}")
        guide_dialog.configure(bg="white")
        
        inner_guide_frame = tk.Frame(guide_dialog, bg="black")
        inner_guide_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        guide_text = (
            "How to Use:\n"
            "DROPLET:\n Drag a model preview from picasa browser onto the droplet window\n"
            "and script will visit the 3dsky model's download page.\n"
            "Once you click to download cristian...\n"
            "it will DL and move the model to where you model preview is...\n"            
            "If you downloaded the model before, will \n"
            "open the model archive with your default zip manager\n"
            "and you can merge your model to you 3dsmax session as usual"
            "\n"
            "\n"
            "PICASA:\n"
            "Use keywords to filter images in Picasa:\n"
            "Combine multiple keywrods like 'modern beige triangle'.\n"
            "Even use 'y202' to filter and show newest models (from 2020 to 2025)\n"
            "You can skimp on entering full keywords\n"
            "for example: 'mod cha minott leath rect y202'\n"
            "which will show modern chairs by minotti with leather material\n in ractangular shape between year 2020-25"
        )
        
        tk.Label(inner_guide_frame, 
                text=guide_text, 
                bg="black", fg="white", font=("Arial", 10), justify="left").pack(pady=10, padx=10)
        
        tk.Button(inner_guide_frame, text="Close", command=guide_dialog.destroy, **button_style).pack(pady=5)
    
    # Sky Droplet logo button frame (centered at the top)
    sky_droplet_frame = tk.Frame(inner_frame, bg="black")
    sky_droplet_frame.pack(pady=5)
    
    # Load Sky Droplet logo
    sky_droplet_logo = Image.open(os.path.join("_gfx", "skydrop.png"))
    sky_droplet_logo = sky_droplet_logo.resize((133, 133), Image.Resampling.LANCZOS)
    sky_droplet_logo_tk = ImageTk.PhotoImage(sky_droplet_logo)
    
    # Sky Droplet button
    sky_droplet_button = tk.Button(sky_droplet_frame, image=sky_droplet_logo_tk, command=on_sky_droplet, 
                                   bg="black", bd=1, relief="solid", activebackground="#444444")
    sky_droplet_button.image = sky_droplet_logo_tk  # Prevent garbage collection
    sky_droplet_button.pack()
    
    # Filter list frame with three columns, centered
    filter_frame = tk.Frame(inner_frame, bg="black")
    filter_frame.pack(pady=5, fill="both", expand=True)
    
    # Centering container for the three columns
    columns_container = tk.Frame(filter_frame, bg="black")
    columns_container.pack(expand=True)  # Center horizontally
    
    # Create three columns
    column1 = tk.Frame(columns_container, bg="black")
    column2 = tk.Frame(columns_container, bg="black")
    column3 = tk.Frame(columns_container, bg="black")
    
    column1.pack(side="left", padx=5, fill="y")
    column2.pack(side="left", padx=5, fill="y")
    column3.pack(side="left", padx=5, fill="y")
    
    # Style for section frames
    section_style = {"bg": "black", "bd": 1, "relief": "solid", "highlightbackground": "white", "highlightthickness": 1}
    
    # Map for non-standard Tkinter color names
    color_map = {
        "dark blue": "darkblue",
        "light green": "lightgreen",
        "fuchsia": "fuchsia",
        "gray": "gray",
        "turquoise": "turquoise",
        "beige": "#f5f5dc",
        "violet": "violet"
    }
    
    # Column 1: Picasa, By Type, Colors
    # Picasa button section (without label)
    picasa_section_frame = tk.Frame(column1, **section_style)
    picasa_section_frame.pack(fill="x", pady=2)
    
    # Load Picasa logo
    picasa_logo = Image.open(os.path.join("_gfx", "picasaweb_logo.gif"))
    picasa_logo = picasa_logo.resize((106, 32), Image.Resampling.LANCZOS)
    picasa_logo_tk = ImageTk.PhotoImage(picasa_logo)
    
    # Picasa button with tooltip
    picasa_button = tk.Button(picasa_section_frame, image=picasa_logo_tk, command=on_picasa, 
                             bg="black", bd=1, relief="solid", activebackground="#444444")
    picasa_button.image = picasa_logo_tk  # Prevent garbage collection
    picasa_button.pack(anchor="w", padx=15, pady=2)
    
    # Tooltip for Picasa button
    picasa_path = r"C:\Program Files (x86)\Google\Picasa3\Picasa3.exe"
    tooltip_text = "Launch Picasa 3" if os.path.exists(picasa_path) else f"Install Picasa 3 at\n{picasa_path}"
    def show_tooltip(event):
        tooltip = tk.Toplevel(picasa_button)
        tooltip.overrideredirect(True)
        tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        tk.Label(tooltip, text=tooltip_text, bg="black", fg="white", font=("Arial", 8), justify="center").pack(padx=5, pady=2)
        picasa_button.tooltip = tooltip
    
    def hide_tooltip(event):
        if hasattr(picasa_button, 'tooltip'):
            picasa_button.tooltip.destroy()
    
    picasa_button.bind("<Enter>", show_tooltip)
    picasa_button.bind("<Leave>", hide_tooltip)
    
    # By Type, Colors sections
    for category in ["By Type", "Colors"]:
        section_frame = tk.Frame(column1, **section_style)
        section_frame.pack(fill="x", pady=2)
        tk.Label(section_frame, text=category.upper() + ":", bg="black", fg="white", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
        
        if category == "Colors":
            for item in filters.get(category, []):
                # Frame for each color item (to hold canvas and label)
                color_frame = tk.Frame(section_frame, bg="black")
                color_frame.pack(anchor="w", padx=5)
                
                # Canvas for the color circle
                canvas = tk.Canvas(color_frame, width=12, height=12, highlightthickness=0, bg="black")
                canvas.pack(side="left", padx=(10, 2))  # Adjust padding for alignment
                
                # Draw the color circle
                try:
                    fill_color = color_map.get(item.lower(), item.lower())
                    canvas.create_oval(2, 2, 10, 10, fill=fill_color, outline="gray")
                except tk.TclError:
                    canvas.create_oval(2, 2, 10, 10, fill="gray", outline="black")  # Fallback
                
                # Text label for the color
                tk.Label(color_frame, text=item.upper(), bg="black", fg="white", font=("Arial", 8)).pack(side="left")
        else:
            for item in filters.get(category, []):
                tk.Label(section_frame, text=item.upper(), bg="black", fg="white", font=("Arial", 8)).pack(anchor="w", padx=15)
    
    # Column 2: Quit?, Filtering Guide, By Style, By Shape
    # Quit? section
    quit_section_frame = tk.Frame(column2, **section_style)
    quit_section_frame.pack(fill="x", pady=2)
    tk.Label(quit_section_frame, text="QUIT?", bg="black", fg="white", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
    yes_no_frame = tk.Frame(quit_section_frame, bg="black")
    yes_no_frame.pack(anchor="w", padx=15)
    yes_button = tk.Button(yes_no_frame, text="Yes", command=on_yes, **button_style)
    yes_button.pack(side="left", padx=5, pady=2)
    no_button = tk.Button(yes_no_frame, text="No", command=on_no, **button_style)
    no_button.pack(side="left", padx=5, pady=2)
    for btn in (yes_button, no_button):
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#444444"))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg="black"))
    
    # Filtering Guide section
    guide_section_frame = tk.Frame(column2, **section_style)
    guide_section_frame.pack(fill="x", pady=2)
    tk.Label(guide_section_frame, text="FILTERING GUIDE:", bg="black", fg="white", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
    guide_button_inner = tk.Button(guide_section_frame, text="Open Guide", command=on_guide, **button_style)
    guide_button_inner.pack(anchor="w", padx=15, pady=2)
    guide_button_inner.bind("<Enter>", lambda e: guide_button_inner.config(bg="#444444"))
    guide_button_inner.bind("<Leave>", lambda e: guide_button_inner.config(bg="black"))
    
    # By Style, By Shape sections
    for category in ["By Style", "By Shape"]:
        section_frame = tk.Frame(column2, **section_style)
        section_frame.pack(fill="x", pady=2)
        tk.Label(section_frame, text=category.upper() + ":", bg="black", fg="white", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
        for item in filters.get(category, []):
            tk.Label(section_frame, text=item.upper(), bg="black", fg="white", font=("Arial", 8)).pack(anchor="w", padx=15)
    
    # Column 3: YouTube, By Year, Materials
    # YouTube button section (without label)
    youtube_section_frame = tk.Frame(column3, **section_style)
    youtube_section_frame.pack(fill="x", pady=2)
    
    # Load YouTube logo
    youtube_logo = Image.open(os.path.join("_gfx", "youtube_logo.gif"))
    youtube_logo = youtube_logo.resize((106, 32), Image.Resampling.LANCZOS)
    youtube_logo_tk = ImageTk.PhotoImage(youtube_logo)
    
    # YouTube button with tooltip
    youtube_button = tk.Button(youtube_section_frame, image=youtube_logo_tk, command=on_youtube, 
                              bg="black", bd=1, relief="solid", activebackground="#444444")
    youtube_button.image = youtube_logo_tk  # Prevent garbage collection
    youtube_button.pack(anchor="w", padx=15, pady=2)
    
    # Tooltip for YouTube button
    youtube_tooltip_text = "Visit ProVarch YouTube Channel"
    def show_youtube_tooltip(event):
        tooltip = tk.Toplevel(youtube_button)
        tooltip.overrideredirect(True)
        tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        tk.Label(tooltip, text=youtube_tooltip_text, bg="black", fg="white", font=("Arial", 8), justify="center").pack(padx=5, pady=2)
        youtube_button.tooltip = tooltip
    
    def hide_youtube_tooltip(event):
        if hasattr(youtube_button, 'tooltip'):
            youtube_button.tooltip.destroy()
    
    youtube_button.bind("<Enter>", show_youtube_tooltip)
    youtube_button.bind("<Leave>", hide_youtube_tooltip)
    
    # By Year, Materials sections
    for category in ["By Year", "Materials"]:
        section_frame = tk.Frame(column3, **section_style)
        section_frame.pack(fill="x", pady=2)
        tk.Label(section_frame, text=category.upper() + ":", bg="black", fg="white", font=("Arial", 8, "bold")).pack(anchor="w", padx=5)
        for item in filters.get(category, []):
            tk.Label(section_frame, text=item.upper(), bg="black", fg="white", font=("Arial", 8)).pack(anchor="w", padx=15)
