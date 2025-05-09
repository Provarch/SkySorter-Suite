import os
import sys
import json
import webbrowser
from pathlib import Path
import subprocess
import io
import socket
import time
import ctypes
from ctypes import wintypes
import shutil
import win32com.client
import platform
import uuid
import hashlib
from __button_set import ButtonSet
import re
from __usage_button import UsageButton

# Get the application base directory (script directory for .py files)
app_dir = Path(os.path.dirname(os.path.abspath(__file__)))

# Now import PyQt6 directly
try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QPushButton, QLineEdit, QTextEdit, QLabel,
                                QFileDialog, QToolButton, QGraphicsDropShadowEffect, QDialog)
    from PyQt6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent
    from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer, QMimeData
except ImportError as e:
    print(f"PyQt6 import error: {e}")
    sys.exit(1)
    


def resolve_shortcut_alternative(lnk_path):
    """Alternative method to resolve shortcuts using PowerShell"""
    try:
        # PowerShell command to get shortcut target
        ps_command = f'(New-Object -ComObject WScript.Shell).CreateShortcut("{lnk_path}").TargetPath'
        result = subprocess.run(['powershell', '-Command', ps_command], 
                              capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        if result.returncode == 0:
            target_path = result.stdout.strip()
            if os.path.exists(target_path) and os.path.isdir(target_path):
                return target_path
    except Exception as e:
        print(f"Error resolving shortcut with PowerShell: {e}")
    return None

def resolve_shortcut(lnk_path):
    """Try multiple methods to resolve a Windows shortcut (.lnk) file to its target path"""
    # First try with win32com if available
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target_path = shortcut.Targetpath
        if os.path.exists(target_path) and os.path.isdir(target_path):
            return target_path
    except ImportError:
        print("win32com not available, trying alternative method...")
    except Exception as e:
        print(f"Error with win32com method: {e}")
    
    # If win32com fails or is not available, try PowerShell method
    return resolve_shortcut_alternative(lnk_path)

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

class DragDropLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            # Get the first dropped path
            path = urls[0].toLocalFile()
            
            # Check if it's a .lnk file
            if path.lower().endswith('.lnk') and os.path.exists(path):
                resolved_path = resolve_shortcut(path)
                if resolved_path:
                    path = resolved_path
                else:
                    print(f"Could not resolve shortcut: {path}")
                    return  # Skip if we couldn't resolve the shortcut
            
            # For regular folders, check if they exist
            if os.path.exists(path) and os.path.isdir(path):
                # Convert forward slashes to backward slashes for Windows consistency
                normalized_path = path.replace('/', '\\')
                self.setText(normalized_path)
                # Trigger textChanged signal to save config
                self.textChanged.emit(normalized_path)

class MainWindow(QMainWindow):
    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'button_set'):
            self.button_set.update_dropdown_position()
    def __init__(self):
        super().__init__()
        self.PADDING_OUTER = 5
        self.PADDING_INNER = 5
        
        # Get the application base directory
        self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        print(f"Running as script from {self.app_dir}")

        # Initialize UID as None until extracted from console
        self.user_uid = None  # Will be set when parsed from console output

        
        # Set up window icon
        icon_path = find_app_icon(self.app_dir)
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
            print(f"Set window icon to: {icon_path}")
        
        # Only use _internal folder for config
        self.internal_dir = self.app_dir.parent / '_internal'
        self.config_file = self.internal_dir / 'ui.ini'
        
        # Set the _gfx folder path - check all possible locations
        self.gfx_dir = None
        possible_gfx_paths = [
            self.app_dir / '_gfx',                      # Original location
            self.internal_dir / '_gfx',                 # Preferred location
            self.internal_dir / '_internal' / '_gfx',   # Nested location
        ]
        
        for path in possible_gfx_paths:
            if path.exists():
                self.gfx_dir = path
                print(f"Found graphics directory at: {self.gfx_dir}")
                break
                
        if self.gfx_dir is None:
            print("WARNING: Could not find graphics directory!")
            # Fall back to the app directory
            self.gfx_dir = self.app_dir / '_gfx'
        
        # Print paths for debugging
        print(f"Internal directory: {self.internal_dir}")
        print(f"Config file path: {self.config_file}")
        print(f"Graphics directory: {self.gfx_dir}")
        
        # Define path to skySorter.py
        self.sky_sorter_script = self.internal_dir / "__client.py"
        self.skylister_script = self.internal_dir / "__lister.py"
        
        self.setWindowTitle("skySorter")
        self.setMinimumSize(680, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(self.PADDING_OUTER, self.PADDING_OUTER, self.PADDING_OUTER, 0)
        main_layout.setSpacing(self.PADDING_INNER)
        
        content_widget = QWidget(main_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.central_widget = content_widget
        
        # Set up background label with absolute positioning
        background_label = QLabel(content_widget)
        bg_path = self.gfx_dir / "bg_toolkit.png"
        pixmap = QPixmap(str(bg_path))
        scaled_pixmap = pixmap.scaled(700, 700, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x = (690 - scaled_pixmap.width()) // 2
        y = (583 - scaled_pixmap.height()) // 2
        background_label.setGeometry(x, y, scaled_pixmap.width(), scaled_pixmap.height())
        background_label.setPixmap(scaled_pixmap)
        background_label.lower()  # Ensure background is behind all other widgets
        
        title_bar = QWidget()
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar.setStyleSheet("QWidget { background-color: #1e1e1e; color: white; }")
        title_label = QLabel("skySorter")
        title_label.setStyleSheet("padding: 5px;")
        close_button = QPushButton("×")
        minimize_button = QPushButton("−")
        close_button.clicked.connect(self.close)
        minimize_button.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(minimize_button)
        title_bar_layout.addWidget(close_button)
        self.usage_button = UsageButton(self)
        self.current_usage = 0  # Initialize current usage counter
        self.total_usage = 2000  # Default total limit, updated by "All-time usage" message
        
        top_section = self.setup_top_section(self.app_dir)
        middle_section = self.setup_middle_section(self.app_dir)
        process_widget = self.setup_process_widget()
        console_container = self.setup_console()
        
        # Create a container for the hero overlay
        hero_container = QWidget()
        hero_layout = QVBoxLayout(hero_container)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        process_hover_button = QPushButton("Process Folders")
        process_hover_button.setFixedSize(100, 40)
        process_hover_button.setStyleSheet("""
            QPushButton { background-color: rgba(255, 255, 255, 0.1); color: white; border: 2px solid rgba(255, 255, 255, 0.7); border-radius: 20px; padding: 5px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); border: 2px solid white; }
        """)
        process_hover_button.hide()
        hero_container.enterEvent = lambda event: process_hover_button.show()
        hero_container.leaveEvent = lambda event: process_hover_button.hide()
        process_hover_button.enterEvent = lambda event: process_hover_button.show()
        process_hover_button.leaveEvent = lambda event: process_hover_button.hide()
        process_hover_button.clicked.connect(self.run_sky_sorter)
        hero_layout.addWidget(process_hover_button)
        
        # Create a bottom container for path fields and console
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)        
        bottom_layout.addWidget(process_widget)
        bottom_layout.addLayout(console_container)

        # Add sections to content_layout
        content_layout.addWidget(top_section, 0)
        # Optionally remove middle_section if it's empty
        content_layout.addWidget(middle_section, 0)
        content_layout.addWidget(hero_container, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addStretch(1)
        content_layout.addWidget(bottom_container, 0)
        
        # Ensure top_section (which contains ButtonSet and the dropdown) is above the background
        top_section.raise_()
        content_widget.raise_()
        
        main_layout.addWidget(content_widget, 1)
        
        self.setStyleSheet("""
            QWidget { background-color: transparent; }
            QLabel { color: white; }
            QPushButton { background-color: rgba(61, 61, 61, 200); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: rgba(77, 77, 77, 200); }
            QLineEdit { background-color: rgba(61, 61, 61, 200); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
            QTextEdit { background-color: rgba(30, 30, 30, 200); color: white; border: 1px solid #555555; border-radius: 4px; }
        """)
        
        # Initialize QProcess with unbuffered output
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
     
        # Set process to read in unbuffered mode
        process_env = QProcessEnvironment.systemEnvironment()
        process_env.insert("PYTHONUNBUFFERED", "1")
        process_env.insert("PYTHONIOENCODING", "utf-8")
        process_env.insert("PYTHONUTF8", "1")
        self.process.setProcessEnvironment(process_env)

        
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
        # Now that console_output is created, we can load the config
        self.load_config()
        
        self.folder_input1.textChanged.connect(self.save_config)
        self.process_input.textChanged.connect(self.save_config)
        self.apply_saved_config()
        
        self.dragging = False
        self.drag_position = None

    def copy_uid_to_clipboard(self, uid):
        QApplication.clipboard().setText(uid)
        self.console_output.append(f"UID '{uid}' copied to clipboard.")

    def setup_top_section(self, script_dir):
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setSpacing(5)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Column 1: Just the Provarch logo
        logo_container = QWidget()
        logo_container.setFixedWidth(85)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Provarch logo 
        provarch_logo = QToolButton()
        provarch_logo.setFixedSize(85, 85)
        logo_path = self.gfx_dir / "prov_logo_v3.png"
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(105, 105, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            provarch_logo.setIcon(QIcon(scaled_logo))
            provarch_logo.setIconSize(scaled_logo.size())
            provarch_logo.setStyleSheet("""
                QToolButton { background-color: rgba(0, 0, 0, 0); border: none; border-radius: 5px; padding: 3px; }
                QToolButton:hover { background-color: rgba(77, 77, 77, 255); }
            """)
            logo_glow = QGraphicsDropShadowEffect()
            logo_glow.setColor(Qt.GlobalColor.white)
            logo_glow.setBlurRadius(15)
            logo_glow.setOffset(0)
            provarch_logo.setGraphicsEffect(logo_glow)
            logo_glow.setEnabled(False)
            provarch_logo.enterEvent = lambda event: logo_glow.setEnabled(True)
            provarch_logo.leaveEvent = lambda event: logo_glow.setEnabled(False)
            provarch_logo.clicked.connect(lambda: webbrowser.open('https://www.patreon.com/c/Provarch'))
            provarch_logo.setToolTip("<b>Provarch</b><br>Click to visit Patreon page")
        logo_layout.addWidget(provarch_logo)
        
        # Column 2: Just the social buttons 
        social_container = QWidget()
        social_container.setFixedWidth(40)
        social_layout = QVBoxLayout(social_container)
        social_layout.setContentsMargins(10, 0, 0, 0)
        social_layout.setSpacing(2)
        social_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Discord button 
        discord_button = QToolButton()
        discord_button.setFixedWidth(27)
        discord_button.setFixedHeight(27)
        discord_logo_path = self.gfx_dir / "dis_logo+.png"
        if discord_logo_path.exists():
            discord_pixmap = QPixmap(str(discord_logo_path))
            scaled_discord = discord_pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            discord_button.setIcon(QIcon(scaled_discord))
            discord_button.setIconSize(scaled_discord.size())
            discord_button.setStyleSheet("""
                QToolButton { background-color: rgba(0, 0, 0, 0); border: none; border-radius: 5px; padding: 3px; }
                QToolButton:hover { background-color: rgba(77, 77, 77, 255); }
            """)
            discord_glow = QGraphicsDropShadowEffect()
            discord_glow.setColor(Qt.GlobalColor.white)
            discord_glow.setBlurRadius(15)
            discord_glow.setOffset(0)
            discord_button.setGraphicsEffect(discord_glow)
            discord_glow.setEnabled(False)
            discord_button.enterEvent = lambda event: discord_glow.setEnabled(True)
            discord_button.leaveEvent = lambda event: discord_glow.setEnabled(False)
            discord_button.clicked.connect(lambda: webbrowser.open('https://discord.gg/C7NJWgPCaH'))
            discord_button.setToolTip("<b>Discord</b><br>Join our Discord community")
        
        # YouTube button 
        youtube_button = QToolButton()
        youtube_button.setFixedWidth(27)
        youtube_button.setFixedHeight(27)
        youtube_logo_path = self.gfx_dir / "yt_logo.png"
        if youtube_logo_path.exists():
            youtube_pixmap = QPixmap(str(youtube_logo_path))
            scaled_youtube = youtube_pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            youtube_button.setIcon(QIcon(scaled_youtube))
            youtube_button.setIconSize(scaled_youtube.size())
            youtube_button.setStyleSheet("""
                QToolButton { background-color: rgba(0, 0, 0, 0); border: none; border-radius: 5px; padding: 3px; }
                QToolButton:hover { background-color: rgba(77, 77, 77, 255); }
            """)
            youtube_glow = QGraphicsDropShadowEffect()
            youtube_glow.setColor(Qt.GlobalColor.white)
            youtube_glow.setBlurRadius(15)
            youtube_glow.setOffset(0)
            youtube_button.setGraphicsEffect(youtube_glow)
            youtube_glow.setEnabled(False)
            youtube_button.enterEvent = lambda event: youtube_glow.setEnabled(True)
            youtube_button.leaveEvent = lambda event: youtube_glow.setEnabled(False)
            youtube_button.clicked.connect(lambda: webbrowser.open('https://www.youtube.com/@provarch'))
            youtube_button.setToolTip("<b>YouTube</b><br>Visit my channel for guides and updates")
        
        social_layout.addStretch(1)
        social_layout.addWidget(discord_button, 0, Qt.AlignmentFlag.AlignCenter)
        social_layout.addWidget(youtube_button, 0, Qt.AlignmentFlag.AlignCenter)
        social_layout.addStretch(1)
        
        # Paths widget with Sky-Bank Folder and ButtonSet
        paths_widget = QWidget()
        paths_layout = QVBoxLayout(paths_widget)
        paths_layout.setSpacing(5)
        paths_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sky Bank Folder input 
        self.folder_input1 = DragDropLineEdit()
        self.folder_input1.textChanged.connect(lambda text: self.folder_input1.setText(self.remove_quotes_from_path(text)) if '"' in text else None)
        
        folder_widget1 = QWidget()
        folder_layout1 = QHBoxLayout(folder_widget1)
        folder_layout1.setContentsMargins(0, 0, 0, 0)
        folder_layout1.setSpacing(5)
        folder_layout1.addStretch(1)
        folder_label1 = QToolButton()
        folder_label1.setText("Sky-Bank Folder")
        folder_label1.setFixedWidth(150)
        folder_label1.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_label1.clicked.connect(lambda: self.open_explorer(self.folder_input1.text()))
        folder_label1.setStyleSheet("""
            QToolButton { background-color: rgba(30, 30, 30, 200); color: white; padding: 5px; border-radius: 4px; border: none; text-align: left; }
            QToolButton:hover { background-color: rgba(77, 77, 77, 200); }
        """)
        folder_label1.setToolTip("<b>3dsky Bank Folder</b><br>This is the location where your processed models be stored in. Leaving this folder path empty will stop detecting dublicate models")
        
        self.folder_input1.setFixedWidth(320)
        folder_button1 = QPushButton("...")
        folder_button1.setFixedWidth(30)
        folder_button1.clicked.connect(self.select_3dsky_folder)
        folder_layout1.addWidget(folder_label1)
        folder_layout1.addWidget(self.folder_input1)
        folder_layout1.addWidget(folder_button1)
        
        # Add the Sky-Bank Folder widget
        paths_layout.addWidget(folder_widget1)

        # Add the ButtonSet widget (Skynizer, Skydrop, Updates, and UID)
        self.button_set = ButtonSet(self, self.user_uid, self.gfx_dir, self)
        paths_layout.addWidget(self.button_set)
        
        # Add all three columns to the top layout
        top_layout.addWidget(logo_container, 0)
        top_layout.addWidget(social_container, 0)
        top_layout.addWidget(paths_widget, 1)
        
        return top_section

    def setup_process_button(self):
        process_button = QToolButton()
        process_button.setObjectName("processExtraButton")
        process_button.setText("")
        process_button.setFixedSize(350, 140)
        process_button.setCursor(Qt.CursorShape.PointingHandCursor)
        process_button.setStyleSheet("""
            QToolButton { background-color: transparent; border: 2px solid transparent; border-radius: 60px; padding: 0px; margin: 0px; }
            QToolButton:hover { border: 2px solid rgba(255, 255, 255, 0.7); border-radius: 60px; }
            QToolButton:pressed { border: 2px solid white; border-radius: 60px; }
        """)
        # Update tooltip for the process button
        process_button.setToolTip("""
            <b>SkySorter</b><br>
            Works on the unprocessed folder.<br>
            Sorts and organizes 3dsky models based on their IDs.<br>
            Moves models to appropriate categories in the 3dsky bank folder.
        """)
        
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setColor(Qt.GlobalColor.white)
        glow_effect.setBlurRadius(11)
        glow_effect.setOffset(0)
        process_button.setGraphicsEffect(glow_effect)
        process_button.enterEvent = lambda event: glow_effect.setEnabled(True)
        process_button.leaveEvent = lambda event: glow_effect.setEnabled(False)
        
        # Add validation for the process button
        process_button.clicked.connect(self.validate_and_run_sky_sorter)
        
        return process_button
        
    def validate_and_run_sky_sorter(self):
        # Check if unprocessed folder path is valid before running skySorter
        if not self.process_input.text():
            self.console_output.append("Error: Please select an unprocessed folder path first")
            return
        
        # If validation passes, run skySorter
        self.run_sky_sorter()

    def setup_middle_section(self, script_dir):
        middle_section = QWidget()
        middle_layout = QHBoxLayout(middle_section)
        middle_layout.setContentsMargins(5, 1, 5, 1)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(10)

        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(1, 1, 1, 1)

        process_button = self.setup_process_button()

        # Vertical layout for Process and Usage buttons
        middle_container = QVBoxLayout()
        middle_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_container.setContentsMargins(135, 20, 0, 0)
        middle_container.addWidget(process_button)

        # Vertical spacer for up/down nudging
        middle_container.addSpacing(0)  # Adjust this for vertical offset (e.g., 30 for more downward nudge)

        # Horizontal layout for UsageButton with left/right nudging
        usage_button_container = QHBoxLayout()
        usage_button_container.addSpacing(400)  # Adjust this for horizontal offset (e.g., 50 for more rightward nudge)
        usage_button_container.addWidget(self.usage_button)
        usage_button_container.addStretch()  # Push UsageButton to the left within its container

        middle_container.addLayout(usage_button_container)

        buttons_layout.addLayout(middle_container)

        central_layout.addWidget(buttons_widget, 1)
        middle_layout.addStretch(1)
        middle_layout.addWidget(central_widget)
        middle_layout.addStretch(1)
        return middle_section

    def setup_process_widget(self):
        process_widget = QWidget()
        process_layout = QHBoxLayout(process_widget)
        process_layout.setContentsMargins(10, 5, 20, 5)
        
        process_button_tags = QToolButton()
        process_button_tags.setText("Unprocessed(Raw) folder")
        process_button_tags.clicked.connect(lambda: self.open_explorer(self.process_input.text()))
        process_button_tags.setStyleSheet("""
            QToolButton { background-color: rgba(30, 30, 30, 200); color: white; padding: 5px; border-radius: 4px; border: none; }
            QToolButton:hover { background-color: rgba(77, 77, 77, 200); }
        """)
        self.process_input = DragDropLineEdit()
        self.process_input.setFixedWidth(360)
        # Add event handler to remove quotes from pasted paths
        self.process_input.textChanged.connect(lambda text: self.process_input.setText(self.remove_quotes_from_path(text)) if '"' in text else None)
        
        kill_process_button = QPushButton("Kill Process")
        kill_process_button.setFixedSize(100, 30)  
        kill_process_button.setStyleSheet("""
            QPushButton { background-color: rgba(100, 30, 30, 100); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: rgba(255, 50, 50, 200); }
        """)
        kill_process_button.clicked.connect(self.kill_process)
        
        process_button = QPushButton("...")
        process_button.setFixedWidth(30)
        process_button.clicked.connect(self.select_process_path)
        
        process_layout.addStretch(1)
        process_layout.addWidget(process_button_tags)
        process_layout.addWidget(kill_process_button)  # Added Kill Process button here
        process_layout.addWidget(self.process_input)
        process_layout.addWidget(process_button)
        return process_widget

    def setup_console(self):
            console_output = QTextEdit()
            console_output.setPlaceholderText("Console output")
            console_output.setReadOnly(False)
            console_output.setFixedHeight(250)
            console_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            console_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            console_output.setStyleSheet("""
                QTextEdit { 
                    background-color: rgba(20, 20, 20, 0.8); 
                    color: #00ff00; 
                    border: 1px solid rgba(40, 40, 40, 0.8); 
                    border-radius: 10px; 
                    padding: 10px; 
                    font-family: Consolas; 
                    font-size: 11px; 
                }
                QScrollBar:vertical { 
                    background-color: rgba(30, 30, 30, 0.5); 
                    width: 12px;  /* Increased width for better visibility */
                    border-radius: 6px; 
                    margin: 0px; 
                }
                QScrollBar::handle:vertical { 
                    background-color: rgba(60, 60, 60, 0.8); 
                    border-radius: 6px; 
                    min-height: 20px;  /* Ensure handle doesn't shrink too small */
                }
                QScrollBar::handle:vertical:hover { 
                    background-color: rgba(80, 80, 80, 0.9);  /* Slightly lighter on hover */
                }
                QScrollBar::add-line:vertical, 
                QScrollBar::sub-line:vertical { 
                    height: 0px; 
                }
                QScrollBar::up-arrow:vertical, 
                QScrollBar::down-arrow:vertical { 
                    height: 0px; 
                }
            """)
            
            console_output.keyPressEvent = lambda event: self.handle_console_input(event, console_output)
            
            console_container = QHBoxLayout()
            console_container.setContentsMargins(0, 0, 0, 5)
            console_container.addWidget(console_output)
            self.console_output = console_output
            return console_container

    def handle_console_input(self, event, console):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Get cursor and move to end
            cursor = console.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            
            # Get the last line
            cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
            current_line = cursor.selectedText()
            
            # Extract only the user input after the prompt
            if "Enter your choice (c/i/r):" in current_line:
                current_input = current_line.split(":")[-1].strip()
            else:
                current_input = current_line.strip()
            
            if self.process and self.process.state() == QProcess.ProcessState.Running:
                # Write only the input character to the process
                self.process.write(f"{current_input}\n".encode())
                self.process.waitForBytesWritten()
                
                # Add a new line in the console
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertText("\n")
            
        else:
            # For all other keys, use default handling
            QTextEdit.keyPressEvent(console, event)
            
    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode('utf-8', errors='replace')
        cursor = self.console_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        self.console_output.insertPlainText(stdout)
        
        # Parse UID, usage limit, and monthly usage messages
        uid_pattern = r"Usage limit: uid:([0-9a-f]{16}):"
        usage_pattern = r"All-time usage: (\d+)/(\d+) requests"
        monthly_usage_pattern = r"Monthly usage: (\d+)/(\d+) requests"
        success_pattern = r"✅ Processed [^\s]+ successfully\."
        for line in stdout.splitlines():
            # Extract UID
            uid_match = re.search(uid_pattern, line)
            if uid_match:
                new_uid = uid_match.group(1)  # Extract the UID
                if new_uid != self.user_uid:  # Only update if the UID has changed
                    self.user_uid = new_uid
                    self.button_set.update_uid(self.user_uid)  # Use ButtonSet's update method to handle masking
                    self.console_output.append(f"Extracted UID: {self.user_uid}")
                    self.save_config()  # Save the config to update ui.ini
            
            # Check for All-time usage message
            usage_match = re.search(usage_pattern, line)
            if usage_match:
                current, total = map(int, usage_match.groups())
                self.current_usage = max(self.current_usage, current)
                self.total_usage = total
                self.usage_button.update_usage(line)  # Pass the full line
            
            # Check for Monthly usage message
            monthly_match = re.search(monthly_usage_pattern, line)
            if monthly_match:
                current, total = map(int, monthly_match.groups())
                self.current_usage = max(self.current_usage, current)
                self.total_usage = total  # Update total_usage with monthly limit
                self.usage_button.update_usage(line)  # Pass the full line
            
            # Check for successful process completion
            success_match = re.search(success_pattern, line)
            if success_match:
                self.current_usage += 1
                self.usage_button.update_usage(f"Monthly usage: {self.current_usage}/{self.total_usage} requests")
        
        cursor.movePosition(cursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )
        QApplication.processEvents()

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode('utf-8', errors='replace')
        cursor = self.console_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        self.console_output.insertHtml(f'<span style="color: red;">{stderr}</span>')
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

        
    def load_config(self):
        default_config = {'3dsky_folder': '', 'process_models_path': '', 'alias': '', 'user_uid': ''}
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    self.config = {
                        '3dsky_folder': self.config.get('3dsky_folder', ''),
                        'process_models_path': self.config.get('process_models_path', ''),
                        'alias': self.config.get('alias', ''),
                        'user_uid': self.config.get('user_uid', '')
                    }
                    # Apply loaded UID if available
                    if self.config['user_uid']:
                        self.user_uid = self.config['user_uid']
                        self.button_set.update_uid(self.user_uid)  # Use ButtonSet's update method to handle masking
            else:
                self.console_output.append(f"Warning: Config file not found at {self.config_file}")
                print(f"Warning: Config file not found at {self.config_file}")
                self.config = default_config
        except Exception as e:
            self.console_output.append(f"Error loading config: {e}")
            print(f"Error loading config: {e}")
            self.config = default_config

    def save_config(self):
        try:
            config_data = {
                '3dsky_folder': self.folder_input1.text(),
                'process_models_path': self.process_input.text(),
                'alias': self.button_set.get_alias(),
                'user_uid': self.user_uid if self.user_uid else ''
            }
            
            # Ensure the internal directory exists
            self.internal_dir.mkdir(parents=True, exist_ok=True)
            
            # If config file exists, read it to preserve other settings
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    full_config = json.load(f)
                    
                # Update only the settings we manage
                full_config.update(config_data)
            else:
                # If config file doesn't exist, create a new one with just our data
                full_config = config_data
                self.console_output.append(f"Creating new config file at {self.config_file}")
                    
            # Write the config data
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(full_config, f, indent=4)
                    
        except Exception as e:
            if hasattr(self, 'console_output'):
                self.console_output.append(f"Error saving config: {e}")
            print(f"Error saving config: {e}")
            
    def apply_saved_config(self):
        if hasattr(self, 'config'):
            self.folder_input1.setText(self.config.get('3dsky_folder', ''))
            self.process_input.setText(self.config.get('process_models_path', ''))
            self.button_set.set_alias(self.config.get('alias', ''))
            if self.config.get('user_uid', ''):
                self.user_uid = self.config['user_uid']
                self.button_set.update_uid(self.user_uid)  # Use ButtonSet's update method to handle masking

    def select_3dsky_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select 3dsky Folder", self.config.get('3dsky_folder', ''))
        if folder:
            self.folder_input1.setText(folder)
            self.save_config()

    def select_process_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Process Models Path", self.config.get('process_models_path', ''))
        if folder:
            self.process_input.setText(folder)
            self.save_config()

    def remove_quotes_from_path(self, text):
        """Remove quotes from the beginning and end of a path string"""
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        return text

    def run_sky_sorter(self):
        unprocessed_path = self.process_input.text()
        sky_bank_path = self.folder_input1.text()
        alias = self.button_set.get_alias()
        
        if not unprocessed_path:
            self.console_output.append("Error: Please select an unprocessed folder path first")
            return
        
        try:
            # Check if the script exists
            if not self.sky_sorter_script.exists():
                self.console_output.append(f"Error: skySorter.py not found at {self.sky_sorter_script}")
                return
                
            # Clear the console output
            self.console_output.clear()
            
            # Run the Python script using QProcess to capture output
            self.console_output.append(f"Launching: Python with {self.sky_sorter_script} {unprocessed_path}")
            if sky_bank_path:
                self.console_output.append(f"Sky bank path provided: {sky_bank_path}")
            if alias and alias.strip() != "patreon alias...":
                self.console_output.append(f"Alias provided: {alias}")
            
            # Configure the process
            self.process.setWorkingDirectory(str(self.app_dir))
            
            # Set up the command and arguments - run with Python interpreter
            program = str(sys.executable)  # Use the current Python interpreter
            arguments = [str(self.sky_sorter_script), unprocessed_path]
            
            # Add sky bank path as second argument if provided
            if sky_bank_path:
                arguments.append(sky_bank_path)
            
            # Add alias as third argument if it exists and is not the default placeholder
            if alias and alias.strip() != "patreon alias...":
                arguments.append(alias)
            
            # Start the process
            self.process.start(program, arguments)
            
        except Exception as e:
            self.console_output.append(f"Error running SkySorter: {str(e)}")
            
    def run_skylister(self):
        sky_bank_path = self.folder_input1.text()
        
        if not sky_bank_path:
            self.console_output.append("Error: Please select a Sky Bank folder path first")
            return
        
        try:
            # Check if the script exists
            if not self.skylister_script.exists():
                self.console_output.append(f"Error: Skylister script not found at {self.skylister_script}")
                return
                
            # Clear the console output
            self.console_output.clear()
            
            # Run the Python script using QProcess to capture output
            self.console_output.append(f"Launching: Python with {self.skylister_script} {sky_bank_path}")
            
            # Configure the process
            self.process.setWorkingDirectory(str(self.app_dir))
            
            # Set up the command and arguments - run with Python interpreter
            program = str(sys.executable)  # Use the current Python interpreter
            arguments = [str(self.skylister_script), sky_bank_path]
            
            # Start the process
            self.process.start(program, arguments)
            
        except Exception as e:
            self.console_output.append(f"Error running Skylister: {str(e)}")
    def process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.console_output.append("\nProcess completed successfully.")
        else:
            self.console_output.append(f"\nProcess finished with exit code: {exit_code}")
    def kill_process(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            self.console_output.append("Attempting to terminate SkySorter client process...")
            
            # Wait for the client to terminate and give it a chance to shut down the bridge
            QTimer.singleShot(2000, self.check_and_kill_bridge)  # Check after 2 seconds
        else:
            self.console_output.append("No running client process to kill.")
            # Even if no client is running, check for a lingering bridge
            self.check_and_kill_bridge()

    def check_and_kill_bridge(self):
        # Check client termination status
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()  # Force kill the client if still running
            self.console_output.append("Client process forcibly killed.")

        # Attempt to gracefully shut down the bridge via TCP
        bridge_port = 8888  # Match the PORT from client.py and __bridge.py
        shutdown_acknowledged = False  # Initialize the variable
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", bridge_port))
                s.send("bridge_shutdown".encode())
                response = s.recv(1024).decode()
                if response == "bridge_closing":
                    self.console_output.append("✅ Bridge shutdown command acknowledged.")
                    shutdown_acknowledged = True
                else:
                    self.console_output.append(f"⚠️ Unexpected bridge response: {response}")
        except ConnectionRefusedError:
            self.console_output.append("ℹ️ No bridge detected on port 8888, assuming already terminated.")
            return  # No bridge running, so we’re done
        except Exception:
            pass
            

        # If shutdown was acknowledged, give the bridge time to exit and verify
        if shutdown_acknowledged:
            time.sleep(4)  # Wait longer to allow bridge to fully shut down
            retries = 3
            for attempt in range(retries):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)  # Increase timeout for verification
                        s.connect(("127.0.0.1", bridge_port))
                        s.close()
                        self.console_output.append(f"⚠️ Bridge still running after shutdown command (attempt {attempt + 1}/{retries}).")
                        if attempt == retries - 1:
                            self.console_output.append("❌ Bridge failed to shut down gracefully.")
                            self.force_kill_bridge()
                        time.sleep(1)  # Wait between retries
                except ConnectionRefusedError:
                    self.console_output.append("✅ Bridge successfully shut down.")
                    return  # Bridge is confirmed down
                except Exception:
                    pass
            




    def check_process(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()  # Force kill if terminate didn't work
            self.console_output.append("Process forcibly killed.")
        else:
            self.console_output.append("Process has been terminated.")
    def open_explorer(self, path):
        if not path:
            self.console_output.append("Error: No path specified")
            return
        try:
            path_obj = Path(path)
            if path_obj.exists():
                # Start the explorer process
                os.startfile(str(path_obj))
                
                # Wait a moment for the window to appear
                time.sleep(0.1)
                
                # Determine which folder is being opened
                if path == self.process_input.text():
                    # Process folder - position on the left
                    self.resize_and_position_explorer_window(600, 900, "left")
                else:
                    # Sky bank or non-sky bank folder - position on the right
                    self.resize_and_position_explorer_window(600, 900, "right")
            else:
                self.console_output.append(f"Error: Path does not exist: {path}")
        except Exception as e:
            self.console_output.append(f"Error opening explorer: {str(e)}")
            
    def resize_and_position_explorer_window(self, width, height, position="right"):
        """Resize and position File Explorer windows to the specified side of the screen."""
        try:
            # Windows API constants
            SW_RESTORE = 9
            HWND_TOP = 0
            SWP_SHOWWINDOW = 0x0040
            
            # Get screen dimensions
            GetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
            screen_width = GetSystemMetrics(0)  # SM_CXSCREEN
            screen_height = GetSystemMetrics(1)  # SM_CYSCREEN
            
            # Calculate position based on requested side
            if position == "left":
                x = 10  # Left side with a small margin
            else:  # "right" is default
                x = screen_width - width - 10  # Right side with a small margin
                
            y = (screen_height - height) // 2  # Center vertically
            
            # Find the most recently opened explorer window
            # Explorer windows have class name "CabinetWClass"
            hwnd = ctypes.windll.user32.FindWindowW("CabinetWClass", None)
            
            if hwnd:
                # Restore the window if minimized
                ShowWindow = ctypes.windll.user32.ShowWindow
                ShowWindow(hwnd, SW_RESTORE)
                
                # Set window position and size
                SetWindowPos = ctypes.windll.user32.SetWindowPos
                SetWindowPos(hwnd, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW)
            else:
                # Try to find by enumerating all windows with the explorer class
                def enum_windows_callback(hwnd, lParam):
                    # Check if this is an explorer window
                    class_name = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetClassNameW(hwnd, class_name, 256)
                    
                    if class_name.value == "CabinetWClass":
                        # Check if the window is visible
                        if ctypes.windll.user32.IsWindowVisible(hwnd):
                            # Restore the window if minimized
                            ShowWindow = ctypes.windll.user32.ShowWindow
                            ShowWindow(hwnd, SW_RESTORE)
                            
                            # Set window position and size
                            SetWindowPos = ctypes.windll.user32.SetWindowPos
                            SetWindowPos(hwnd, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW)
                            return False  # Stop enumeration after finding one
                    return True  # Continue enumeration
                
                # Define callback type
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                # Enumerate windows
                ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        except Exception as e:
            print(f"Error positioning explorer window: {str(e)}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.position().toPoint())
            if not widget or not any(isinstance(widget, t) for t in (QPushButton, QToolButton, QLineEdit, QTextEdit)):
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            dialog = ConfirmExitDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.close()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def closeEvent(self, event):
        # Accept the close event
        event.accept()

# Function to find the best icon
def find_app_icon(app_dir):
    # Define icon names in order of preference
    icon_names = [
        "ui_icon.ico",
        "sky_toolkit.ico",
        "icon.ico"
    ]
    
    # Primary location is _internal/_gfx
    primary_path = app_dir.parent / '_internal' / '_gfx'
    fallback_path = app_dir.parent / '_gfx'
    
    # First try to find *ui.ico files (case insensitive) in primary location
    if primary_path.exists():
        ico_files = [f for f in primary_path.iterdir() if f.is_file()]
        ui_icons = [f for f in ico_files if f.name.lower().endswith('ui.ico')]
        if ui_icons:
            return ui_icons[0]
    
    # Try each preferred icon name in both locations
    for icon_name in icon_names:
        # Try primary location first
        icon_path = primary_path / icon_name
        if icon_path.exists():
            return icon_path
            
        # Try fallback location
        icon_path = fallback_path / icon_name
        if icon_path.exists():
            return icon_path
    
    # If no preferred icons found, look for any .ico file
    if primary_path.exists():
        ico_files = list(primary_path.glob('*.ico'))
        if ico_files:
            return ico_files[0]
            
    if fallback_path.exists():
        ico_files = list(fallback_path.glob('*.ico'))
        if ico_files:
            return ico_files[0]
    
    # If we get here, no icon was found - prepare warning message
    warning_msg = "Warning: No suitable icon found.\n"
    warning_msg += f"Searched for icons in this order:\n"
    warning_msg += f"1. Any *ui.ico file in {primary_path}\n"
    for icon_name in icon_names:
        warning_msg += f"2. {icon_name} in {primary_path}\n"
        warning_msg += f"3. {icon_name} in {fallback_path}\n"
    warning_msg += f"4. Any .ico file in {primary_path}\n"
    warning_msg += f"5. Any .ico file in {fallback_path}\n"
    
    print(warning_msg)
    return None

if __name__ == '__main__':
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Set application-wide attributes before creating any windows
    app.setStyle('Fusion')  # Use Fusion style for better icon handling
    
    # Find and set the application icon
    icon_path = find_app_icon(app_dir)
    if icon_path:
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)  # Set for application/taskbar
    
    # Create and set up main window
    window = MainWindow()
    
    # Position the window higher on the screen
    screen = app.primaryScreen().geometry()
    window.show()
    frame_geom = window.frameGeometry()
    window_width = window.width()
    window_height = window.height()
    x = (screen.width() - window_width) // 2 
    y = (screen.height() - window_height) // 2 - 50
    window.move(x, y)
    
    # Show the window and start the event loop
    window.show()
    sys.exit(app.exec())
