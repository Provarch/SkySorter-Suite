import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QDialog, QSizePolicy, QSizeGrip, QInputDialog, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
import sys
import re
import requests
import time
import subprocess
import shutil
from urllib.parse import urlparse, quote
from pathlib import Path
import hashlib
from PIL import Image
import imagehash
import json
import platform
import webbrowser

class ConfirmExitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog { background-color: black; color: white; font-size: 12px; }
            QPushButton { background-color: transparent; color: white; border: 1px solid white; border-radius: 5px; padding: 5px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); }
        """)
        layout = QVBoxLayout(self)
        label = QLabel("Are you sure you want to quit?")
        layout.addWidget(label)
        yes_button = QPushButton("Yes")
        yes_button.clicked.connect(self.accept)
        layout.addWidget(yes_button)
        no_button = QPushButton("No")
        no_button.clicked.connect(self.reject)
        layout.addWidget(no_button)
        self.setLayout(layout)

class CredentialDialog(QDialog):
    def __init__(self, parent=None, title="Login Credentials", prompt="Enter your 3dsky.org email:"):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QWidget { background-color: black; }
            QLabel { color: white; }
            QPushButton { 
                background-color: rgba(61, 61, 61, 200); 
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 5px; 
            }
            QPushButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
            QPushButton:disabled { 
                background-color: rgba(40, 40, 40, 200); 
                color: #777777; 
            }
            QWebEngineView { background-color: black; }
            
            /* Special styling for Thrash button */
            QPushButton#thrash_button { 
                background-color: #883333;  /* Darker red in normal state */
            }
            QPushButton#thrash_button:hover { 
                background-color: #AA5555;  /* Lighter red on hover */
            }
        """)
        layout = QVBoxLayout(self)
        self.label = QLabel(prompt)
        layout.addWidget(self.label)
        self.input_field = QLineEdit(self)
        if "password" in prompt.lower():
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input_field)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_text(self):
        return self.input_field.text()

class DropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Define sky_regex to match model_id format (e.g., "5353361.6486e31087722.zip")
        self.sky_regex = re.compile(r'^\d{4,8}\.[0-9a-fA-F]{12,13}\.(zip|rar|7z)$')

        # Main layout (vertical)
        self.main_layout = QVBoxLayout()

        # Horizontal layout for content
        self.content_layout = QHBoxLayout()

        # Image container widget for overlay (this will hold the image and buttons)
        self.image_container_widget = QWidget(self)
        self.image_container_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_container_widget.setMinimumSize(100, 100)
        self.image_container_widget.setMaximumSize(460, 460)

        # Vertical layout for the image label (restores original sizing behavior)
        image_container = QVBoxLayout(self.image_container_widget)

        # Image label (inside the layout for proper sizing)
        self.image_label = QLabel(self.image_container_widget)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMaximumSize(460, 460)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(100, 100)
        image_container.addWidget(self.image_label)

        # Previous preview button (overlayed on left)
        self.prev_preview_button = QPushButton("<", self.image_container_widget)
        self.prev_preview_button.clicked.connect(self.display_prev_preview)
        self.prev_preview_button.setEnabled(False)
        self.prev_preview_button.setToolTip("Previous preview image")
        self.prev_preview_button.setFixedSize(30, 30)
        self.prev_preview_button.setStyleSheet("QPushButton { background-color: rgba(0, 0, 0, 150); color: white; border: none; } QPushButton:hover { background-color: rgba(100, 100, 100, 150); }")

        # Next preview button (overlayed on right)
        self.next_preview_button = QPushButton(">", self.image_container_widget)
        self.next_preview_button.clicked.connect(self.display_next_preview)
        self.next_preview_button.setEnabled(False)
        self.next_preview_button.setToolTip("Next preview image")
        self.next_preview_button.setFixedSize(30, 30)
        self.next_preview_button.setStyleSheet("QPushButton { background-color: rgba(0, 0, 0, 150); color: white; border: none; } QPushButton:hover { background-color: rgba(100, 100, 100, 150); }")

        # Add image container widget to content layout (left)
        self.content_layout.addWidget(self.image_container_widget, stretch=1)

        # Vertical layout for buttons (middle)
        self.button_layout = QVBoxLayout()
        self.button_layout.addStretch()

        script_dir = Path(__file__).parent

        # Provarch button
        self.provarch_button = QPushButton(self)
        self.provarch_button.clicked.connect(self.open_provarch)
        provarch_icon_path = script_dir / "_gfx" / "prov_logo_v3.png"
        if provarch_icon_path.exists():
            self.provarch_button.setIcon(QIcon(str(provarch_icon_path)))
            self.provarch_button.setIconSize(QSize(60, 60))
        self.provarch_button.setFixedSize(70, 70)
        self.provarch_button.setToolTip("Visit Provarch on Patreon")
        self.button_layout.addWidget(self.provarch_button)

        # YouTube and Discord buttons
        youtube_discord_layout = QHBoxLayout()
        self.youtube_button = QPushButton(self)
        self.youtube_button.clicked.connect(self.open_youtube)
        youtube_icon_path = script_dir / "_gfx" / "yt_logo.png"
        if youtube_icon_path.exists():
            self.youtube_button.setIcon(QIcon(str(youtube_icon_path)))
            self.youtube_button.setIconSize(QSize(20, 20))
        self.youtube_button.setFixedSize(25, 25)
        self.youtube_button.setToolTip("Visit Provarch on YouTube")
        youtube_discord_layout.addWidget(self.youtube_button)

        self.discord_button = QPushButton(self)
        self.discord_button.clicked.connect(self.open_discord)
        discord_icon_path = script_dir / "_gfx" / "dis_logo+.png"
        if discord_icon_path.exists():
            self.discord_button.setIcon(QIcon(str(discord_icon_path)))
            self.discord_button.setIconSize(QSize(20, 20))
        self.discord_button.setFixedSize(25, 25)
        self.discord_button.setToolTip("Join the Provarch Discord community")
        youtube_discord_layout.addWidget(self.discord_button)
        self.button_layout.addLayout(youtube_discord_layout)

        # Tutorial button
        self.tutorial_button = QPushButton("Tuto", self)
        self.tutorial_button.clicked.connect(self.open_tutorial)
        self.tutorial_button.setToolTip("Watch the SkyMatcher tutorial on YouTube")
        self.button_layout.addWidget(self.tutorial_button)

        # Login button
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.open_login)
        self.login_button.setToolTip("Login to 3dsky.org (auto-fills credentials and keeps them strictly local)")
        self.button_layout.addWidget(self.login_button)

        # Check button
        self.check_button = QPushButton("Check", self)
        self.check_button.clicked.connect(self.open_archive)
        self.check_button.setEnabled(False)
        self.check_button.setToolTip("Open the current model's archive")
        self.button_layout.addWidget(self.check_button)

        # Browse button
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.open_folder)
        self.browse_button.setToolTip("Select a folder or open current folder")
        self.button_layout.addWidget(self.browse_button)

        # Back button
        self.back_button = QPushButton("Back", self)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)
        self.back_button.setToolTip("Go to the previous model archive")
        back_width = self.back_button.sizeHint().width()
        self.back_button.setFixedHeight(back_width)
        self.button_layout.addWidget(self.back_button)

        # Next button
        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.display_next_model)
        self.next_button.setEnabled(False)
        self.next_button.setToolTip("Go to the next model archive")
        next_width = self.next_button.sizeHint().width()
        self.next_button.setFixedHeight(next_width)
        self.button_layout.addWidget(self.next_button)

        # Non button
        self.non_button = QPushButton("Non", self)
        self.non_button.clicked.connect(self.move_to_non_sky)
        self.non_button.setFixedHeight(back_width)
        self.non_button.setEnabled(False)
        self.non_button.setToolTip("Move to __non-sky folder")
        self.button_layout.addWidget(self.non_button)

        # Thrash button
        self.thrash_button = QPushButton("Thrash", self)
        self.thrash_button.clicked.connect(self.move_to_thrash)
        self.thrash_button.setFixedHeight(back_width)
        self.thrash_button.setEnabled(False)
        self.thrash_button.setToolTip("Move to __thrash folder")
        self.button_layout.addWidget(self.thrash_button)
        
        # Quit button
        self.quit_button = QPushButton("Quit", self)
        self.quit_button.clicked.connect(self.show_quit_dialog)
        self.quit_button.setFixedHeight(back_width)
        self.quit_button.setToolTip("Quit the application")
        self.quit_button.setStyleSheet("""
            QPushButton { 
                background-color: rgba(150, 30, 30, 150); 
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 5px; 
            }
            QPushButton:hover { 
                background-color: rgba(255, 50, 50, 200); 
            }
        """)
        self.button_layout.addWidget(self.quit_button)

        self.button_layout.addStretch()
        self.button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Web view for displaying 3dsky.org (right)
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("https://3dsky.org"))
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.web_view.setMinimumSize(400, 300)

        # Add to content layout
        self.content_layout.addLayout(self.button_layout)
        self.content_layout.addWidget(self.web_view, stretch=1)

        # Add content layout to main layout
        self.main_layout.addLayout(self.content_layout, stretch=1)

        # Status label and resize grip
        self.label = QLabel("Drag an archive file or image here", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize_grip = QSizeGrip(self)
        self.resize_grip.setFixedSize(20, 20)
        self.resize_grip.setStyleSheet("QSizeGrip { background-color: #FF5555; border: 1px solid white; }")

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.resize_grip, alignment=Qt.AlignmentFlag.AlignRight)
        self.main_layout.addLayout(bottom_layout)
        self.setLayout(self.main_layout)

        # Set initial size and center window
        self.setMinimumSize(1200, 680)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Store state
        self.last_archive_path = None
        self.model_name = None
        self.preview_files = []
        self.main_preview = None
        self.current_image_path = None
        self.url_history = ["https://3dsky.org"]
        self.current_index = 0
        self.model_list = []
        self.current_model_index = -1
        self.current_preview_index = 0  # Track current preview

        # Dragging and resizing state
        self.dragging = False
        self.resizing = False
        self.drag_position = None

        # Credentials will be loaded or prompted when Login is clicked
        self.credentials = {"email": "", "password": ""}
        self.config_path = script_dir / "login.cfg"

        # Apply black theme
        self.setStyleSheet("""
            QWidget { background-color: black; }
            QLabel { color: white; }
            QPushButton { background-color: rgba(61, 61, 61, 200); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: rgba(77, 77, 77, 200); }
            QWebEngineView { background-color: black; }
        """)

        # Initial positioning of overlay buttons
        self.update_button_positions()

        # Check for command-line argument for folder path
        if len(sys.argv) > 1:
            folder_path = sys.argv[1].strip('"')  # Remove quotes if present
            folder_path = Path(folder_path)
            if folder_path.exists() and folder_path.is_dir():
                # Defer folder loading until the window is shown
                QTimer.singleShot(0, lambda: self.load_folder(folder_path))
            else:
                self.label.setText(f"Invalid folder path: {folder_path}")
        
    # New method to display the previous preview
    def display_prev_preview(self):
        if not self.preview_files or len(self.preview_files) <= 1:
            return
        self.current_preview_index = (self.current_preview_index - 1) % len(self.preview_files)
        self.display_image(self.preview_files[self.current_preview_index])
        self.update_preview_buttons()

    # New method to display the next preview
    def display_next_preview(self):
        if not self.preview_files or len(self.preview_files) <= 1:
            return
        self.current_preview_index = (self.current_preview_index + 1) % len(self.preview_files)
        self.display_image(self.preview_files[self.current_preview_index])
        self.update_preview_buttons()

    # New method to update the state of preview buttons
    def update_preview_buttons(self):
        has_multiple_previews = len(self.preview_files) > 1
        self.prev_preview_button.setEnabled(has_multiple_previews)
        self.next_preview_button.setEnabled(has_multiple_previews)
        self.prev_preview_button.setVisible(has_multiple_previews)
        self.next_preview_button.setVisible(has_multiple_previews)

    # Modified handle_archive_drop to reset preview index and update buttons
    def handle_archive_drop(self, file_path):
        self.last_archive_path = Path(file_path)
        archive_name = self.last_archive_path.stem
        self.model_name = archive_name
        self.label.setText(f"Processing archive: {archive_name}")

        directory = self.last_archive_path.parent
        self.refresh_model_list(directory)
        
        if not self.model_list:
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.current_preview_index = 0  # Reset
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            self.update_preview_buttons()  # Update new buttons
            return

        self.current_model_index = self.model_list.index(self.last_archive_path) if self.last_archive_path in self.model_list else 0
        self.preview_files = [
            f for f in directory.glob(f"{self.model_name}*")
            if f.suffix.lower() in ('.jpg', '.jpeg', '.webp', '.png') and f.is_file()
        ]
        
        self.next_button.setEnabled(len(self.model_list) > 1)
        self.back_button.setEnabled(len(self.model_list) > 1)
        self.check_button.setEnabled(True)
        self.non_button.setEnabled(True)
        self.thrash_button.setEnabled(True)

        if self.preview_files:
            self.preview_files.sort(key=lambda x: x.name)
            self.main_preview = self.preview_files[0]
            self.current_preview_index = 0  # Reset to first preview
            prev, curr, nxt = self.get_model_names()
            self.label.setText(f" {curr}")
            self.display_image(self.main_preview)
            self.update_preview_buttons()  # Update new buttons
        else:
            self.main_preview = None
            self.current_preview_index = 0  # Reset
            self.image_label.clear()
            self.label.setText(f"No previews found for {archive_name}")
            self.update_preview_buttons()  # Update new buttons

        search_query = self.sanitize_search_string(archive_name)
        search_url = f"https://3dsky.org/3dmodels?query={quote(search_query)}"
        print(f"Loading search URL in web view: {search_url}")
        self.web_view.setUrl(QUrl(search_url))
        self.update_history(search_url)

    # Modified handle_image_drop to reset preview index and update buttons
    def handle_image_drop(self, file_path):
        image_path = Path(file_path)
        self.current_image_path = image_path
        directory = image_path.parent
        image_base_name = image_path.stem.rsplit(maxsplit=1)[0]
        self.model_name = image_base_name.strip()
        self.label.setText(f"Processing image: {image_path.name}")

        self.refresh_model_list(directory)
        
        matching_archives = [
            f for f in directory.glob(f"{image_base_name}*") 
            if f.suffix.lower() in ('.rar', '.zip', '.7z') and f.is_file()
        ]
        
        if matching_archives:
            self.last_archive_path = matching_archives[0]
            self.model_name = self.last_archive_path.stem
            self.main_preview = image_path
            self.preview_files = [image_path]
            other_previews = [
                f for f in directory.glob(f"{self.model_name}*")
                if f.suffix.lower() in ('.jpg', '.jpeg', '.webp', '.png') 
                and f.is_file() 
                and f != image_path
            ]
            self.preview_files.extend(other_previews)
            self.current_model_index = (
                self.model_list.index(self.last_archive_path) 
                if self.last_archive_path in self.model_list 
                else 0
            )
        else:
            self.last_archive_path = None
            self.main_preview = image_path
            self.preview_files = [image_path]
            self.current_model_index = -1
            self.label.setText(f"No matching archive found for: {image_base_name}")

        self.current_preview_index = 0  # Reset to first preview
        has_archive = self.last_archive_path is not None
        self.check_button.setEnabled(has_archive)
        self.non_button.setEnabled(has_archive)
        self.thrash_button.setEnabled(has_archive)
        self.next_button.setEnabled(len(self.model_list) > 1)
        self.back_button.setEnabled(len(self.model_list) > 1)
        self.update_preview_buttons()  # Update new buttons

        self.display_image(self.main_preview)
        
        prev, curr, nxt = self.get_model_names()
        self.label.setText(f" {curr}")

        search_query = self.sanitize_search_string(self.model_name)
        search_url = f"https://3dsky.org/3dmodels?query={quote(search_query)}"
        self.web_view.setUrl(QUrl(search_url))
        self.update_history(search_url)

    # Modified go_back to reset preview index and update buttons
    def go_back(self):
        if not self.model_list:
            self.label.setText("No models available to display")
            return
        
        valid_models = [m for m in self.model_list if not self.sky_regex.match(m.name)]
        if not valid_models:
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.current_preview_index = 0  # Reset
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            self.update_preview_buttons()  # Update new buttons
            return
        
        if self.current_model_index < 0 or self.current_model_index >= len(self.model_list):
            self.current_model_index = len(self.model_list) - 1
        
        self.current_model_index = (self.current_model_index - 1) % len(self.model_list)
        
        loops = 0
        while (self.sky_regex.match(self.model_list[self.current_model_index].name) and 
               loops < len(self.model_list)):
            self.current_model_index = (self.current_model_index - 1) % len(self.model_list)
            loops += 1
        
        if loops >= len(self.model_list):
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.current_preview_index = 0  # Reset
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            self.update_preview_buttons()  # Update new buttons
            return
        
        next_model_path = self.model_list[self.current_model_index]
        self.last_archive_path = next_model_path
        self.model_name = next_model_path.stem
        
        directory = self.last_archive_path.parent
        self.preview_files = [
            f for f in directory.glob(f"{self.model_name}*")
            if f.suffix.lower() in ('.jpg', '.jpeg', '.webp', '.png') and f.is_file()
        ]
        
        if self.preview_files:
            self.preview_files.sort(key=lambda x: x.name)
            self.main_preview = self.preview_files[0]
            self.current_preview_index = 0  # Reset to first preview
            prev, curr, nxt = self.get_model_names()
            self.label.setText(f" {curr}")
            self.display_image(self.main_preview)
            self.update_preview_buttons()  # Update new buttons
        else:
            self.main_preview = None
            self.current_preview_index = 0  # Reset
            self.image_label.clear()
            self.label.setText(f"No previews found for model: {self.model_name}")
            self.update_preview_buttons()  # Update new buttons
        
        self.back_button.setEnabled(len(valid_models) > 1)
        self.next_button.setEnabled(len(valid_models) > 1)
        self.check_button.setEnabled(True)
        self.non_button.setEnabled(True)
        self.thrash_button.setEnabled(True)
        
        search_query = self.sanitize_search_string(self.model_name)
        search_url = f"https://3dsky.org/3dmodels?query={quote(search_query)}"
        print(f"Loading previous model URL: {search_url}")
        self.web_view.setUrl(QUrl(search_url))
        self.update_history(search_url)

    # Modified display_next_model to reset preview index and update buttons
    def display_next_model(self):
        if not self.model_list:
            self.label.setText("No models available to display")
            return
        
        valid_models = [m for m in self.model_list if not self.sky_regex.match(m.name)]
        if not valid_models:
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.current_preview_index = 0  # Reset
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            self.update_preview_buttons()  # Update new buttons
            return
        
        if self.current_model_index < 0 or self.current_model_index >= len(self.model_list):
            self.current_model_index = 0
        
        self.current_model_index = (self.current_model_index + 1) % len(self.model_list)
        
        loops = 0
        while (self.sky_regex.match(self.model_list[self.current_model_index].name) and 
               loops < len(self.model_list)):
            self.current_model_index = (self.current_model_index + 1) % len(self.model_list)
            loops += 1
        
        if loops >= len(self.model_list):
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.current_preview_index = 0  # Reset
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            self.update_preview_buttons()  # Update new buttons
            return
        
        next_model_path = self.model_list[self.current_model_index]
        self.last_archive_path = next_model_path
        self.model_name = next_model_path.stem
        
        directory = self.last_archive_path.parent
        self.preview_files = [
            f for f in directory.glob(f"{self.model_name}*")
            if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp') and f.is_file()
        ]
        
        if self.preview_files:
            self.preview_files.sort(key=lambda x: x.name)
            self.main_preview = self.preview_files[0]
            self.current_preview_index = 0  # Reset to first preview
            prev, curr, nxt = self.get_model_names()
            self.label.setText(f" {curr}")
            self.display_image(self.main_preview)
            self.update_preview_buttons()  # Update new buttons
        else:
            self.main_preview = None
            self.current_preview_index = 0  # Reset
            self.image_label.clear()
            self.label.setText(f"No previews found for model: {self.model_name}")
            self.update_preview_buttons()  # Update new buttons
        
        self.back_button.setEnabled(len(valid_models) > 1)
        self.next_button.setEnabled(len(valid_models) > 1)
        self.check_button.setEnabled(True)
        self.non_button.setEnabled(True)
        self.thrash_button.setEnabled(True)
        
        search_query = self.sanitize_search_string(self.model_name)
        search_url = f"https://3dsky.org/3dmodels?query={quote(search_query)}"
        print(f"Loading next model URL: {search_url}")
        self.web_view.setUrl(QUrl(search_url))
        self.update_history(search_url)

    def convert_to_preview_url(self, thumbnail_url):
        if "sky_model_new_thumb_ang" in thumbnail_url:
            return thumbnail_url.replace("sky_model_new_thumb_ang", "tuk_model_custom_filter_ang_en")
        return None
    
    def download_image(self, image_url):
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    file_name = urlparse(image_url).path.split("/")[-1] or "preview_image.jpg"
                    save_dir = self.last_archive_path.parent if self.last_archive_path else Path.cwd()
                    save_path = save_dir / file_name
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    print(f"Image downloaded as: {save_path}")
                    self.label.setText(f"Preview image downloaded: {file_name}")
                    self.display_image(save_path)
                    return save_path
                else:
                    if attempt == max_attempts - 1:  # Last attempt
                        self.label.setText("Failed to download preview image after retries")
                        return None
                    print(f"Attempt {attempt + 1} failed with status code: {response.status_code}")
                    time.sleep(1)  # Small delay before retry
            except Exception as e:
                if attempt == max_attempts - 1:  # Last attempt
                    print(f"Error downloading image after retries: {e}")
                    self.label.setText("Error downloading preview image")
                    return None
                print(f"Attempt {attempt + 1} failed with error: {e}")
                time.sleep(1)  # Small delay before retry
        return None  # Fallback return if all attempts fail
    
    def _remove_old_previews(self, model_name, exclude_path=None):
        """Remove all previews for a model except the excluded path."""
        directory = self.last_archive_path.parent if self.last_archive_path else Path.cwd()
        for old_preview in directory.glob(f"{model_name}*"):
            if old_preview.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                if exclude_path and old_preview.samefile(exclude_path):
                    continue  # Skip the new image we're keeping
                old_preview.unlink()  # Delete the file
                print(f"Removed old preview: {old_preview}")
    # Modified handle_webpage_element_drop to reset preview index and update buttons
    def handle_webpage_element_drop(self, mime_data):
        html = mime_data.html()
        img_match = re.search(r'<img[^>]+src=["\'](.*?)["\']', html, re.IGNORECASE)
        if not img_match:
            self.label.setText("No image found in HTML")
            return

        thumbnail_url = img_match.group(1)
        preview_url = self.convert_to_preview_url(thumbnail_url)
        if not preview_url:
            self.label.setText("Could not convert to preview URL")
            return

        downloaded_file = self.download_image(preview_url)
        if not downloaded_file:
            return

        new_model_id = downloaded_file.stem

        if self.last_archive_path and self.model_name:
            directory = self.last_archive_path.parent
            old_previews = [
                f for f in directory.glob(f"{self.model_name}*")
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp') and f.is_file()
                and not f.samefile(downloaded_file)
            ]
            for old_preview in old_previews:
                hash_result = self.combined_hash(old_preview, model_id=new_model_id)
                if not hash_result.startswith("Error"):
                    print(f"Stored hash {hash_result} for {old_preview} under model_id {new_model_id}")
                else:
                    print(f"Failed to hash {old_preview}: {hash_result}")

        if self.last_archive_path and self.model_name:
            self._remove_old_previews(self.model_name, exclude_path=downloaded_file)

        self.preview_files = [downloaded_file]
        self.main_preview = downloaded_file
        self.current_preview_index = 0  # Reset to first preview
        self.display_image(downloaded_file)
        self.label.setText(f"New preview set: {downloaded_file.name}")
        self.update_preview_buttons()  # Update new buttons

        if self.last_archive_path and self.model_name:
            self.rename_files(downloaded_file)

        self.display_next_model()

    def generate_uid(self) -> str:
            """Generate a unique 16-character system identifier based on platform and machine."""
            system_info = {
                'platform': platform.system(),
                'machine': platform.machine(),
            }
            combined_info = '-'.join(str(value) for value in system_info.values())
            hashed_id = hashlib.sha256(combined_info.encode()).hexdigest()
            return hashed_id[:16]

    def combined_hash(self, image_path, model_id=None):
        """
        Generate a combined pHash and dHash for the given image and store it in _Skynized.ftprnt.
        If the file is inaccessible, fail silently. Use a backup file to handle corruption.
        
        Args:
            image_path (str or Path): Path to the image file.
            model_id (str, optional): Model ID to associate with the hash. Defaults to filename.
            
        Returns:
            str: Combined hash or error message.
        """
        image_path = str(image_path)  # Ensure it's a string
        valid_extensions = ('.jpg', '.jpeg', '.webp', '.png', '.bmp')
        if not any(image_path.lower().endswith(ext) for ext in valid_extensions):
            return f"Error: Invalid image file extension. Got: {image_path}"

        if not os.path.exists(image_path):
            return f"Error: File not found: {image_path}"

        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                phash = str(imagehash.phash(img, hash_size=16))
                dhash = str(imagehash.dhash(img, hash_size=16))
                combined = f"{phash}_{dhash}"
        except Exception as e:
            return f"Error processing image: {e}"

        # Define the target file paths
        ftprnt_file = r"R:\!_3DSKY_DATA\!_Fooprints\_Skynized.ftprnt"
        backup_file = r"R:\!_3DSKY_DATA\!_Fooprints\_Skynized.ftprnt.bak"

        # Check if the target directory is accessible
        ftprnt_dir = os.path.dirname(ftprnt_file)
        if not os.path.isdir(ftprnt_dir):
            print(f"Directory not accessible, skipping hash storage: {ftprnt_dir}")
            return combined

        # Use provided model_id or fallback to filename
        model_id = model_id or os.path.basename(image_path)
        
        # Load existing data, try backup if primary file is corrupted
        data = {}
        if os.path.exists(ftprnt_file):
            try:
                with open(ftprnt_file, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print(f"Primary ftprnt file corrupted, attempting to load backup: {ftprnt_file}")
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r') as f:
                            data = json.load(f)
                        print(f"Successfully loaded backup: {backup_file}")
                    except json.JSONDecodeError:
                        print(f"Backup file also corrupted, starting fresh: {backup_file}")
                        data = {}
                else:
                    print(f"No backup file found, starting fresh: {backup_file}")
                    data = {}
        
        # Create a backup of the current ftprnt file if it exists
        if os.path.exists(ftprnt_file):
            try:
                shutil.copy2(ftprnt_file, backup_file)
                print(f"Created backup: {backup_file}")
            except Exception as e:
                print(f"Failed to create backup, skipping hash storage: {e}")
                return combined
        
        # Store the hash with the model_id
        data[combined] = model_id
        
        # Write updated data to ftprnt file
        try:
            with open(ftprnt_file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Stored hash {combined} for {model_id} in {ftprnt_file}")
        except Exception as e:
            print(f"Failed to write to ftprnt file, skipping hash storage: {e}")
        
        return combined
    
    def load_credentials(self):
        """Load email and password from login.cfg."""
        credentials = {"email": "", "password": ""}
        try:
            with open(self.config_path, "r") as f:
                content = f.read()
                email_match = re.search(r"email\s*=\s*(.+)", content)
                password_match = re.search(r"password\s*=\s*(.+)", content)
                if email_match:
                    credentials["email"] = email_match.group(1).strip()
                if password_match:
                    credentials["password"] = password_match.group(1).strip()
        except FileNotFoundError:
            print("login.cfg not found")
        except Exception as e:
            print(f"Error reading login.cfg: {e}")
        return credentials

    def save_credentials(self, email, password):
        """Save email and password to login.cfg."""
        try:
            with open(self.config_path, "w") as f:
                f.write(f"email = {email}\n")
                f.write(f"password = {password}\n")
            print(f"Credentials saved to {self.config_path}")
            self.label.setText("Credentials saved successfully")
        except Exception as e:
            print(f"Error saving login.cfg: {e}")
            self.label.setText(f"Error saving credentials: {e}")

    def prompt_credentials(self):
        """Prompt user for email and password with themed dialogs."""
        email_dialog = CredentialDialog(self, "Login Credentials", "Enter your 3dsky.org email:")
        if email_dialog.exec() != QDialog.DialogCode.Accepted:
            self.label.setText("Email input canceled")
            return None, None
        email = email_dialog.get_text().strip()
        if not email:
            self.label.setText("Email cannot be empty")
            return None, None

        password_dialog = CredentialDialog(self, "Login Credentials", "Enter your 3dsky.org password:")
        if password_dialog.exec() != QDialog.DialogCode.Accepted:
            self.label.setText("Password input canceled")
            return None, None
        password = password_dialog.get_text().strip()
        if not password:
            self.label.setText("Password cannot be empty")
            return None, None

        return email, password

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasHtml():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls() and not mime_data.hasHtml():
            url = mime_data.urls()[0]
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.rar', '.zip', '.7z')):
                    self.handle_archive_drop(file_path)
                elif file_path.lower().endswith(('.jpg', '.jpeg', '.webp', '.png')):
                    self.handle_image_drop(file_path)
                else:
                    self.label.setText("Please drag a .rar, .zip, .7z, or image file (.jpg, .jpeg, '.webp', .png)")
            else:
                self.label.setText("Dropped URL is not a local file")
        elif mime_data.hasHtml():
            self.handle_webpage_element_drop(mime_data)
        else:
            self.label.setText("No usable data dropped")

    def update_history(self, new_url):
        if self.current_index < len(self.url_history) - 1:
            self.url_history = self.url_history[:self.current_index + 1]
        if not self.url_history or self.url_history[-1] != new_url:
            self.url_history.append(new_url)
            self.current_index = len(self.url_history) - 1
        self.back_button.setEnabled(self.current_index > 0)

    def open_login(self):
        # Load credentials from login.cfg
        self.credentials = self.load_credentials()
        
        # If credentials are missing or empty, prompt for them
        if not self.credentials["email"] or not self.credentials["password"]:
            email, password = self.prompt_credentials()
            if email and password:
                self.credentials["email"] = email
                self.credentials["password"] = password
                self.save_credentials(email, password)
            else:
                return  # Exit if credentials weren't provided

        login_url = "https://3dsky.org/auth/login?referer_url=%2F"
        self.web_view.setUrl(QUrl(login_url))
        self.update_history(login_url)
        self.web_view.loadFinished.connect(self.auto_fill_login)

    def auto_fill_login(self, ok):
        if ok and "login" in self.web_view.url().toString():
            QTimer.singleShot(1000, self.fill_login_fields)
        self.web_view.loadFinished.disconnect(self.auto_fill_login)

    def fill_login_fields(self):
        email = self.credentials["email"]
        password = self.credentials["password"]
        js_code = f"""
            var emailField = document.getElementById('inputEmail');
            var passwordField = document.getElementById('inputPassword');
            emailField.value = '{email}';
            passwordField.value = '{password}';
            var inputEvent = new Event('input', {{ bubbles: true }});
            emailField.dispatchEvent(inputEvent);
            passwordField.dispatchEvent(inputEvent);
            var changeEvent = new Event('change', {{ bubbles: true }});
            emailField.dispatchEvent(changeEvent);
            passwordField.dispatchEvent(changeEvent);
            var loginButton = document.querySelector('button[type="submit"]');
            if (loginButton && !loginButton.disabled) {{
                loginButton.click();
                console.log('Login button clicked');
            }} else {{
                console.log('Login button not found or still disabled');
            }}
        """
        self.web_view.page().runJavaScript(js_code)
        print(f"Filled login fields with email: {email} and attempted to click the login button")

    def open_provarch(self):
        patreon_url = "https://www.patreon.com/c/Provarch"
        webbrowser.open(patreon_url)

    def open_youtube(self):
        provarch_ytube_url = "https://www.youtube.com/@provarch"
        webbrowser.open(provarch_ytube_url)

    def open_discord(self):
        discord_url = "https://discord.gg/C7NJWgPCaH"
        webbrowser.open(discord_url)

    def open_tutorial(self):
        skynizer_tuto_url = "https://www.youtube.com/watch?v=8xYhKv1t4Hw"
        webbrowser.open(skynizer_tuto_url)

    def refresh_model_list(self, directory):
        """Refresh the model_list based on current directory contents."""
        archive_extensions = ('.rar', '.zip', '.7z')
        self.model_list = [
            f for f in directory.glob("*")
            if f.suffix.lower() in archive_extensions and f.is_file() and not self.sky_regex.match(f.name)
        ]
        self.model_list.sort(key=lambda x: x.name)
        # Reset current_model_index if out of bounds
        if self.current_model_index >= len(self.model_list):
            self.current_model_index = max(0, len(self.model_list) - 1)
        if self.current_model_index < 0 and self.model_list:
            self.current_model_index = 0

    def get_model_names(self):
        if not self.model_list:
            return "None", "None", "None"
        
        # Filter out files matching sky_regex
        valid_models = [m for m in self.model_list if not self.sky_regex.match(m.name)]
        if not valid_models:
            return "None", "None", "None"
        
        # Adjust current_model_index to point to a valid model
        if self.current_model_index < 0 or self.current_model_index >= len(self.model_list):
            self.current_model_index = 0
        
        # Map original index to valid_models index
        current_original = self.model_list[self.current_model_index]
        try:
            current_valid_index = valid_models.index(current_original)
        except ValueError:
            current_valid_index = 0 if valid_models else -1
        
        if current_valid_index == -1:
            return "None", "None", "None"
        
        current_model = valid_models[current_valid_index].stem
        prev_index = (current_valid_index - 1) % len(valid_models) if valid_models else 0
        previous_model = valid_models[prev_index].stem if valid_models else "None"
        next_index = (current_valid_index + 1) % len(valid_models) if valid_models else 0
        next_model = valid_models[next_index].stem if valid_models else "None"
        
        return previous_model, current_model, next_model

    def sanitize_search_string(self, search_str):
        search_str = search_str.replace("3d-model>", "").replace("_", " ").replace("-", " ")
        sanitized = " ".join(part for part in search_str.split() if part)
        return sanitized

    def display_image(self, image_path):
        self.current_image_path = image_path
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Calculate overscan dimensions (110% of 512x512)
            overscan_factor = 1.10  # 10% overscan
            target_width = int(512 * overscan_factor)
            target_height = int(512 * overscan_factor)

            # Scale the pixmap with overscan, preserving aspect ratio
            scaled_pixmap = pixmap.scaled(
                target_width, target_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # Create a rectangle to crop the center of the scaled image to 512x512
            cropped_pixmap = scaled_pixmap.copy(
                (scaled_pixmap.width() - 512) // 2,  # x offset to center
                (scaled_pixmap.height() - 512) // 2,  # y offset to center
                512,  # width
                512   # height
            )
            self.image_label.setPixmap(cropped_pixmap)
        else:
            self.image_label.clear()
            self.label.setText(f"Failed to load image: {image_path.name}")
        self.update_image()

    def update_image(self):
        if not self.current_image_path:
            return
        pixmap = QPixmap(str(self.current_image_path))
        if not pixmap.isNull():
            available_width = self.image_label.width()
            available_height = self.image_label.height()
            scaled_pixmap = pixmap.scaled(
                available_width, available_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.update()
            self.setMinimumSize(800, 600)
        else:
            self.image_label.clear()
            self.label.setText(f"Failed to load image: {self.current_image_path.name}")

        
            
    def update_button_positions(self):
        """Position the overlay buttons on the image."""
        container_width = self.image_container_widget.width()
        container_height = self.image_container_widget.height()
        button_size = 30
        margin = 10

        # Position prev button on the left center
        self.prev_preview_button.move(margin, (container_height - button_size) // 2)

        # Position next button on the right center
        self.next_preview_button.move(container_width - button_size - margin, (container_height - button_size) // 2)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()
        self.update_button_positions()  # Update button positions when resizing
        if hasattr(self, 'resize_grip'):
            self.resize_grip.show()

    def rename_files(self, downloaded_file):
        directory = self.last_archive_path.parent
        new_base_name = downloaded_file.stem
        new_archive_path = directory / f"{new_base_name}{self.last_archive_path.suffix}"
        
        # Rename archive
        os.rename(self.last_archive_path, new_archive_path)
        self.last_archive_path = new_archive_path
        
        # Rename the single remaining preview (downloaded_file)
        new_preview_path = directory / f"{new_base_name}{downloaded_file.suffix}"
        os.rename(downloaded_file, new_preview_path)
        
        # Update state
        self.preview_files = [new_preview_path]
        self.main_preview = new_preview_path
        self.model_name = new_base_name
        self.label.setText(f"Renamed to: {new_base_name}")

    def open_archive(self):
        if not self.last_archive_path or not self.last_archive_path.exists():
            self.label.setText("No archive to open")
            return
        try:
            if sys.platform == "win32":
                os.startfile(self.last_archive_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.last_archive_path])
            else:
                subprocess.run(["xdg-open", self.last_archive_path])
            self.label.setText(f"Opened archive: {self.last_archive_path.name}")
        except Exception as e:
            self.label.setText(f"Failed to open archive: {e}")

    def move_to_non_sky(self):
        if not self.last_archive_path or not self.last_archive_path.exists():
            self.label.setText("No archive to move")
            return
        
        directory = self.last_archive_path.parent
        non_sky_dir = directory / "__non-sky"
        try:
            if not non_sky_dir.exists():
                non_sky_dir.mkdir()
            
            new_archive_path = non_sky_dir / self.last_archive_path.name
            shutil.move(str(self.last_archive_path), str(new_archive_path))
            
            for preview in self.preview_files:
                if preview.exists():
                    new_preview_path = non_sky_dir / preview.name
                    shutil.move(str(preview), str(new_preview_path))
            
            self.label.setText(f"Moved {self.last_archive_path.name} and previews to __non-sky")
            
            # Refresh model_list after moving
            self.refresh_model_list(directory)
            
            if not self.model_list:
                self.label.setText("No more models to recognize")
                self.image_label.clear()
                self.last_archive_path = None
                self.preview_files = []
                self.main_preview = None
                self.current_model_index = -1
                self.back_button.setEnabled(False)
                self.next_button.setEnabled(False)
                self.check_button.setEnabled(False)
                self.non_button.setEnabled(False)
                self.thrash_button.setEnabled(False)
                return
            
            # Adjust index and display next model
            if self.current_model_index >= len(self.model_list):
                self.current_model_index = len(self.model_list) - 1
            self.display_next_model()
            
        except Exception as e:
            self.label.setText(f"Failed to move files: {e}")

    def move_to_thrash(self):
        if not self.last_archive_path or not self.last_archive_path.exists():
            self.label.setText("No archive to move")
            return
        
        directory = self.last_archive_path.parent
        thrash_dir = directory / "__thrash"
        try:
            if not thrash_dir.exists():
                thrash_dir.mkdir()
            
            new_archive_path = thrash_dir / self.last_archive_path.name
            shutil.move(str(self.last_archive_path), str(new_archive_path))
            
            for preview in self.preview_files:
                if preview.exists():
                    new_preview_path = thrash_dir / preview.name
                    shutil.move(str(preview), str(new_preview_path))
            
            self.label.setText(f"Moved {self.last_archive_path.name} and previews to __thrash")
            
            # Refresh model_list after moving
            self.refresh_model_list(directory)
            
            if not self.model_list:
                self.label.setText("No more models to recognize")
                self.image_label.clear()
                self.last_archive_path = None
                self.preview_files = []
                self.main_preview = None
                self.current_model_index = -1
                self.back_button.setEnabled(False)
                self.next_button.setEnabled(False)
                self.check_button.setEnabled(False)
                self.non_button.setEnabled(False)
                self.thrash_button.setEnabled(False)
                return
            
            # Adjust index and display next model
            if self.current_model_index >= len(self.model_list):
                self.current_model_index = len(self.model_list) - 1
            self.display_next_model()
            
        except Exception as e:
            self.label.setText(f"Failed to move files: {e}")

    def show_quit_dialog(self):
        """Show the quit confirmation dialog and close the application if accepted."""
        dialog = ConfirmExitDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.close()
            
    def load_folder(self, folder_path):
        """Load models from the specified folder and display the first one."""
        directory = Path(folder_path)
        self.refresh_model_list(directory)
        
        if not self.model_list:
            self.label.setText("No more models to recognize")
            self.image_label.clear()
            self.last_archive_path = None
            self.preview_files = []
            self.main_preview = None
            self.current_model_index = -1
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.non_button.setEnabled(False)
            self.thrash_button.setEnabled(False)
            return
        
        # Load the first model
        self.current_model_index = 0
        self.last_archive_path = self.model_list[self.current_model_index]
        self.model_name = self.last_archive_path.stem
        
        self.preview_files = [
            f for f in directory.glob(f"{self.model_name}*")
            if f.suffix.lower() in ('.jpg', '.jpeg', '.webp', '.png') and f.is_file()
        ]
        
        if self.preview_files:
            self.preview_files.sort(key=lambda x: x.name)
            self.main_preview = self.preview_files[0]
            prev, curr, nxt = self.get_model_names()
            self.label.setText(f" {curr}")
            self.display_image(self.main_preview)
        else:
            self.main_preview = None
            self.image_label.clear()
            self.label.setText(f"No previews found for model: {self.model_name}")
        
        # Enable navigation buttons if there are multiple models
        self.back_button.setEnabled(len(self.model_list) > 1)
        self.next_button.setEnabled(len(self.model_list) > 1)
        self.check_button.setEnabled(True)
        self.non_button.setEnabled(True)
        self.thrash_button.setEnabled(True)
        
        # Load search URL in web view
        search_query = self.sanitize_search_string(self.model_name)
        search_url = f"https://3dsky.org/3dmodels?query={quote(search_query)}"
        print(f"Loading first model URL: {search_url}")
        self.web_view.setUrl(QUrl(search_url))
        self.update_history(search_url)

    def open_folder(self):
        # Check if a model is already loaded (i.e., last_archive_path exists)
        if self.last_archive_path and self.last_archive_path.parent.exists():
            # Open the current folder in the system file explorer
            folder_path = str(self.last_archive_path.parent)
            try:
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder_path])
                else:
                    subprocess.run(["xdg-open", folder_path])
                self.label.setText(f"Opened folder: {folder_path}")
            except Exception as e:
                self.label.setText(f"Failed to open folder: {e}")
            return
        
        # Prompt for a folder
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder with Model Archives", 
            str(Path.cwd()),  # Default to current working directory
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            self.label.setText("No folder selected")
            return
        
        self.load_folder(folder_path)   

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resize_grip.geometry().contains(event.position().toPoint()):
                self.resizing = True
            else:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.pos()
            self.resize(delta.x(), delta.y())
        elif self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            dialog = ConfirmExitDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.close()
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DropWidget()
    window.show()
    sys.exit(app.exec())
