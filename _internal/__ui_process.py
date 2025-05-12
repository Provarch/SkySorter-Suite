import re
import time
import socket
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QFileDialog, QTextEdit
from pathlib import Path
import sys
import os
import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger(__name__)

def run_sky_sorter(main_window):
    unprocessed_path = main_window.process_input.text()
    sky_bank_path = main_window.folder_input1.text()
    alias = main_window.button_set.get_alias()
    
    if not unprocessed_path:
        main_window.console_output.append("Error: Please select an unprocessed folder path first")
        return
    
    try:
        if not main_window.sky_sorter_script.exists():
            main_window.console_output.append(f"Error: skySorter.py not found at {main_window.sky_sorter_script}")
            return
            
        main_window.console_output.clear()
        
        main_window.console_output.append(f"Launching: Python with {main_window.sky_sorter_script} {unprocessed_path}")
        if sky_bank_path:
            main_window.console_output.append(f"Sky bank path provided: {sky_bank_path}")
        if alias and alias.strip() != "patreon alias...":
            main_window.console_output.append(f"Alias provided: {alias}")
        
        main_window.process.setWorkingDirectory(str(main_window.app_dir))
        
        program = str(sys.executable)
        arguments = [str(main_window.sky_sorter_script), unprocessed_path]
        
        if sky_bank_path:
            arguments.append(sky_bank_path)
        
        if alias and alias.strip() != "patreon alias...":
            arguments.append(alias)
        
        main_window.process.start(program, arguments)
        
    except Exception as e:
        main_window.console_output.append(f"Error running SkySorter: {str(e)}")

def run_skylister(main_window):
    sky_bank_path = main_window.folder_input1.text()
    
    if not sky_bank_path:
        main_window.console_output.append("Error: Please select a Sky Bank folder path first")
        return
    
    try:
        if not main_window.skylister_script.exists():
            main_window.console_output.append(f"Error: Skylister script not found at {main_window.skylister_script}")
            return
            
        main_window.console_output.clear()
        
        main_window.console_output.append(f"Launching: Python with {main_window.skylister_script} {sky_bank_path}")
        
        main_window.process.setWorkingDirectory(str(main_window.app_dir))
        
        program = str(sys.executable)
        arguments = [str(main_window.skylister_script), sky_bank_path]
        
        main_window.process.start(program, arguments)
        
    except Exception as e:
        main_window.console_output.append(f"Error running Skylister: {str(e)}")

def process_finished(main_window, exit_code, exit_status):
    if exit_code == 0:
        main_window.console_output.append("\nProcess completed successfully.")
    else:
        main_window.console_output.append(f"\nProcess finished with exit code: {exit_code}")

def kill_process(main_window):
    if main_window.process and main_window.process.state() == QProcess.ProcessState.Running:
        main_window.process.terminate()
        main_window.console_output.append("Attempting to terminate SkySorter client process...")
        
        QTimer.singleShot(2000, lambda: check_and_kill_bridge(main_window))
    else:
        main_window.console_output.append("No running client process to kill.")
        check_and_kill_bridge(main_window)

def check_and_kill_bridge(main_window):
    if main_window.process and main_window.process.state() == QProcess.ProcessState.Running:
        main_window.process.kill()
        main_window.console_output.append("Client process forcibly killed.")

    bridge_port = 8888
    shutdown_acknowledged = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", bridge_port))
            s.send("bridge_shutdown".encode())
            response = s.recv(1024).decode()
            if response == "bridge_closing":
                main_window.console_output.append("✅ Bridge shutdown command acknowledged.")
                shutdown_acknowledged = True
            else:
                main_window.console_output.append(f"⚠️ Unexpected bridge response: {response}")
    except ConnectionRefusedError:
        main_window.console_output.append("ℹ️ No bridge detected on port 8888, assuming already terminated.")
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
                    main_window.console_output.append(f"⚠️ Bridge still running after shutdown command (attempt {attempt + 1}/{retries}).")
                    if attempt == retries - 1:
                        main_window.console_output.append("❌ Bridge failed to shut down gracefully.")
                        force_kill_bridge(main_window)
                    time.sleep(1)
            except ConnectionRefusedError:
                main_window.console_output.append("✅ Bridge successfully shut down.")
                return
            except Exception:
                pass

def force_kill_bridge(main_window):
    # Placeholder for force killing bridge process if needed
    pass

def check_process(main_window):
    if main_window.process and main_window.process.state() == QProcess.ProcessState.Running:
        main_window.process.kill()
        main_window.console_output.append("Process forcibly killed.")
    else:
        main_window.console_output.append("Process has been terminated.")

def open_explorer(main_window, path):
    if not path:
        main_window.console_output.append("Error: No path specified")
        return
    try:
        path_obj = Path(path)
        if path_obj.exists():
            os.startfile(str(path_obj))
            time.sleep(0.1)
            if path == main_window.process_input.text():
                resize_and_position_explorer_window(600, 900, "left")
            else:
                resize_and_position_explorer_window(600, 900, "right")
        else:
            main_window.console_output.append(f"Error: Path does not exist: {path}")
    except Exception as e:
        main_window.console_output.append(f"Error opening explorer: {str(e)}")

