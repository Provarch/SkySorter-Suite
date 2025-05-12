import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from __ui_definitions import MainWindow
from __ui_widgets import find_app_icon
from pathlib import Path

if __name__ == '__main__':
    # Get the application base directory
    app_dir = Path(__file__).parent

    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Set application-wide attributes
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
