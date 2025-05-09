from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QToolTip, QLineEdit
from PyQt6.QtCore import Qt, QTimer, QPoint
import webbrowser
from pathlib import Path
import platform
import uuid
import hashlib
import subprocess
import sys


class ToolsDropdown(QWidget):
    def __init__(self, parent=None, gfx_dir=None, main_window=None, button_set=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.gfx_dir = gfx_dir
        self.main_window = main_window
        self.button_set = button_set  # Reference to ButtonSet

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Skydrop button
        skydrop_button = QToolButton()
        skydrop_button.setText("DROP")
        skydrop_button.setFixedWidth(90)
        skydrop_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: white; 
                padding: 5px; 
                border-radius: 4px; 
                border: none; 
                text-align: center; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        skydrop_button.setToolTip("<b>Skydrop</b><br>A handy droplet script that mimics smart merge script")
        skydrop_button.clicked.connect(lambda: [self.launch_skydrop(), self.button_set.toggle_dropdown()])
        layout.addWidget(skydrop_button)

        
        # Skynizer button
        skynizer_button = QToolButton()
        skynizer_button.setText("NIZER")
        skynizer_button.setFixedWidth(90)
        skynizer_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: white; 
                padding: 5px; 
                border-radius: 4px; 
                border: none; 
                text-align: center; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        skynizer_button.setToolTip("<b>Skynizer</b><br>Click to launch SkyNizer")
        skynizer_button.clicked.connect(lambda: [self.launch_skynizer(), self.button_set.toggle_dropdown()])
        layout.addWidget(skynizer_button)



        # Skylister button
        skylister_button = QToolButton()
        skylister_button.setText("LISTER")
        skylister_button.setFixedWidth(90)
        skylister_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: white; 
                padding: 5px; 
                border-radius: 4px; 
                border: none; 
                text-align: center; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        skylister_button.setToolTip("<b>Skylister</b><br>Generate a report of 3dsky models")
        skylister_button.clicked.connect(lambda: [self.main_window.run_skylister(), self.button_set.toggle_dropdown()])
        layout.addWidget(skylister_button)

        # Updates button
        updates_button = QToolButton()
        updates_button.setText("UPDATE")
        updates_button.setFixedWidth(90)
        updates_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: white; 
                padding: 5px; 
                border-radius: 4px; 
                border: none; 
                text-align: center; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        updates_button.setToolTip("<b>Updates</b><br>Check for skySorter updates")
        updates_button.clicked.connect(lambda: [self.launch_checker(updates_button), self.button_set.toggle_dropdown()])
        layout.addWidget(updates_button)

    def launch_skynizer(self):
        skynizer_script = self.gfx_dir.parent / "__skyNizer.pyw"
        if not skynizer_script.exists():
            print(f"SkyNizer script not found at {skynizer_script}", flush=True)
            if self.main_window and hasattr(self.main_window, 'console_output'):
                self.main_window.console_output.append(f"Error: SkyNizer script not found at {skynizer_script}")
            return
        try:
            # Get the raw folder path from process_input
            raw_folder = self.main_window.process_input.text() if self.main_window else ""
            args = [sys.executable, str(skynizer_script)]
            # Add raw folder as sys arg if it exists and is a valid directory
            if raw_folder and Path(raw_folder).is_dir():
                args.append(raw_folder)
            subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            error_msg = f"Error launching SkyNizer: {str(e)}"
            print(error_msg, flush=True)
            if self.main_window and hasattr(self.main_window, 'console_output'):
                self.main_window.console_output.append(error_msg)

    def launch_skydrop(self):
        skydrop_script = self.gfx_dir.parent / "__SkyDrop.pyw"
        if not skydrop_script.exists():
            print(f"SkyDrop script not found at {skydrop_script}", flush=True)
            return
        try:
            subprocess.Popen([sys.executable, str(skydrop_script)], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error launching SkyDrop: {str(e)}", flush=True)
            
    def launch_checker(self, button):
        checker_script = self.gfx_dir.parent / "__chcker.py"
        if not checker_script.exists():
            print(f"Checker script not found at {checker_script}", flush=True)
            if self.main_window and hasattr(self.main_window, 'console_output'):
                self.main_window.console_output.append(f"Error: Checker script not found at {checker_script}")
            return
        try:
            button_pos = button.mapToGlobal(QPoint(0, 0))
            dialog_x = button_pos.x()
            dialog_y = button_pos.y() + button.height()
            subprocess.Popen([sys.executable, str(checker_script), str(dialog_x), str(dialog_y)], 
                            creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            error_msg = f"Error launching Checker: {str(e)}"
            print(error_msg, flush=True)
            if self.main_window and hasattr(self.main_window, 'console_output'):
                self.main_window.console_output.append(error_msg)
                
    def show_at_position(self, position):
        self.move(position)
        self.show()

    def hide_dropdown(self):
        self.hide()

class ButtonSet(QWidget):
    def __init__(self, parent=None, user_uid=None, gfx_dir=None, main_window=None):
        super().__init__(parent)
        self.user_uid = user_uid  # Can be None initially
        self.gfx_dir = gfx_dir
        self.main_window = main_window
        self.uid_button = None
        self.tools_dropdown = None
        self.tools_button = None
        self.alias_input = None
        self.dropdown_visible = False
        self.dropdown_timer = QTimer()  # Timer for auto-closing the dropdown
        self.dropdown_timer.setSingleShot(True)  # Timer fires only once
        self.dropdown_timer.timeout.connect(self.hide_dropdown_timeout)  # Connect to a method to hide the dropdown
        self.setup_ui()
        self.initialize_position()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)

        # Alias input field
        self.alias_input = QLineEdit()
        self.alias_input.setFixedWidth(125)
        self.alias_input.setText("Your alias...")
        self.alias_input.setStyleSheet("""
            QLineEdit { 
                background-color: rgba(61, 61, 61, 200); 
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 3px; 
            }
            QLineEdit:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        self.alias_input.setToolTip("<b>Alias</b><br>Enter your Patreon username if you have joined a subscription")
        self.alias_input.enterEvent = self.clear_on_hover
        self.alias_input.leaveEvent = self.restore_on_hover_off
        self.alias_input.textChanged.connect(self.main_window.save_config)
        button_layout.addWidget(self.alias_input)

        # UID button with masked display
        self.uid_button = QToolButton()
        # Mask UID, showing only first 6 characters
        displayed_uid = f"{self.user_uid[:6]}******" if self.user_uid and len(self.user_uid) > 6 else (self.user_uid if self.user_uid else "Waiting for UID...")
        self.uid_button.setText(f"UID:{displayed_uid}")
        self.uid_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: #00ff00; 
                padding: 5px; 
                border-radius: 4px; 
                font-family: Consolas; 
                font-size: 12px; 
                border: none; 
                text-align: right; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        self.uid_button.setToolTip("Click to copy the User ID to clipboard")
        self.uid_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uid_button.clicked.connect(self.copy_uid_to_clipboard)
        button_layout.addWidget(self.uid_button)

        # Tools button
        self.tools_button = QToolButton()
        self.tools_button.setText("SKY...")
        self.tools_button.setFixedWidth(80)
        self.tools_button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(30, 30, 30, 200); 
                color: white; 
                padding: 5px; 
                border-radius: 4px; 
                border: none; 
                text-align: center; 
            }
            QToolButton:hover { 
                background-color: rgba(77, 77, 77, 200); 
            }
        """)
        self.tools_button.setToolTip("<b>Tools</b><br>Click to show available tools")
        self.tools_button.clicked.connect(self.toggle_dropdown)
        button_layout.addWidget(self.tools_button)

        # Create the dropdown widget
        self.tools_dropdown = ToolsDropdown(None, self.gfx_dir, self.main_window, button_set=self)
        self.tools_dropdown.setWindowFlags(self.tools_dropdown.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        main_layout.addStretch(1)
        main_layout.addWidget(button_container)

    def update_uid(self, new_uid):
        """Update the UID and refresh the UID button text."""
        self.user_uid = new_uid
        # Update with masked display
        displayed_uid = f"{self.user_uid[:6]}******" if self.user_uid and len(self.user_uid) > 6 else (self.user_uid if self.user_uid else "Waiting for UID...")
        self.uid_button.setText(f"UID:{displayed_uid}")

    def initialize_position(self):
        QTimer.singleShot(100, self.update_dropdown_position)

    def toggle_dropdown(self):
        if not self.dropdown_visible:
            self.update_dropdown_position()
            self.tools_dropdown.show()
            self.dropdown_visible = True
            self.dropdown_timer.start(6000)  # Start the timer for 6 seconds (6000 milliseconds)
        else:
            self.tools_dropdown.hide_dropdown()
            self.dropdown_visible = False
            self.dropdown_timer.stop()  # Stop the timer if manually closed

    def update_dropdown_position(self):
        if self.tools_button:
            button_pos = self.tools_button.mapToGlobal(QPoint(0, 0))
            dropdown_pos = QPoint(button_pos.x(), button_pos.y() + self.tools_button.height())
            self.tools_dropdown.move(dropdown_pos)
            if self.dropdown_visible:
                self.tools_dropdown.show()

    def copy_uid_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.user_uid if self.user_uid else "")
        button_pos = self.uid_button.mapToGlobal(QPoint(0, 0))
        tooltip_pos = QPoint(button_pos.x(), button_pos.y() + self.uid_button.height())
        QToolTip.showText(tooltip_pos, "User ID copied to clipboard", self.uid_button)
        QTimer.singleShot(2000, lambda: QToolTip.hideText())

    def clear_on_hover(self, event):
        if self.alias_input.text() == "Your alias...":
            self.alias_input.clear()

    def restore_on_hover_off(self, event):
        if not self.alias_input.text().strip():
            self.alias_input.setText("Your alias...")

    def get_alias(self):
        return self.alias_input.text() if self.alias_input else ""

    def set_alias(self, alias):
        if self.alias_input:
            self.alias_input.setText(alias if alias else "Your alias...")

    def hide_dropdown_timeout(self):
        """Hide the dropdown when the timer expires."""
        if self.dropdown_visible:
            self.tools_dropdown.hide_dropdown()
            self.dropdown_visible = False