def resize_and_position_explorer_window(width, height, position="right"):
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

def handle_console_input(main_window, event, console):
    if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
        cursor = console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
        current_line = cursor.selectedText()
        
        if "Enter your choice (c/i/r):" in current_line:
            current_input = current_line.split(":")[-1].strip()
        else:
            current_input = current_line.strip()
        
        if main_window.process and main_window.process.state() == QProcess.ProcessState.Running:
            main_window.process.write(f"{current_input}\n".encode())
            main_window.process.waitForBytesWritten()
            
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText("\n")
    else:
        QTextEdit.keyPressEvent(console, event)

def handle_stdout(main_window):
    data = main_window.process.readAllStandardOutput()
    stdout = bytes(data).decode('utf-8', errors='replace')
    cursor = main_window.console_output.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    main_window.console_output.setTextCursor(cursor)
    main_window.console_output.insertPlainText(stdout)
    
    uid_pattern = r"Usage limit: uid:([0-9a-f]{16}):"
    usage_pattern = r"All-time usage: (\d+)/(\d+) requests"
    monthly_usage_pattern = r"Monthly usage: (\d+)/(\d+) requests"
    success_pattern = r"✅ Processed [^\s]+ successfully\."
    for line in stdout.splitlines():
        uid_match = re.search(uid_pattern, line)
        if uid_match:
            new_uid = uid_match.group(1)
            if new_uid != main_window.user_uid:
                main_window.user_uid = new_uid
                main_window.button_set.update_uid(main_window.user_uid)
                main_window.console_output.append(f"Extracted UID: {main_window.user_uid}")
                main_window.save_config()
        
        usage_match = re.search(usage_pattern, line)
        if usage_match:
            current, total = map(int, usage_match.groups())
            main_window.current_usage = max(main_window.current_usage, current)
            main_window.total_usage = total
            main_window.usage_button.update_usage(line)
            main_window.save_config()
        
        monthly_match = re.search(monthly_usage_pattern, line)
        if monthly_match:
            current, total = map(int, monthly_match.groups())
            main_window.current_usage = max(main_window.current_usage, current)
            main_window.total_usage = total
            main_window.usage_button.update_usage(line)
            main_window.save_config()
        
        success_match = re.search(success_pattern, line)
        if success_match:
            main_window.current_usage += 1
            main_window.usage_button.update_usage(f"Monthly usage: {main_window.current_usage}/{main_window.total_usage} requests")
            main_window.save_config()
    
    cursor.movePosition(cursor.MoveOperation.End)
    main_window.console_output.setTextCursor(cursor)
    main_window.console_output.verticalScrollBar().setValue(
        main_window.console_output.verticalScrollBar().maximum()
    )
    QApplication.processEvents()

def handle_stderr(main_window):
    data = main_window.process.readAllStandardError()
    stderr = bytes(data).decode('utf-8', errors='replace')
    cursor = main_window.console_output.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    main_window.console_output.setTextCursor(cursor)
    main_window.console_output.insertHtml(f'<span style="color: red;">{stderr}</span>')
    main_window.console_output.verticalScrollBar().setValue(
        main_window.console_output.verticalScrollBar().maximum()
    )

def validate_and_run_sky_sorter(main_window):
    if not main_window.process_input.text():
        main_window.console_output.append("Error: Please select an unprocessed folder path first")
        return
    run_sky_sorter(main_window)

def copy_uid_to_clipboard(main_window, uid):
    QApplication.clipboard().setText(uid)
    main_window.console_output.append(f"UID '{uid}' copied to clipboard.")

def mousePressEvent(main_window, event):
    if event.button() == Qt.MouseButton.LeftButton:
        widget = main_window.childAt(event.position().toPoint())
        if not widget or not any(isinstance(widget, t) for t in (QPushButton, QToolButton, QLineEdit, QTextEdit)):
            main_window.dragging = True
            main_window.drag_position = event.globalPosition().toPoint() - main_window.frameGeometry().topLeft()
            event.accept()

def mouseReleaseEvent(main_window, event):
    if event.button() == Qt.MouseButton.LeftButton:
        main_window.dragging = False
        event.accept()
    elif event.button() == Qt.MouseButton.RightButton:
        dialog = ConfirmExitDialog(main_window)
        
        window_geometry = main_window.geometry()
        dialog_geometry = dialog.geometry()
        
        center_x = window_geometry.x() + (window_geometry.width() - dialog_geometry.width()) // 2
        center_y = window_geometry.y() + (window_geometry.height() - dialog_geometry.height()) // 2
        
        offset_x = -40
        offset_y = -90
        
        dialog.move(center_x + offset_x, center_y + offset_y)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            main_window.close()
        event.accept()

def mouseMoveEvent(main_window, event):
    if main_window.dragging and event.buttons() & Qt.MouseButton.LeftButton:
        main_window.move(event.globalPosition().toPoint() - main_window.drag_position)
        event.accept()

def closeEvent(main_window, event):
    event.accept()