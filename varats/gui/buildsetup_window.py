"""
A module that manages the building of VaRa.
"""
import os

from PyQt5.QtWidgets import QWidget

from varats.gui.views.ui_BuildMenu import Ui_BuildSetup
from varats import vara_manager


class BuildSetup(QWidget, Ui_BuildSetup):
    """
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.folderPath.insert(os.getcwd() + "/VaRA/")
        self.installPath.insert(os.getcwd() + "/VaRA/install/")

        self.initButton.clicked.connect(self._setup_vara)
        self.buildButton.clicked.connect(self._build_vara)

    def _setup_vara(self):
        """
        Downloads VaRA to the current working directory.
        """
        path = self.__get_root_path()
        if not os.path.exists(path):
            os.makedirs(path)
        print(path)
        if os.listdir(path) == []:
            vara_manager.download_vara(path)
            vara_manager.checkout_vara_version(path + "llvm/", 60, True)
        else:
            # TODO: error dont want to over write
            pass

    def _build_vara(self):
        if self.checkDev.isChecked():
            vara_manager.build_vara(self.__get_llvm_path(),
                                    self.__get_install_path(),
                                    vara_manager.BuildType.DEV)

        if self.checkOpt.isChecked():
            raise NotImplementedError

    def __get_root_path(self):
        return self.folderPath.text()

    def __get_llvm_path(self):
        return self.__get_root_path() + "llvm/"

    def __get_install_path(self):
        return self.installPath.text()
