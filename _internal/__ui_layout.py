from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QLabel, QPushButton, QGraphicsDropShadowEffect, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
import webbrowser
from pathlib import Path
from __ui_widgets import DragDropLineEdit
from __button_set import ButtonSet

def setup_top_section(main_window, script_dir):
    top_section = QWidget()
    top_layout = QHBoxLayout(top_section)
    top_layout.setSpacing(5)
    top_layout.setContentsMargins(0, 0, 0, 0)
    
    logo_container = QWidget()
    logo_container.setFixedWidth(85)
    logo_layout = QHBoxLayout(logo_container)
    logo_layout.setContentsMargins(0, 0, 0, 0)
    logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    provarch_logo = QToolButton()
    provarch_logo.setFixedSize(85, 85)
    logo_path = main_window.gfx_dir / "prov_logo_v3.png"
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
    
    social_container = QWidget()
    social_container.setFixedWidth(40)
    social_layout = QVBoxLayout(social_container)
    social_layout.setContentsMargins(10, 0, 0, 0)
    social_layout.setSpacing(2)
    social_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    
    discord_button = QToolButton()
    discord_button.setFixedWidth(27)
    discord_button.setFixedHeight(27)
    discord_logo_path = main_window.gfx_dir / "dis_logo+.png"
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
    
    youtube_button = QToolButton()
    youtube_button.setFixedWidth(27)
    youtube_button.setFixedHeight(27)
    youtube_logo_path = main_window.gfx_dir / "yt_logo.png"
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
    
    paths_widget = QWidget()
    paths_layout = QVBoxLayout(paths_widget)
    paths_layout.setSpacing(5)
    paths_layout.setContentsMargins(0, 0, 0, 0)
    
    main_window.folder_input1 = DragDropLineEdit()
    main_window.folder_input1.textChanged.connect(lambda text: main_window.folder_input1.setText(main_window.remove_quotes_from_path(text)) if '"' in text else None)
    
    folder_widget1 = QWidget()
    folder_layout1 = QHBoxLayout(folder_widget1)
    folder_layout1.setContentsMargins(0, 0, 0, 0)
    folder_layout1.setSpacing(5)
    folder_layout1.addStretch(1)
    folder_label1 = QToolButton()
    folder_label1.setText("Sky-Bank Folder")
    folder_label1.setFixedWidth(150)
    folder_label1.setCursor(Qt.CursorShape.PointingHandCursor)
    folder_label1.clicked.connect(lambda: main_window.open_explorer(main_window.folder_input1.text()))
    folder_label1.setStyleSheet("""
        QToolButton { background-color: rgba(30, 30, 30, 200); color: white; padding: 5px; border-radius: 4px; border: none; text-align: left; }
        QToolButton:hover { background-color: rgba(77, 77, 77, 200); }
    """)
    folder_label1.setToolTip("<b>3dsky Bank Folder</b><br>This is the location where your processed models be stored in. Leaving this folder path empty will stop detecting dublicate models")
    
    main_window.folder_input1.setFixedWidth(320)
    folder_button1 = QPushButton("...")
    folder_button1.setFixedWidth(30)
    folder_button1.clicked.connect(main_window.select_3dsky_folder)
    folder_layout1.addWidget(folder_label1)
    folder_layout1.addWidget(main_window.folder_input1)
    folder_layout1.addWidget(folder_button1)
    
    paths_layout.addWidget(folder_widget1)
    
    main_window.button_set = ButtonSet(main_window, main_window.user_uid, main_window.gfx_dir, main_window)
    paths_layout.addWidget(main_window.button_set)
    
    top_layout.addWidget(logo_container, 0)
    top_layout.addWidget(social_container, 0)
    top_layout.addWidget(paths_widget, 1)
    
    return top_section

def setup_process_button(main_window):
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
    
    process_button.clicked.connect(main_window.validate_and_run_sky_sorter)
    
    return process_button

def setup_middle_section(main_window, script_dir):
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

    process_button = setup_process_button(main_window)

    middle_container = QVBoxLayout()
    middle_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
    middle_container.setContentsMargins(105, 20, 0, 0)
    middle_container.addWidget(process_button)

    middle_container.addSpacing(30)

    usage_button_container = QHBoxLayout()
    usage_button_container.addSpacing(350)
    usage_button_container.addWidget(main_window.usage_button)
    usage_button_container.addStretch()

    middle_container.addLayout(usage_button_container)

    buttons_layout.addLayout(middle_container)

    central_layout.addWidget(buttons_widget, 1)
    middle_layout.addStretch(1)
    middle_layout.addWidget(central_widget)
    middle_layout.addStretch(1)
    return middle_section

