from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import QMimeData
import os
import subprocess
import win32com.client
from pathlib import Path

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
            path = urls[0].toLocalFile()
            if path.lower().endswith('.lnk') and os.path.exists(path):
                resolved_path = resolve_shortcut(path)
                if resolved_path:
                    path = resolved_path
                else:
                    print(f"Could not resolve shortcut: {path}")
                    return
            if os.path.exists(path) and os.path.isdir(path):
                normalized_path = path.replace('/', '\\')
                self.setText(normalized_path)
                self.textChanged.emit(normalized_path)

def get_main_stylesheet():
    return """
        QWidget { background-color: transparent; }
        QLabel { color: white; }
        QPushButton { background-color: rgba(61, 61, 61, 200); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
        QPushButton:hover { background-color: rgba(77, 77, 77, 200); }
        QLineEdit { background-color: rgba(61, 61, 61, 200); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
        QTextEdit { background-color: rgba(30, 30, 30, 200); color: white; border: 1px solid #555555; border-radius: 4px; }
    """

def resolve_shortcut_alternative(lnk_path):
    try:
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
    return resolve_shortcut_alternative(lnk_path)

def find_app_icon(app_dir):
    icon_names = [
        "ui_icon.ico",
        "sky_toolkit.ico",
        "icon.ico"
    ]
    primary_path = app_dir.parent / '_internal' / '_gfx'
    fallback_path = app_dir.parent / '_gfx'
    
    if primary_path.exists():
        ico_files = [f for f in primary_path.iterdir() if f.is_file()]
        ui_icons = [f for f in ico_files if f.name.lower().endswith('ui.ico')]
        if ui_icons:
            return ui_icons[0]
    
    for icon_name in icon_names:
        icon_path = primary_path / icon_name
        if icon_path.exists():
            return icon_path
        icon_path = fallback_path / icon_name
        if icon_path.exists():
            return icon_path
    
    if primary_path.exists():
        ico_files = list(primary_path.glob('*.ico'))
        if ico_files:
            return ico_files[0]
            
    if fallback_path.exists():
        ico_files = list(fallback_path.glob('*.ico'))
        if ico_files:
            return ico_files[0]
    
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
