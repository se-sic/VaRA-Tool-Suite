"""Driver module for `vara-graphview`."""
import sys
import typing as tp

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from varats.gui.main_window import MainWindow
from varats.tools.research_tools.vara_manager import ProcessManager
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.utils import settings


class VaRATSGui:
    """Start VaRA-TS grafical user interface for graphs."""

    def __init__(self) -> None:
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)

        if settings.vara_cfg()["config_file"].value is None:
            err = QMessageBox()
            err.setIcon(QMessageBox.Warning)
            err.setWindowTitle("Missing config file.")
            err.setText(
                "Could not find VaRA config file.\n"
                "Should we create a config file in the current folder?"
            )

            err.setStandardButtons(
                tp.cast(
                    QMessageBox.StandardButtons,
                    QMessageBox.Yes | QMessageBox.No
                )
            )
            answer = err.exec_()
            if answer == QMessageBox.Yes:
                settings.save_config()
            else:
                sys.exit()

        self.main_window = MainWindow()

    def main(self) -> None:
        """Setup and Run Qt application."""
        ret = self.app.exec_()
        ProcessManager.shutdown()
        sys.exit(ret)


def main() -> None:
    """Start VaRA-TS driver and run application."""
    initialize_cli_tool()
    driver = VaRATSGui()
    driver.main()


if __name__ == '__main__':
    main()
