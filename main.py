#main.py
"""
Bone Segmentation 3D - Medical Imaging Application

Entry point for the application.
"""
import sys
import os

# Add src directory to path for package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication
from bone_segmentation.ui.main_window_init import MainWindow


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
