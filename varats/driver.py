#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import sys

from varats.gui.main_window import MainWindow

from PyQt5.QtWidgets import QApplication

class VaRATSGui():

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()

    def main(self):
        """Setup and Run Qt application"""
        sys.exit(self.app.exec_())


def main():
    """
    Setup correct VaRA-TS driver an run application.
    """
    driver = VaRATSGui()

    driver.main()


if __name__ == "__main__":
    main()
