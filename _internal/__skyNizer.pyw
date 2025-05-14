from PyQt6.QtWidgets import QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit, QApplication, QToolButton, QLineEdit
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer
from pathlib import Path
import os
import json
import logging
import re
import time
import socket
import sys
import ctypes
from ctypes import wintypes
from __ui_widgets import DragDropLineEdit, find_app_icon, get_main_stylesheet
from __button_set import ButtonSet
from __usage_button import UsageButton
from __ui_layout import setup_top_section, setup_middle_section, setup_process_widget, setup_console
import threading

import sys
import threading
import queue
from filelock import FileLock, Timeout
import time

logger = logging.getLogger(__name__)
def exception_hook(exctype, value, traceback):
    logger.error('Unhandled exception', exc_info=(exctype, value, traceback))
    with open('skysorter_crash.log', 'a', encoding='utf-8') as f:
        import traceback as tb
        f.write(f"[{time.ctime()}] Unhandled {exctype.__name__}: {value}\n")
        tb.print_tb(traceback, file=f)
    sys.__excepthook__(exctype, value, traceback)

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

class MainWindow(QMainWindow):
    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'button_set'):
            self.button_set.update_dropdown_position()

    def __init__(self):
        super().__init__()
        self.PADDING_OUTER = 5
        self.PADDING_INNER = 5
        
        self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        print(f"Running as script from {self.app_dir}")
        self.user_uid = None
        self.current_usage = 0
        self.total_usage = 0
        
        icon_path = find_app_icon(self.app_dir)
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
            print(f"Set window icon to: {icon_path}")
        
        self.internal_dir = self.app_dir
        self.config_file = self.internal_dir / 'sssuite.cfg'
        self.default_config_file = self.app_dir / 'default_config.json'
        self.report_filter_file = self.app_dir / 'report_filter.json'
        
        self.load_config()
        self.load_report_filters()
        
        self.gfx_dir = None
        possible_gfx_paths = [
            self.app_dir / '_gfx',
            self.internal_dir / '_gfx',
            self.internal_dir / '_internal' / '_gfx',
        ]
        for path in possible_gfx_paths:
            if path.exists():
                self.gfx_dir = path
                print(f"Found graphics directory at: {self.gfx_dir}")
                break
        if self.gfx_dir is None:
            print("WARNING: Could not find graphics directory!")
            self.gfx_dir = self.app_dir / '_gfx'
        
        print(f"Internal directory: {self.internal_dir}")
        print(f"Config file path: {self.config_file}")
        print(f"Graphics directory: {self.gfx_dir}")
        
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
        
        background_label = QLabel(content_widget)
        bg_path = self.gfx_dir / "bg_toolkit.png"
        pixmap = QPixmap(str(bg_path))
        scaled_pixmap = pixmap.scaled(700, 700, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x = (690 - scaled_pixmap.width()) // 2
        y = (583 - scaled_pixmap.height()) // 2
        background_label.setGeometry(x, y, scaled_pixmap.width(), scaled_pixmap.height())
        background_label.setPixmap(scaled_pixmap)
        background_label.lower()
        
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
        
        top_section = setup_top_section(self, self.app_dir)
        middle_section = setup_middle_section(self, self.app_dir)
        process_widget = setup_process_widget(self)
        console_container = setup_console(self)
        
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
        
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        bottom_layout.addWidget(process_widget)
        bottom_layout.addLayout(console_container)
        
        content_layout.addWidget(top_section, 0)
        content_layout.addWidget(middle_section, 0)
        content_layout.addWidget(hero_container, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addStretch(1)
        content_layout.addWidget(bottom_container, 0)
        
        top_section.raise_()
        content_widget.raise_()
        
        main_layout.addWidget(content_widget, 1)
        
        self.setStyleSheet(get_main_stylesheet())
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process_env = QProcessEnvironment.systemEnvironment()
        process_env.insert("PYTHONUNBUFFERED", "1")
        process_env.insert("PYTHONIOENCODINGHITHOUT", "utf-8")
        process_env.insert("PYTHONUTF8", "1")
        self.process.setProcessEnvironment(process_env)
        
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
        self.apply_saved_config()
        
        self.folder_input1.textChanged.connect(self.save_config)
        self.process_input.textChanged.connect(self.save_config)
        
        self.dragging = False
        self.drag_position = None

    def load_report_filters(self):
        """Load report filter patterns from report_filter.json and compile them as regex."""
        self.suppressed_patterns = []
        try:
            if self.report_filter_file.exists():
                with open(self.report_filter_file, 'r', encoding='utf-8') as f:
                    filter_data = json.load(f)
                    patterns = filter_data.get('suppressed_patterns', [])
                    # Compile patterns as regex for efficient matching
                    self.suppressed_patterns = [re.compile(pattern) for pattern in patterns]
                    logger.debug(f"Loaded and compiled report filters from {self.report_filter_file}: {patterns}")
            else:
                logger.warning(f"Report filter file not found at {self.report_filter_file}")
                print(f"Warning: Report filter file not found at {self.report_filter_file}")
        except Exception as e:
            logger.error(f"Error loading report filters: {str(e)}")
            print(f"Error loading report filters: {str(e)}")
            self.console_output.append(f"Error loading report filters: {str(e)}")


    def load_config(self):
        """Load configuration from sssuite.cfg, using default_config.json as the baseline."""
        default_config = {}
        try:
            if self.default_config_file.exists():
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
                    logger.debug(f"Loaded default_config from {self.default_config_file}: {default_config}")
            else:
                print(f"Warning: default_config.json not found at {self.default_config_file}")
                logger.warning(f"Warning: default_config.json not found at {self.default_config_file}")
        except Exception as e:
            print(f"Error loading default_config.json: {e}")
            logger.error(f"Error loading default_config.json: {e}")

        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config = {**default_config, **loaded_config}
                    logger.debug(f"Loaded and merged config from {self.config_file}: {self.config}")
            else:
                print(f"Warning: Config file not found at {self.config_file}")
                logger.warning(f"Warning: Config file not found at {self.config_file}")
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            logger.error(f"Error loading config: {e}")
            self.config = default_config
            self.save_config()

    def save_config(self):
        """Save configuration to sssuite.cfg with debouncing and file locking."""
        logger.debug("Requesting save_config")
        try:
            if not hasattr(self, '_save_config_timer'):
                self._save_config_timer = QTimer(self)
                self._save_config_timer.setSingleShot(True)
                self._save_config_timer.timeout.connect(self._execute_save_config)
            
            # Debounce: Delay save_config by 500ms
            if not self._save_config_timer.isActive():
                self._save_config_timer.start(500)
            else:
                logger.debug("save_config debounced, waiting for timer")
        except Exception as e:
            logger.error(f"Error initiating save_config: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error initiating config save: {str(e)}")

    def _execute_save_config(self):
        """Execute config save with file locking."""
        logger.debug("Executing save_config")
        try:
            config_data = {
                '3dsky_folder': self.config.get('3dsky_folder', '') if not hasattr(self, 'folder_input1') else self.folder_input1.text(),
                'process_models_path': self.config.get('process_models_path', '') if not hasattr(self, 'process_input') else self.process_input.text(),
                'alias': self.config.get('alias', '') if not hasattr(self, 'button_set') else self.button_set.get_alias(),
                'user_uid': self.user_uid if self.user_uid else '',
                'current': self.config.get('current', 0) if not hasattr(self, 'usage_button') else getattr(self.usage_button, 'current', 0),
                'total': self.config.get('total', 0) if not hasattr(self, 'usage_button') else getattr(self.usage_button, 'total', 0),
                'renewal_date': self.config.get('renewal_date', '') if not hasattr(self, 'usage_button') else (getattr(self.usage_button, 'renewal_date', '') or '')
            }
            
            full_config = self.config.copy()
            full_config.update(config_data)
            
            self.internal_dir.mkdir(parents=True, exist_ok=True)
            lock_file = self.config_file.with_suffix('.cfg.lock')
            
            with FileLock(lock_file, timeout=5):
                temp_file = self.config_file.with_suffix('.cfg.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(full_config, f, indent=4)
                if self.config_file.exists():
                    self.config_file.unlink()
                temp_file.rename(self.config_file)
            
            logger.debug(f"Saved config to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error saving config: {str(e)}")

    def apply_saved_config(self):
        """Apply saved configuration to UI elements."""
        logger.debug("Applying saved configuration")
        try:
            if hasattr(self, 'config'):
                if hasattr(self, 'folder_input1'):
                    self.folder_input1.setText(self.config.get('3dsky_folder', ''))
                if hasattr(self, 'process_input'):
                    self.process_input.setText(self.config.get('process_models_path', ''))
                if hasattr(self, 'button_set'):
                    self.button_set.set_alias(self.config.get('alias', ''))
                if self.config.get('user_uid', ''):
                    self.user_uid = self.config['user_uid']
                    if hasattr(self, 'button_set'):
                        self.button_set.update_uid(self.user_uid)
                if hasattr(self, 'usage_button') and 'current' in self.config and 'total' in self.config:
                    self.current_usage = self.config.get('current', 0)
                    self.total_usage = self.config.get('total', 0)
                    self.usage_button.current = self.current_usage
                    self.usage_button.total = self.total_usage
                    renewal_date = self.config.get('renewal_date', '')
                    self.usage_button.renewal_date = renewal_date if renewal_date else None
                    total_str = f"{self.total_usage // 1000}K" if self.total_usage >= 1000 else str(self.total_usage)
                    self.usage_button.setText(
                        f"{self.current_usage}/{total_str}\n{renewal_date}".strip()
                    )
                    self.usage_button.update_glow_based_on_usage()
        except Exception as e:
            logger.error(f"Error applying config: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error applying config: {str(e)}")

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
        """Run the SkySorter process."""
        logger.debug("Running sky sorter")
        try:
            unprocessed_path = self.process_input.text()
            sky_bank_path = self.folder_input1.text()
            alias = ''
            if hasattr(self, 'button_set'):
                try:
                    alias = self.button_set.get_alias()
                except Exception as e:
                    logger.error(f"Error getting alias: {str(e)}\n{traceback.format_exc()}")
            
            if not unprocessed_path:
                self.console_output.append("Error: Please select an unprocessed folder path first")
                return
            
            if not self.sky_sorter_script.exists():
                self.console_output.append(f"Error: skySorter.py not found at {self.sky_sorter_script}")
                return
                
            self.console_output.clear()
            
            self.console_output.append(f"Launching: Python with {self.sky_sorter_script} {unprocessed_path}")
            if sky_bank_path:
                self.console_output.append(f"Sky bank path provided: {sky_bank_path}")
            if alias and alias.strip() != "patreon alias...":
                self.console_output.append(f"Alias provided: {alias}")
            
            self.process.setWorkingDirectory(str(self.app_dir))
            
            program = str(sys.executable)
            arguments = [str(self.sky_sorter_script), unprocessed_path]
            
            if sky_bank_path:
                arguments.append(sky_bank_path)
            
            if alias and alias.strip() != "patreon alias...":
                arguments.append(alias)
            
            self.process.start(program, arguments)
            
        except Exception as e:
            logger.error(f"Error running SkySorter: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error running SkySorter: {str(e)}")

    def run_skylister(self):
        sky_bank_path = self.folder_input1.text()
        
        if not sky_bank_path:
            self.console_output.append("Error: Please select a Sky Bank folder path first")
            return
        
        try:
            if not self.skylister_script.exists():
                self.console_output.append(f"Error: Skylister script not found at {self.skylister_script}")
                return
                
            self.console_output.clear()
            
            self.console_output.append(f"Launching: Python with {self.skylister_script} {sky_bank_path}")
            
            self.process.setWorkingDirectory(str(self.app_dir))
            
            program = str(sys.executable)
            arguments = [str(self.skylister_script), sky_bank_path]
            
            self.process.start(program, arguments)
            
        except Exception as e:
            self.console_output.append(f"Error running Skylister: {str(e)}")

    def process_finished(self, exit_code, exit_status):
        if exit_code == 0:
            self.console_output.append("\nProcess completed successfully.")
        else:
            self.console_output.append(f"\nProcess finished with exit_code: {exit_code}")

    def kill_process(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            self.console_output.append("Attempting to terminate SkySorter client process...")
            
            QTimer.singleShot(2000, lambda: self.check_and_kill_bridge())
        else:
            self.console_output.append("No running client process to kill.")
            self.check_and_kill_bridge()

    def check_and_kill_bridge(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.console_output.append("Client process forcibly killed.")

        bridge_port = 8888
        shutdown_acknowledged = False
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
            return
        except Exception:
            pass

        if shutdown_acknowledged:
            time.sleep(4)
            retries = 3
            for attempt in range(retries):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect(("127.0.0.1", bridge_port))
                        s.close()
                        self.console_output.append(f"⚠️ Bridge still running after shutdown command (attempt {attempt + 1}/{retries}).")
                        if attempt == retries - 1:
                            self.console_output.append("❌ Bridge failed to shut down gracefully.")
                            self.force_kill_bridge()
                        time.sleep(1)
                except ConnectionRefusedError:
                    self.console_output.append("✅ Bridge successfully shut down.")
                    return
                except Exception:
                    pass

    def force_kill_bridge(self):
        # Placeholder for force killing bridge process if needed
        pass

    def check_process(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
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
                os.startfile(str(path_obj))
                time.sleep(0.1)
                if path == self.process_input.text():
                    self.resize_and_position_explorer_window(600, 900, "left")
                else:
                    self.resize_and_position_explorer_window(600, 900, "right")
            else:
                self.console_output.append(f"Error: Path does not exist: {path}")
        except Exception as e:
            self.console_output.append(f"Error opening explorer: {str(e)}")

    def resize_and_position_explorer_window(self, width, height, position="right"):
        try:
            SW_RESTORE = 9
            HWND_TOP = 0
            SWP_SHOWWINDOW = 0x0040
            
            GetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
            screen_width = GetSystemMetrics(0)
            screen_height = GetSystemMetrics(1)
            
            if position == "left":
                x = 10
            else:
                x = screen_width - width - 10
                
            y = (screen_height - height) // 2
            
            hwnd = ctypes.windll.user32.FindWindowW("CabinetWClass", None)
            
            if hwnd:
                ShowWindow = ctypes.windll.user32.ShowWindow
                ShowWindow(hwnd, SW_RESTORE)
                
                SetWindowPos = ctypes.windll.user32.SetWindowPos
                SetWindowPos(hwnd, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW)
            else:
                def enum_windows_callback(hwnd, lParam):
                    class_name = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetClassNameW(hwnd, class_name, 256)
                    
                    if class_name.value == "CabinetWClass":
                        if ctypes.windll.user32.IsWindowVisible(hwnd):
                            ShowWindow = ctypes.windll.user32.ShowWindow
                            ShowWindow(hwnd, SW_RESTORE)
                            
                            SetWindowPos = ctypes.windll.user32.SetWindowPos
                            SetWindowPos(hwnd, HWND_TOP, x, y, width, height, SWP_SHOWWINDOW)
                            return False
                    return True
                
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                ctypes.windll.user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        except Exception as e:
            print(f"Error positioning explorer window: {str(e)}")

    def handle_console_input(self, event, console):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            cursor = console.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            
            cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
            current_line = cursor.selectedText()
            
            if "Enter your choice (c/i/r):" in current_line:
                current_input = current_line.split(":")[-1].strip()
            else:
                current_input = current_line.strip()
            
            if self.process and self.process.state() == QProcess.ProcessState.Running:
                self.process.write(f"{current_input}\n".encode())
                self.process.waitForBytesWritten()
                
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertText("\n")
        else:
            QTextEdit.keyPressEvent(console, event)

    def handle_stdout(self):
        """Handle stdout from the process and update usage limits."""
        try:
            data = self.process.readAllStandardOutput()
            stdout = bytes(data).decode('utf-8', errors='replace')
            cursor = self.console_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.console_output.setTextCursor(cursor)
            
            uid_pattern = r"Usage limit: uid:([0-9a-f]{16}):"
            usage_pattern = r"All-time usage: (\d+)/(\d+) requests"
            monthly_usage_pattern = r"Monthly usage: (\d+)/(\d+) requests"
            success_pattern = r"✅ Processed [^\s]+ successfully\."
            
            updated = False
            for line in stdout.splitlines():
                # Check if the line matches any suppressed regex pattern
                is_suppressed = any(pattern.match(line) for pattern in self.suppressed_patterns)
                
                # Log suppressed messages to debug
                if is_suppressed:
                    logger.debug(f"Suppressed message: {line}")
                
                # Process the line for functional updates (UID, usage, etc.) regardless of suppression
                uid_match = re.search(uid_pattern, line)
                if uid_match and hasattr(self, 'button_set'):
                    new_uid = uid_match.group(1)
                    if new_uid != self.user_uid:
                        self.user_uid = new_uid
                        self.button_set.update_uid(self.user_uid)
                        if not is_suppressed:
                            self.console_output.append(f"Extracted UID: {self.user_uid}")
                        updated = True
                
                usage_match = re.search(usage_pattern, line)
                if usage_match and hasattr(self, 'usage_button'):
                    current, total = map(int, usage_match.groups())
                    self.current_usage = max(self.current_usage, current)
                    self.total_usage = total
                    self.usage_button.update_usage(line)
                    updated = True
                
                monthly_match = re.search(monthly_usage_pattern, line)
                if monthly_match and hasattr(self, 'usage_button'):
                    current, total = map(int, monthly_match.groups())
                    self.current_usage = max(self.current_usage, current)
                    self.total_usage = total
                    self.usage_button.update_usage(line)
                    updated = True
                
                success_match = re.search(success_pattern, line)
                if success_match and hasattr(self, 'usage_button'):
                    self.current_usage += 1
                    self.usage_button.update_usage(f"Monthly usage: {self.current_usage}/{self.total_usage} requests")
                    updated = True
                
                # Display the line only if it is not suppressed
                if not is_suppressed:
                    self.console_output.insertPlainText(line + '\n')
            
            if updated:
                self.save_config()
            
            cursor.movePosition(cursor.MoveOperation.End)
            self.console_output.setTextCursor(cursor)
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
        except Exception as e:
            logger.error(f"Error in handle_stdout: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error processing stdout: {str(e)}")

            
            cursor.movePosition(cursor.MoveOperation.End)
            self.console_output.setTextCursor(cursor)
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
        except Exception as e:
            logger.error(f"Error in handle_stdout: {str(e)}\n{traceback.format_exc()}")
            self.console_output.append(f"Error processing stdout: {str(e)}")


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

    def validate_and_run_sky_sorter(self):
        if not self.process_input.text():
            self.console_output.append("Error: Please select an unprocessed folder path first")
            return
        self.run_sky_sorter()

    def copy_uid_to_clipboard(self, uid):
        QApplication.clipboard().setText(uid)
        self.console_output.append(f"UID '{uid}' copied to clipboard.")

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
            
            window_geometry = self.geometry()
            dialog_geometry = dialog.geometry()
            
            center_x = window_geometry.x() + (window_geometry.width() - dialog_geometry.width()) // 2
            center_y = window_geometry.y() + (window_geometry.height() - dialog_geometry.height()) // 2
            
            offset_x = -40
            offset_y = -90
            
            dialog.move(center_x + offset_x, center_y + offset_y)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.close()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def closeEvent(self, event):
        event.accept()
