import webbrowser
import logging
import re
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor

# Set up logging to debug input values
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UsageButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110)
        self.is_hovered = False
        self.current = 0
        self.total = 0
        self.renewal_date = None
        self.main_window = parent
        
        # Load saved usage data
        self.load_usage_data()  # Call the corrected method
        
        # Set initial text based on loaded or default values
        total_str = f"{self.total // 1000}K" if self.total >= 1000 else str(self.total)
        usage_text = f"{self.current}/{total_str}"
        renewal_text = f"{self.renewal_date}" if self.renewal_date else ""
        self.setText(f"{usage_text}\n{renewal_text}".strip())
        
        # Set initial style with white border for 0/0
        border_color = "#FFFFFF" if self.current == 0 and self.total == 0 else f"rgb(255, {int(255 * (1 - (self.current / self.total if self.total > 0 else 1.0)))}, 255)"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: white;
                border: 2px solid {border_color};
                border-radius: 42px;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)
        
        self.setMask(self.roundedRect(self.rect(), 42))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("<b>Usage Limit</b><br>Enjoy your monthly free 400 request limit \n if you are collector \n Click to purchase additional request limits\n Be sure to use them up in 30-days.")
        self.clicked.connect(self.open_url)
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setColor(QColor(255, 255, 255))
        self.glow_effect.setBlurRadius(25)
        self.glow_effect.setOffset(0)
        self.setGraphicsEffect(self.glow_effect)
        self.glow_effect.setEnabled(True)
        self.enterEvent = self.on_enter
        self.leaveEvent = self.on_leave

    def load_usage_data(self):
        """Load usage data from MainWindow's config."""
        try:
            if hasattr(self.main_window, 'config') and self.main_window.config:
                self.current = self.main_window.config.get('current', 0)
                self.total = self.main_window.config.get('total', 0)
                self.renewal_date = self.main_window.config.get('renewal_date', None)
                logger.debug(f"Loaded usage data: current={self.current}, total={self.total}, renewal={self.renewal_date}")
            else:
                logger.debug("No config available in MainWindow, using defaults")
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")

    def load_config(self):
        """Load configuration from sssuite.cfg, using default_config.json as the baseline."""
        default_config = {}
        try:
            if self.default_config_file.exists():
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
                    logger.debug(f"Loaded default_config from {self.default_config_file}: {default_config}")
            else:
                self.console_output.append(f"Warning: default_config.json not found at {self.default_config_file}")
                print(f"Warning: default_config.json not found at {self.default_config_file}")
        except Exception as e:
            self.console_output.append(f"Error loading default_config.json: {e}")
            print(f"Error loading default_config.json: {e}")
            logger.error(f"Error loading default_config.json: {e}")

        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config = {**default_config, **loaded_config}
                    logger.debug(f"Loaded and merged config from {self.config_file}: {self.config}")
            else:
                self.console_output.append(f"Warning: Config file not found at {self.config_file}")
                print(f"Warning: Config file not found at {self.config_file}")
                self.config = default_config
        except Exception as e:
            self.console_output.append(f"Error loading config: {e}")
            print(f"Error loading config: {e}")
            logger.error(f"Error loading config: {e}")
    def save_usage_data(self):
        """Save usage data to MainWindow's config."""
        try:
            if hasattr(self.main_window, 'config'):
                self.main_window.config.update({
                    'current': self.current,
                    'total': self.total,
                    'renewal_date': self.renewal_date
                })
                self.main_window.save_config()
                logger.debug(f"Saved usage data: current={self.current}, total={self.total}, renewal={self.renewal_date}")
        except Exception as e:
            logger.error(f"Error saving usage data: {e}")

    def on_enter(self, event):
        """Handle mouse enter event to show glow and full opacity on hover"""
        self.is_hovered = True
        text = self.text().split('\n')[0]
        if '/' not in text or text == "0/0":
            current, total = 0, 0
        else:
            current_str, total_str = text.split('/')
            current = int(current_str)
            if total_str.endswith('K'):
                total = int(total_str[:-1]) * 1000
            else:
                total = int(total_str)
        
        # Set glow to max strength, color based on usage
        self.glow_effect.setBlurRadius(11)
        if current == 0 and total == 0:
            self.glow_effect.setColor(QColor(255, 255, 255))  # White for 0/0
        else:
            usage_ratio = current / total if total > 0 else 1.0
            green = int(255 * (1 - usage_ratio))
            white = int(255 * usage_ratio)
            self.glow_effect.setColor(QColor(white, green, white))
        self.glow_effect.setEnabled(True)
        self.update()

    def on_leave(self, event):
        """Handle mouse leave event to reduce opacity and update glow"""
        self.is_hovered = False
        self.update_glow_based_on_usage()
        self.update()

    def parse_usage_string(self, response):
        """Parse usage data from response string like 'Monthly usage: 51/3400 requests (1% of limit). Renews on 4th.'"""
        match = re.search(r'(\d+)/(\d+)\s*requests(?:.*?Renews on (\w+))?', response, re.DOTALL)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            renewal = match.group(3) if match.lastindex >= 3 else None  # Renewal date is optional
            logger.debug(f"Parsed usage string: current={current}, total={total}, renewal={renewal}")
            return current, total, renewal
        logger.error(f"Failed to parse usage string: {response}")
        return None, None, None

    def update_usage(self, current, total=None):
        """Update the usage counter and limit, handling string or numeric input"""
        logger.debug(f"update_usage called with current={current}, total={total}")
        
        if isinstance(current, str):
            if 'usage' in current.lower():
                new_current, new_total, renewal = self.parse_usage_string(current)
                # Only update if parsing was successful
                if new_current is not None and new_total is not None:
                    self.current = new_current
                    self.total = new_total
                    self.renewal_date = renewal if renewal else self.renewal_date
                    logger.debug(f"Renewal date parsed: {self.renewal_date}")
                    self.save_usage_data()  # Save to sssuite.cfg
                else:
                    logger.debug("Parsing failed, retaining previous values")
            else:
                try:
                    current_str, total_str = current.split('/')
                    self.current = int(current_str)
                    if total_str.endswith('K'):
                        self.total = int(total_str[:-1]) * 1000
                    else:
                        self.total = int(total_str)
                    self.renewal_date = None  # Reset if no renewal info
                    logger.debug(f"Parsed string input: current={self.current}, total={self.total}")
                except ValueError as e:
                    logger.error(f"Invalid string input: {current}, error: {e}")
                    # Retain previous values
                    logger.debug("Parsing failed, retaining previous values")
        else:
            if not isinstance(current, int) or (total is not None and not isinstance(total, int)):
                logger.error(f"Invalid input types: current={type(current)}, total={type(total)}")
                # Retain previous values
                logger.debug("Parsing failed, retaining previous values")
            else:
                self.current = current
                self.total = total if total is not None else 0
                self.save_usage_data()  # Save to sssuite.cfg
        
        if self.total is None or self.total < 0:
            self.total = 0
        total_str = f"{self.total // 1000}K" if self.total >= 1000 else str(self.total)
        usage_text = f"{self.current}/{total_str}"
        renewal_text = f"{self.renewal_date}" if self.renewal_date else ""
        self.setText(f"{usage_text}\n{renewal_text}".strip())
        logger.debug(f"Set text to: {usage_text}\n{renewal_text}")
        
        # Save the updated values to file
        self.save_usage_data()
        
        usage_ratio = 0.0 if self.current == 0 and self.total == 0 else self.current / self.total if self.total > 0 else 1.0
        green = int(255 * (1 - usage_ratio))
        white = int(255 * usage_ratio)
        border_color = "#FFFFFF" if self.current == 0 and self.total == 0 else f"rgb({white}, {green}, {white})"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: white;
                border: 2px solid {border_color};
                border-radius: 42px;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)

        self.update_glow_based_on_usage()

    def update_glow_based_on_usage(self, current=None, total=None):
        if current is None or total is None:
            current, total = self.current, self.total

        usage_ratio = 0.0 if current == 0 and total == 0 else current / total if total > 0 else 1.0

        if current == 0 and total == 0:
            self.glow_effect.setColor(QColor(255, 255, 255))
            self.glow_effect.setBlurRadius(11)
            self.glow_effect.setEnabled(True)
        elif usage_ratio >= 1.0:
            self.glow_effect.setColor(QColor(255, 255, 255))
            self.glow_effect.setBlurRadius(0)
            self.glow_effect.setEnabled(False)
        else:
            green = int(255 * (1 - usage_ratio))
            white = int(255 * usage_ratio)
            self.glow_effect.setColor(QColor(white, green, white))
            self.glow_effect.setBlurRadius(int(11 * (1 - usage_ratio)))
            self.glow_effect.setEnabled(True)

    def open_url(self):
        webbrowser.open("https://www.patreon.com/Provarch/shop/skysorter-boost-limits-10k-1297547")
    
    def roundedRect(self, rect, radius):
        from PyQt6.QtGui import QRegion
        return QRegion(rect, QRegion.RegionType.Ellipse)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setOpacity(1.0 if self.is_hovered else 0.8)
        
        text = self.text()
        if '/' not in text.split('\n')[0] or text.split('\n')[0] == "0/0":
            pen_color = QColor(255, 255, 255)
        else:
            current_str, total_str = text.split('\n')[0].split('/')
            current = int(current_str)
            total = int(total_str[:-1]) * 1000 if total_str.endswith('K') else int(total_str)
            usage_ratio = current / total if total > 0 else 1.0
            green = int(255 * (1 - usage_ratio))
            white = int(255 * usage_ratio)
            pen_color = QColor(white, green, white)
        
        pen = QPen(pen_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        
        painter.drawEllipse(2, 2, self.width()-4, self.height()-4)
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
