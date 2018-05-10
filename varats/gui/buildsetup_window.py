"""
A module that manages the building of VaRa.
"""
import os

from PyQt5.QtWidgets import QWidget

from varats.gui.views.ui_BuildMenu import Ui_BuildSetup
from varats import vara_manager


class BuildSetup(QWidget):
    """
    """

    def __init__(self):
        super().__init__()
        self.ui_setup = Ui_BuildSetup()
        self.ui_setup.setupUi(self)

        self.ui_setup.folderPath.insert(os.getcwd() + "/VaRA/")
        self.ui_setup.installPath.insert(os.getcwd() + "/VaRA/bin/")

        self.ui_setup.initButton.clicked.connect(self._setup_vara)

    def _setup_vara(self):
        """
        Downloads VaRA to the current working directory.
        """
        path = self.ui_setup.folderPath.text()
        if not os.path.exists(path):
            os.makedirs(path)
        vara_manager.download_vara(path)
        vara_manager.checkout_vara_version(path + "llvm/", 60, True)