def setup_process_widget(main_window):
    process_widget = QWidget()
    process_layout = QHBoxLayout(process_widget)
    process_layout.setContentsMargins(10, 5, 10, 5)
    
    process_button_tags = QToolButton()
    process_button_tags.setText("Unprocessed(Raw) folder")
    process_button_tags.clicked.connect(lambda: main_window.open_explorer(main_window.process_input.text()))
    process_button_tags.setStyleSheet("""
        QToolButton { background-color: rgba(30, 30, 30, 200); color: white; padding: 5px; border-radius: 4px; border: none; }
        QToolButton:hover { background-color: rgba(77, 77, 77, 200); }
    """)
    main_window.process_input = DragDropLineEdit()
    main_window.process_input.setFixedWidth(360)
    main_window.process_input.textChanged.connect(lambda text: main_window.process_input.setText(main_window.remove_quotes_from_path(text)) if '"' in text else None)
    
    # Add sorting type toggle button
    sorting_toggle_button = QToolButton()
    # Load the current sorting type from config
    current_sorting_type = main_window.config.get('sorting_type', 'CAT')
    sorting_toggle_button.setText(current_sorting_type)
    sorting_toggle_button.setFixedSize(30, 30)  # Match folder picker's dimensions
    sorting_toggle_button.setStyleSheet("""
        QToolButton { 
            background-color: rgba(30, 30, 100, 200); /* Base blue color */
            color: white; 
            padding: 2px; 
            border-radius: 4px; 
            border: none; 
            font-size: 10px;  /* Smaller text to fit CAT */
            text-align: center; 
        }
        QToolButton:hover { background-color: rgba(50, 50, 255, 200); /* Brighter blue on hover */ }
    """)
    sorting_toggle_button.setToolTip("Placeholder tooltip")  # Placeholder tooltip
    # Connect the button to toggle logic
    sorting_toggle_button.clicked.connect(lambda: toggle_sorting_type(main_window, sorting_toggle_button))
    
    kill_process_button = QPushButton("Kill Process")
    kill_process_button.setFixedSize(80, 30)
    kill_process_button.setStyleSheet("""
        QPushButton { background-color: rgba(100, 30, 30, 100); color: white; border: 1px solid #555555; border-radius: 4px; padding: 5px; }
        QPushButton:hover { background-color: rgba(255, 50, 50, 200); }
    """)
    kill_process_button.clicked.connect(main_window.kill_process)
    
    process_button = QPushButton("...")
    process_button.setFixedWidth(30)
    process_button.clicked.connect(main_window.select_process_path)
    
    process_layout.addStretch(1)
    process_layout.addWidget(process_button_tags)
    process_layout.addWidget(sorting_toggle_button)  # Add the toggle button before Kill Process
    process_layout.addWidget(kill_process_button)
    process_layout.addWidget(main_window.process_input)
    process_layout.addWidget(process_button)
    return process_widget

def toggle_sorting_type(main_window, button):
    # Get the current sorting type from config
    current_sorting_type = main_window.config.get('sorting_type', 'CAT')
    # Toggle between CAT and ID
    new_sorting_type = 'ID' if current_sorting_type == 'CAT' else 'CAT'
    # Update the config
    main_window.config['sorting_type'] = new_sorting_type
    # Save the updated config to sssuite.cfg
    main_window.save_config()
    # Update the button text and reapply style
    button.setText(new_sorting_type)
    if new_sorting_type == 'ID':
        button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(0, 128, 128, 100); /* Turquoise */
                color: white; 
                padding: 2px; 
                border-radius: 4px; 
                border: none; 
                font-size: 10px;  /* Smaller text to fit CAT */
                text-align: center; 
            }
            QToolButton:hover { background-color: rgba(0, 255, 255, 200); /* Brighter turquoise on hover */ }
        """)
    else:  # CAT
        button.setStyleSheet("""
            QToolButton { 
                background-color: rgba(255, 165, 0, 200); /* Orange */
                color: white; 
                padding: 2px; 
                border-radius: 4px; 
                border: none; 
                font-size: 10px;  /* Smaller text to fit CAT */
                text-align: center; 
            }
            QToolButton:hover { background-color: rgba(255, 200, 0, 200); /* Brighter orange on hover */ }
        """)

def setup_console(main_window):
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
            width: 12px; 
            border-radius: 6px; 
            margin: 0px; 
        }
        QScrollBar::handle:vertical { 
            background-color: rgba(60, 60, 60, 0.8); 
            border-radius: 6px; 
            min-height: 20px; 
        }
        QScrollBar::handle:vertical:hover { 
            background-color: rgba(80, 80, 80, 0.9); 
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
    
    console_output.keyPressEvent = lambda event: main_window.handle_console_input(event, console_output)
    
    console_container = QHBoxLayout()
    console_container.setContentsMargins(0, 0, 0, 5)
    console_container.addWidget(console_output)
    main_window.console_output = console_output
    return console_container
