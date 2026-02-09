#!/usr/bin/env python3
"""
Run script for Bone Segmentation 3D Application.

This script handles environment setup and launches the application.
"""
import os
import sys
import subprocess


def setup_qt_environment():
    """Set up Qt environment for proper plugin loading."""
    # Common conda environment paths
    conda_env = os.environ.get('CONDA_PREFIX')
    if conda_env:
        qt_plugin_path = os.path.join(conda_env, 'Library', 'plugins')
        if os.path.exists(qt_plugin_path):
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            print(f"Set QT_PLUGIN_PATH to: {qt_plugin_path}")


def main():
    """Main entry point."""
    setup_qt_environment()
    
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Add src to path
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Change to project root
    os.chdir(project_root)
    
    # Import and run
    from bone_segmentation.ui.main_window_init import MainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
