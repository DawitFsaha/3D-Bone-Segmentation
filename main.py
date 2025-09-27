#main.py
import sys
from PyQt5.QtWidgets import QApplication
from main_window_init import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
