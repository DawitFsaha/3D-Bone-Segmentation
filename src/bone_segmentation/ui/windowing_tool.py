# windowing_tool.py - Simplified without automatic real-time preview

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QHBoxLayout, QSizePolicy, QFrame, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor


class WindowingTool(QWidget):
    # NO automatic windowing_changed signal - user must click Apply

    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            # Standard HU range for CT imaging
            self.min_hu = -1024  # Air
            self.max_hu = 3071  # Dense bone

            # Standard window presets for medical imaging
            self.window_presets = {
                "Bone": {"center": 1000, "width": 1800},
                "Soft Tissue": {"center": 40, "width": 400},
                "Lung": {"center": -600, "width": 1600},
                "Brain": {"center": 40, "width": 80},
                "Liver": {"center": 60, "width": 160},
                "Mediastinum": {"center": 50, "width": 350},
                "Custom": {"center": 40, "width": 400}
            }

            self.current_preset = "Bone"
            self.initUI()
            self.apply_preset("Bone")
        except Exception as e:
            print(f"Failed to initialize WindowingTool: {str(e)}")

    def initUI(self):
        try:
            layout = QVBoxLayout()
            layout.setSpacing(10)  # Add more spacing between elements
            layout.setContentsMargins(10, 10, 10, 10)  # Add margins around the layout

            # Preset selection
            preset_layout = QHBoxLayout()
            preset_layout.setSpacing(8)  # Add spacing between label and combo

            preset_label = QLabel("Preset:")
            preset_label.setFont(QFont('Arial', 8))  # Back to 8pt
            preset_label.setMinimumHeight(25)  # Ensure adequate height

            self.preset_combo = QComboBox()
            self.preset_combo.addItems(list(self.window_presets.keys()))
            self.preset_combo.setCurrentText(self.current_preset)
            self.preset_combo.currentTextChanged.connect(self.on_preset_changed)

            # Fix the ComboBox styling and sizing issues
            self.preset_combo.setFont(QFont('Arial', 8))  # Back to 8pt
            self.preset_combo.setMinimumHeight(28)  # Increased height
            self.preset_combo.setMinimumWidth(120)

            # Set comprehensive stylesheet for the ComboBox
            combo_style = """
                QComboBox {
                    background-color: white;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 3px 18px 3px 6px;
                    font-size: 8pt;
                    font-family: Arial;
                    color: black;
                    selection-background-color: #0078d4;
                }

                QComboBox:hover {
                    border: 1px solid #0078d4;
                }

                QComboBox:focus {
                    border: 2px solid #0078d4;
                }

                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 15px;
                    border-left-width: 1px;
                    border-left-color: #cccccc;
                    border-left-style: solid;
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                    background-color: #f0f0f0;
                }

                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid #666666;
                    width: 0px;
                    height: 0px;
                }

                QComboBox QAbstractItemView {
                    background-color: white;
                    border: 1px solid #cccccc;
                    selection-background-color: #0078d4;
                    selection-color: white;
                    font-size: 8pt;
                    font-family: Arial;
                    color: black;
                    padding: 2px;
                    min-width: 120px;
                }

                QComboBox QAbstractItemView::item {
                    background-color: white;
                    color: black;
                    padding: 4px 8px;
                    border: none;
                    min-height: 18px;
                }

                QComboBox QAbstractItemView::item:selected {
                    background-color: #0078d4;
                    color: white;
                }

                QComboBox QAbstractItemView::item:hover {
                    background-color: #e6f3ff;
                    color: black;
                }
            """

            self.preset_combo.setStyleSheet(combo_style)

            preset_layout.addWidget(preset_label)
            preset_layout.addWidget(self.preset_combo)
            layout.addLayout(preset_layout)

            # Add spacing after preset selection
            layout.addSpacing(12)  # Increased spacing

            # Window display label
            self.label = QLabel("Window: C:1000 W:1800 (Range: 100 to 1900)")
            self.label.setFont(QFont('Arial', 8))  # Back to 8pt
            self.label.setAlignment(Qt.AlignCenter)
            self.label.setMinimumHeight(25)  # Ensure adequate height
            layout.addWidget(self.label)

            # Status label - shows that user needs to click Apply
            self.status_label = QLabel("")
            self.status_label.setFont(QFont('Arial', 8))  # Slightly larger
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("color: #666666; font-style: italic;")
            self.status_label.setMinimumHeight(20)  # Ensure adequate height
            layout.addWidget(self.status_label)

            # Window Center slider
            center_layout = QHBoxLayout()
            center_layout.setSpacing(5)  # Add spacing between elements

            center_title = QLabel("Center:")
            center_title.setFont(QFont('Arial', 8))  # Back to 8pt
            center_title.setFixedWidth(45)  # Slightly wider
            center_title.setMinimumHeight(25)  # Ensure adequate height

            self.center_label_left = QLabel("-")
            self.center_label_left.setFont(QFont('Arial', 14))
            self.center_label_left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.center_label_left.setCursor(QCursor(Qt.PointingHandCursor))
            self.center_label_left.mousePressEvent = self.decrease_center

            self.center_slider = QSlider(Qt.Horizontal)
            self.center_slider.setMinimum(self.min_hu)
            self.center_slider.setMaximum(self.max_hu)
            self.center_slider.setValue(1000)  # Default bone center
            self.center_slider.valueChanged.connect(self.update_windowing_display)
            self.center_slider.setMaximumWidth(200)  # Restrict slider width

            self.center_label_right = QLabel("+")
            self.center_label_right.setFont(QFont('Arial', 13))
            self.center_label_right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.center_label_right.setCursor(QCursor(Qt.PointingHandCursor))
            self.center_label_right.mousePressEvent = self.increase_center

            center_layout.addWidget(center_title)
            center_layout.addWidget(self.center_label_left)
            center_layout.addWidget(self.center_slider)
            center_layout.addWidget(self.center_label_right)

            # Window Width slider
            width_layout = QHBoxLayout()
            width_layout.setSpacing(5)  # Add spacing between elements

            width_title = QLabel("Width:")
            width_title.setFont(QFont('Arial', 8))  # Back to 8pt
            width_title.setFixedWidth(45)  # Slightly wider
            width_title.setMinimumHeight(25)  # Ensure adequate height

            self.width_label_left = QLabel("-")
            self.width_label_left.setFont(QFont('Arial', 14))
            self.width_label_left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.width_label_left.setCursor(QCursor(Qt.PointingHandCursor))
            self.width_label_left.mousePressEvent = self.decrease_width

            self.width_slider = QSlider(Qt.Horizontal)
            self.width_slider.setMinimum(1)  # Minimum width of 1
            self.width_slider.setMaximum(4000)  # Maximum practical width
            self.width_slider.setValue(1800)  # Default bone width
            self.width_slider.valueChanged.connect(self.update_windowing_display)
            self.width_slider.setMaximumWidth(200)  # Restrict slider width

            self.width_label_right = QLabel("+")
            self.width_label_right.setFont(QFont('Arial', 13))
            self.width_label_right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.width_label_right.setCursor(QCursor(Qt.PointingHandCursor))
            self.width_label_right.mousePressEvent = self.increase_width

            width_layout.addWidget(width_title)
            width_layout.addWidget(self.width_label_left)
            width_layout.addWidget(self.width_slider)
            width_layout.addWidget(self.width_label_right)

            layout.addLayout(center_layout)
            layout.addLayout(width_layout)

            self.setLayout(layout)
            self.setFixedSize(360, 150)  # Increased both width and height to accommodate better spacing
        except Exception as e:
            print(f"Failed to initialize UI: {str(e)}")

    def on_preset_changed(self, preset_name):
        """Handle preset selection change"""
        try:
            if preset_name != "Custom":
                self.apply_preset(preset_name)
            self.current_preset = preset_name
        except Exception as e:
            print(f"Failed to change preset: {str(e)}")

    def apply_preset(self, preset_name):
        """Apply a windowing preset"""
        try:
            if preset_name in self.window_presets:
                preset = self.window_presets[preset_name]

                # Block signals to prevent recursive updates
                self.center_slider.blockSignals(True)
                self.width_slider.blockSignals(True)

                self.center_slider.setValue(preset["center"])
                self.width_slider.setValue(preset["width"])

                # Unblock signals and update
                self.center_slider.blockSignals(False)
                self.width_slider.blockSignals(False)

                self.update_windowing_display()
                print(f"Applied {preset_name} preset: Center={preset['center']}, Width={preset['width']}")
        except Exception as e:
            print(f"Failed to apply preset: {str(e)}")

    def update_windowing_display(self):
        """Update windowing display ONLY - no automatic application"""
        try:
            center = self.center_slider.value()
            width = self.width_slider.value()

            # Calculate min and max values from center and width
            min_val = center - width // 2
            max_val = center + width // 2

            # Update label
            self.label.setText(f"Window: C:{center} W:{width} (Range: {min_val} to {max_val})")

            # If user manually adjusts sliders, switch to Custom preset
            if self.sender() in [self.center_slider, self.width_slider]:
                if self.current_preset != "Custom":
                    self.preset_combo.blockSignals(True)
                    self.preset_combo.setCurrentText("Custom")
                    self.preset_combo.blockSignals(False)
                    self.current_preset = "Custom"

            # NO automatic signal emission - user must click Apply

        except Exception as e:
            print(f"Failed to update windowing display: {str(e)}")

    def get_values(self):
        """Get current min and max values"""
        try:
            center = self.center_slider.value()
            width = self.width_slider.value()
            min_val = center - width // 2
            max_val = center + width // 2
            return min_val, max_val
        except Exception as e:
            print(f"Failed to get windowing values: {str(e)}")
            return 100, 1900  # Default fallback

    def get_center_width(self):
        """Get current center and width values"""
        try:
            return self.center_slider.value(), self.width_slider.value()
        except Exception as e:
            print(f"Failed to get center/width values: {str(e)}")
            return 1000, 1800  # Default fallback

    # Center adjustment methods
    def decrease_center(self, event):
        try:
            self.center_slider.setValue(self.center_slider.value() - 10)
        except Exception as e:
            print(f"Failed to decrease center: {str(e)}")

    def increase_center(self, event):
        try:
            self.center_slider.setValue(self.center_slider.value() + 10)
        except Exception as e:
            print(f"Failed to increase center: {str(e)}")

    # Width adjustment methods
    def decrease_width(self, event):
        try:
            current_width = self.width_slider.value()
            new_width = max(1, current_width - 10)  # Ensure minimum width of 1
            self.width_slider.setValue(new_width)
        except Exception as e:
            print(f"Failed to decrease width: {str(e)}")

    def increase_width(self, event):
        try:
            self.width_slider.setValue(self.width_slider.value() + 10)
        except Exception as e:
            print(f"Failed to increase width: {str(e)}")

    # Legacy methods for compatibility
    @property
    def min_slider(self):
        """Legacy property for compatibility"""

        class MockSlider:
            def value(self):
                center = self.parent.center_slider.value()
                width = self.parent.width_slider.value()
                return center - width // 2

            def __init__(self, parent):
                self.parent = parent

        return MockSlider(self)

    @property
    def max_slider(self):
        """Legacy property for compatibility"""

        class MockSlider:
            def value(self):
                center = self.parent.center_slider.value()
                width = self.parent.width_slider.value()
                return center + width // 2

            def __init__(self, parent):
                self.parent = parent

        return MockSlider(self)