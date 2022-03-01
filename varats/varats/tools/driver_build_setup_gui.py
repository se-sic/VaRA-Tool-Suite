"""Driver module for `vara-buildsetup-gui`."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from varats.gui.buildsetup_window import BuildSetup
from varats.ts_utils.cli_util import initialize_cli_tool


class VaRATSSetup:
    """Start VaRA-TS grafical user interface for setting up VaRA."""

    def __init__(self) -> None:
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)
        self.main_window = BuildSetup()

    def main(self) -> None:
        """Start VaRA setup GUI."""
        sys.exit(self.app.exec_())


def main() -> None:
    """Start VaRA-TS driver and run application."""
    initialize_cli_tool()
    driver = VaRATSSetup()
    driver.main()


if __name__ == '__main__':
    main()
