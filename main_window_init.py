# main_window_init.py

from PyQt5.QtWidgets import (QMainWindow, QAction, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QWidget, QPushButton,
                             QScrollBar, QSplitter, QFrame, QSlider, QLabel, QComboBox)
from PyQt5.QtCore import Qt
from image_viewer import ImageViewer
from windowing_tool import WindowingTool
from main_window_functions import MainWindowFunctions


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.functions = MainWindowFunctions(self)
        self.initUI()

        # Simple processing flags - no complications
        self.threshold_applied = False
        self.contrast_applied = False
        self.windowing_applied = False  # Simple flag - when user clicks Apply Windowing
        self.filter_applied = False

    def initUI(self):
        try:
            self.setWindowTitle(
                'Patient-Specific 3D Model Generation for Preoperative Planning - Enhanced Density Visualization')

            openFile = QAction('Open File', self)
            openFile.triggered.connect(self.functions.showFileDialog)

            openFolder = QAction('Open Folder', self)
            openFolder.triggered.connect(self.functions.showFolderDialog)

            menubar = self.menuBar()
            fileMenu = menubar.addMenu('&File')
            fileMenu.addAction(openFile)
            fileMenu.addAction(openFolder)

            # Create image viewers with orientation
            self.coronal_view = ImageViewer(orientation='coronal')
            self.sagittal_view = ImageViewer(orientation='sagittal')
            self.axial_view = ImageViewer(orientation='axial')

            # Set up direct references for immediate updates
            self.coronal_view.set_functions_reference(self.functions)
            self.sagittal_view.set_functions_reference(self.functions)
            self.axial_view.set_functions_reference(self.functions)

            # Connect ROI signals
            self.coronal_view.roi_changed.connect(self.functions.on_roi_changed)
            self.sagittal_view.roi_changed.connect(self.functions.on_roi_changed)
            self.axial_view.roi_changed.connect(self.functions.on_roi_changed)

            self.empty_view = QWidget()
            self.empty_view.setFixedSize(400, 450)  # Increased height for controls

            self.coronal_scrollbar = QScrollBar(Qt.Vertical)
            self.coronal_scrollbar.valueChanged.connect(self.functions.update_coronal_view)
            self.coronal_scrollbar.setEnabled(False)

            self.sagittal_scrollbar = QScrollBar(Qt.Vertical)
            self.sagittal_scrollbar.valueChanged.connect(self.functions.update_sagittal_view)
            self.sagittal_scrollbar.setEnabled(False)

            self.axial_scrollbar = QScrollBar(Qt.Vertical)
            self.axial_scrollbar.valueChanged.connect(self.functions.update_axial_view)
            self.axial_scrollbar.setEnabled(False)

            self.loadFolderButton = QPushButton("Import CT|MRI Dataset")
            self.loadFolderButton.clicked.connect(self.functions.showFolderDialog)

            # Clear ROI button
            self.clear_roi_button = QPushButton("Clear ROI")
            self.clear_roi_button.setEnabled(False)
            self.clear_roi_button.clicked.connect(self.functions.clear_roi)

            # Threshold slider
            self.threshold_slider = QSlider(Qt.Horizontal)
            self.threshold_slider.setMinimum(0)
            self.threshold_slider.setMaximum(255)
            self.threshold_slider.setValue(128)
            self.threshold_slider.setTickInterval(1)
            self.threshold_slider.setTickPosition(QSlider.TicksBelow)

            self.threshold_label = QLabel(f"Threshold: {self.threshold_slider.value()}")
            self.threshold_slider.valueChanged.connect(self.functions.update_threshold_label)

            # Apply threshold button
            self.apply_threshold_button = QPushButton("Apply Threshold")
            self.apply_threshold_button.setEnabled(False)
            self.apply_threshold_button.clicked.connect(self.functions.apply_threshold)

            # Contrast slider
            self.contrast_slider = QSlider(Qt.Horizontal)
            self.contrast_slider.setMinimum(0)
            self.contrast_slider.setMaximum(100)
            self.contrast_slider.setValue(0)
            self.contrast_slider.setTickInterval(1)
            self.contrast_slider.setTickPosition(QSlider.TicksBelow)

            self.contrast_label = QLabel(f"Contrast: {self.contrast_slider.value()}")
            self.contrast_slider.valueChanged.connect(self.functions.update_contrast_label)

            # Apply contrast button
            self.apply_contrast_button = QPushButton("Apply Contrast")
            self.apply_contrast_button.setEnabled(False)
            self.apply_contrast_button.clicked.connect(self.functions.apply_contrast)

            self.filtering_label = QLabel("Filtering Method:")
            self.filtering_combobox = QComboBox()
            self.filtering_combobox.addItems(["Gaussian Filter", "Median Filter"])
            self.filtering_combobox.currentIndexChanged.connect(self.functions.update_filter_value)

            self.filter_value_combobox = QComboBox()
            self.filter_value_combobox.addItems([str(i) for i in range(1, 11)])

            self.apply_filter_button = QPushButton("Apply Filter")
            self.apply_filter_button.setEnabled(False)
            self.apply_filter_button.clicked.connect(self.functions.apply_filter)

            # Create a horizontal layout for the filter selection
            filtering_layout = QHBoxLayout()
            filtering_layout.addWidget(self.filtering_label)
            filtering_layout.addWidget(self.filtering_combobox)
            filtering_layout.addWidget(self.filter_value_combobox)

            # Create a frame to hold the filtering layout and button
            filtering_frame = QFrame()
            filtering_frame.setLayout(QVBoxLayout())
            filtering_frame.layout().addLayout(filtering_layout)
            filtering_frame.layout().addWidget(self.apply_filter_button)
            filtering_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            filtering_frame.setLineWidth(2)
            filtering_frame.setFixedSize(360, 100)

            # Build 3D view button - Enhanced with density visualization
            self.build_3d_button = QPushButton("Build 3D")
            self.build_3d_button.setFixedSize(130, 40)
            self.build_3d_button.setEnabled(False)
            self.build_3d_button.clicked.connect(self.functions.build_3d_view)

            # Pop out 3D view button
            self.popout_3d_button = QPushButton("Pop Out 3D")
            self.popout_3d_button.setFixedSize(100, 40)
            self.popout_3d_button.setEnabled(False)
            self.popout_3d_button.clicked.connect(self.functions.popout_3d_view)

            # Export 3D to STL button
            self.export_3d_button = QPushButton("3D to STL")
            self.export_3d_button.setFixedSize(100, 40)
            self.export_3d_button.setEnabled(False)
            self.export_3d_button.clicked.connect(self.functions.export_3d_to_stl)

            # Create a horizontal layout for the 3D buttons
            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(self.build_3d_button)
            buttons_layout.addWidget(self.popout_3d_button)
            buttons_layout.addWidget(self.export_3d_button)

            # Create a frame to hold the buttons layout
            buttons_frame = QFrame()
            buttons_frame.setLayout(buttons_layout)
            buttons_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            buttons_frame.setLineWidth(2)
            buttons_frame.setFixedSize(380, 70)  # Slightly wider for new button text

            # Simplified Windowing tool - NO real-time preview complications
            self.windowing_tool = WindowingTool()

            self.apply_windowing_button = QPushButton("Apply Windowing")
            self.apply_windowing_button.setEnabled(False)
            self.apply_windowing_button.clicked.connect(self.functions.apply_windowing)

            # Create a frame to hold the windowing tool layout
            windowing_layout = QVBoxLayout()
            windowing_layout.addWidget(self.windowing_tool)
            windowing_layout.addWidget(self.apply_windowing_button)
            windowing_frame = QFrame()
            windowing_frame.setLayout(windowing_layout)
            windowing_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            windowing_frame.setLineWidth(2)
            windowing_frame.setFixedSize(360, 230)  # Reduced height

            # Add information panel for density visualization
            self.density_info_frame = QFrame()
            density_info_layout = QVBoxLayout()

            density_title = QLabel("3D Density Visualization Info")
            density_title.setStyleSheet("font-weight: bold; color: #2E3440; font-size: 11px;")

            density_help = QLabel("• Build 3D model with applied processing settings\n"
                                  "• Different colors represent tissue densities\n"
                                  "• Click on 3D model to see exact HU values\n"
                                  "• Use controls above 3D view to customize display")
            density_help.setStyleSheet("color: #5E81AC; font-size: 9px;")
            density_help.setWordWrap(True)

            density_info_layout.addWidget(density_title)
            density_info_layout.addWidget(density_help)
            self.density_info_frame.setLayout(density_info_layout)
            self.density_info_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            self.density_info_frame.setLineWidth(1)
            self.density_info_frame.setFixedSize(360, 80)

            # Toolbox layout - Updated with density info
            self.toolbox_layout = QVBoxLayout()
            self.toolbox_layout.addWidget(self.loadFolderButton)
            self.toolbox_layout.addWidget(self.clear_roi_button)
            self.toolbox_layout.addWidget(self.threshold_label)
            self.toolbox_layout.addWidget(self.threshold_slider)
            self.toolbox_layout.addWidget(self.apply_threshold_button)
            self.toolbox_layout.addWidget(self.contrast_label)
            self.toolbox_layout.addWidget(self.contrast_slider)
            self.toolbox_layout.addWidget(self.apply_contrast_button)
            self.toolbox_layout.addWidget(filtering_frame)
            self.toolbox_layout.addWidget(windowing_frame)
            self.toolbox_layout.addWidget(buttons_frame)
            self.toolbox_layout.addWidget(self.density_info_frame)
            self.toolbox_layout.addStretch()

            toolbox_container = QFrame()
            toolbox_container.setLayout(self.toolbox_layout)
            toolbox_container.setFixedSize(400, 950)  # Increased height for density info
            toolbox_container.setFrameStyle(QFrame.Box | QFrame.Raised)
            toolbox_container.setLineWidth(2)

            # Adjusting the layout to place scrollbars on the right side of each view
            coronal_layout = QVBoxLayout()
            coronal_title = QLabel("Coronal View")
            coronal_layout.addWidget(coronal_title)
            coronal_view_layout = QHBoxLayout()
            coronal_view_layout.addWidget(self.coronal_view)
            coronal_view_layout.addWidget(self.coronal_scrollbar)
            coronal_layout.addLayout(coronal_view_layout)

            sagittal_layout = QVBoxLayout()
            sagittal_title = QLabel("Sagittal View")
            sagittal_title.setAlignment(Qt.AlignCenter)
            sagittal_layout.addWidget(sagittal_title)
            sagittal_view_layout = QHBoxLayout()
            sagittal_view_layout.addWidget(self.sagittal_view)
            sagittal_view_layout.addWidget(self.sagittal_scrollbar)
            sagittal_layout.addLayout(sagittal_view_layout)

            axial_layout = QVBoxLayout()
            axial_title = QLabel("Axial View")
            axial_title.setAlignment(Qt.AlignCenter)
            axial_layout.addWidget(axial_title)
            axial_view_layout = QHBoxLayout()
            axial_view_layout.addWidget(self.axial_view)
            axial_view_layout.addWidget(self.axial_scrollbar)
            axial_layout.addLayout(axial_view_layout)

            empty_layout = QVBoxLayout()
            empty_title = QLabel("3D Density Visualization")
            empty_title.setAlignment(Qt.AlignCenter)
            empty_title.setStyleSheet("font-weight: bold; color: #2E3440;")
            empty_layout.addWidget(empty_title)
            empty_view_layout = QHBoxLayout()
            empty_view_layout.addWidget(self.empty_view)
            empty_layout.addLayout(empty_view_layout)

            grid_layout = QGridLayout()
            grid_layout.setSpacing(10)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.addLayout(coronal_layout, 0, 0)
            grid_layout.addLayout(sagittal_layout, 0, 1)
            grid_layout.addLayout(axial_layout, 1, 0)
            grid_layout.addLayout(empty_layout, 1, 1)

            left_side_layout = QHBoxLayout()
            left_side_layout.addWidget(toolbox_container)
            left_side_layout.addLayout(grid_layout)

            left_container = QWidget()
            left_container.setLayout(left_side_layout)

            right_container = QWidget()

            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(left_container)
            splitter.addWidget(right_container)
            splitter.setSizes([1000, 800])

            main_layout = QHBoxLayout()
            main_layout.addWidget(splitter)

            container = QWidget()
            container.setLayout(main_layout)
            self.setCentralWidget(container)

            self.showMaximized()
        except Exception as e:
            print(f"Error: {str(e)}")