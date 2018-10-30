"""
VaRA-TS MainWindow
"""

from varats.settings import CFG
from varats.gui.ui_MainWindow import Ui_MainWindow
from varats.gui.views.example_view import ExampleView
from varats.gui.views.cr_bar_view import CRBarView
from varats.gui.buildsetup_window import BuildSetup

from PyQt5.QtWidgets import QMainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Manages the GUI state and manages the different active views.
    """

    def __init__(self):
        super(self.__class__, self).__init__()
        self.views = []
        self.bwg = None

        self.setupUi(self)
        self.actionExampleView.triggered.connect(self._spawn_exampleview)
        self.actionCR_BarView.triggered.connect(self._spawn_cr_bar_view)

        # Signals for menubar
        self.actionVaRA_Setup.triggered.connect(self._spawn_vara_setup)
        self.actionSave_Config.triggered.connect(self._save_config)

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

    def _spawn_vara_setup(self):
        """
        Spawn a setup window to configure and build VaRA
        """
        self.bwg = BuildSetup()
        self.bwg.show()

    def _save_config(self):
        """
        Save current config to file.
        """
        if CFG["config_file"].value == None:
            config_file = ".vara.yaml"
        else:
            config_file = str(CFG["config_file"])
        CFG.store(config_file)

    def __remove_tab(self, index):
        tab = self.tabWidget.widget(index)
        if tab is not None:
            self.views.remove(tab)

            self.tabWidget.removeTab(index)
