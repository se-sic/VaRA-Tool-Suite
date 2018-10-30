#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import sys

from enum import Enum

from varats import settings
from varats.gui.main_window import MainWindow
from varats.gui.buildsetup_window import BuildSetup

from PyQt5.QtWidgets import QApplication

class VaRATSGui():

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()

    def main(self):
        """Setup and Run Qt application"""
        sys.exit(self.app.exec_())


class VaRATSSetup():

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = BuildSetup()

    def main(self):
        sys.exit(self.app.exec_())


def main_graph_view():
    """
    Start VaRA-TS driver and run application.
    """
    driver = VaRATSGui()
    driver.main()


def main_setup():
    """
    Start VaRA BuildSetup driver and run application.
    """
    raise NotImplementedError
    driver = VaRATSSetup()
    driver.main()


if __name__ == "__main__":
    main()
