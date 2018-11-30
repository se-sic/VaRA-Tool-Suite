"""
VaRA-TS MainWindow
"""

from os import path

from varats.settings import CFG, save_config, generate_benchbuild_config
from varats.gui.ui_MainWindow import Ui_MainWindow
from varats.gui.views.example_view import ExampleView
from varats.gui.views.cr_bar_view import CRBarView
from varats.gui.buildsetup_window import BuildSetup, create_missing_folders

from PyQt5.QtWidgets import QMainWindow, QMessageBox

class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Manages the GUI state and manages the different active views.
    """

    def __init__(self):
        super(MainWindow, self).__init__()
        self.views = []
        self.bwg = None

        self.setupUi(self)
        self.actionExampleView.triggered.connect(self._spawn_exampleview)
        self.actionCR_BarView.triggered.connect(self._spawn_cr_bar_view)

        # Signals for menubar
        self.actionVaRA_Setup.triggered.connect(self._spawn_vara_build_setup)
        self.actionSave_Config.triggered.connect(self._save_config)
        self.actionCreate_BenchBuild_Config.triggered.connect(
            self._create_benchbuild_config)

        self.tabWidget.tabCloseRequested.connect(self.__remove_tab)

        self.show()

    def _spawn_exampleview(self):
        new_tab = ExampleView()
        self.views.append(new_tab)

        self.tabWidget.addTab(new_tab, "ExampleView")

    def _spawn_cr_bar_view(self):
        new_tab = CRBarView()
        self.views.append(new_tab)

        self.tabWidget.addTab(new_tab, "CR-BarView")

    def _spawn_vara_build_setup(self):
        """
        Spawn a setup window to configure and build VaRA
        """
        self.bwg = BuildSetup()
        self.bwg.show()

    def _save_config(self):
        """
        Save current config to file.
        """
        save_config()

    def _create_benchbuild_config(self):
        if CFG["config_file"].value is None:
            print("No VaRA config found, please initialize a VaRA config first.")
            return

        if CFG["benchbuild_root"].value is None:
            CFG["benchbuild_root"] = path.dirname(str(CFG["config_file"]))\
                                                  + "/benchbuild"
        create_missing_folders()

        generate_benchbuild_config(CFG,
                                   str(CFG["benchbuild_root"]) +
                                   "/.benchbuild.yml")

    def __remove_tab(self, index):
        tab = self.tabWidget.widget(index)
        if tab is not None:
            self.views.remove(tab)

            self.tabWidget.removeTab(index)
