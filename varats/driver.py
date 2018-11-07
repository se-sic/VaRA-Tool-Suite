#!/usr/bin/env python3
"""
Main drivers for VaRA-TS
"""

import sys

from enum import Enum

from varats import settings
from varats.gui.main_window import MainWindow
from varats.gui.buildsetup_window import BuildSetup

from PyQt5.QtWidgets import QApplication, QMessageBox

class VaRATSGui():

    def __init__(self):
        self.app = QApplication(sys.argv)

        if settings.CFG["config_file"].value is None:
            err = QMessageBox()
            err.setIcon(QMessageBox.Warning)
            err.setWindowTitle("Missing config file.")
            err.setText("Could not find VaRA config file.\n"
                        "Should we create a config file in the current folder?")
            err.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            answer = err.exec_()
            if answer == QMessageBox.Yes:
                settings.save_config()
            else:
                sys.exit()

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
