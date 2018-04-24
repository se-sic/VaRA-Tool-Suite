"""
VaRA-TS MainWindow
"""

from varats.gui.ui_MainWindow import Ui_MainWindow
from varats.gui.views.example_view import ExampleView
from varats.gui.views.cr_bar_view import CRBarView

from PyQt5.QtWidgets import QMainWindow

class MainWindow(object):
    """
    Manages the GUI state and manages the different active views.
    """

    def __init__(self):
        self.ui_mw = Ui_MainWindow()
        self.main_window = QMainWindow()
        self.views = []

        self.setup_ui()

    def setup_ui(self):
        """
        Setup main GUI
        """
        self.ui_mw.setupUi(self.main_window)
        self.ui_mw.actionExampleView.triggered.connect(self._spawn_exampleview)
        self.ui_mw.actionCR_BarView.triggered.connect(self._spawn_cr_bar_view)

        self.ui_mw.tabWidget.tabCloseRequested.connect(self.__remove_tab)

        self.main_window.show()

    def _spawn_exampleview(self):
        new_tab = ExampleView()
        self.views.append(new_tab)

        self.ui_mw.tabWidget.addTab(new_tab, "ExampleView")

    def _spawn_cr_bar_view(self):
        new_tab = CRBarView()
        self.views.append(new_tab)

        self.ui_mw.tabWidget.addTab(new_tab, "CR-BarView")

    def __remove_tab(self, index):
        tab = self.ui_mw.tabWidget.widget(index)
        if tab is not None:
            self.views.remove(tab)

            self.ui_mw.tabWidget.removeTab(index)
