"""
A module that manages the building of VaRa.
"""
import os

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor

from varats.gui.views.ui_BuildMenu import Ui_BuildSetup
from varats import vara_manager


class WorkerSignals(QObject):
    """
    Worker signal to communicate information back to the GUI.
    """
    finished = pyqtSignal()
    update = pyqtSignal(object)
    text_update = pyqtSignal(object)


class SetupWorker(QRunnable):
    """
    Setup worker to handle the setup of VaRA.
    """

    def __init__(self, path):
        super(self.__class__, self).__init__()
        self.path = path
        self.signals = WorkerSignals()
        self.steps = vara_manager.get_download_steps() + 2

    def _update_progress(self, val):
        self.signals.update.emit(val)

    def _update_text(self, text):
        self.signals.text_update.emit(text)

    def get_steps(self):
        return self.steps

    @pyqtSlot()
    def run(self):
        vara_manager.download_vara(self.path, self._update_progress, self._update_text)

        self._update_progress(7)
        vara_manager.checkout_vara_version(self.path + "llvm/", 60, True)

        self._update_progress(8)
        self.signals.finished.emit()


class BuildSetup(QWidget, Ui_BuildSetup):
    """
    Window to control the setup and status of the local VaRA installation.
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.folderPath.insert(os.getcwd() + "/VaRA/")
        self.installPath.insert(os.getcwd() + "/VaRA/install/")

        self.initButton.clicked.connect(self._setup_vara)
        self.buildButton.clicked.connect(self._build_vara)
        self.textOutput.setReadOnly(True)
        self.textOutput.ensureCursorVisible()

        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)

        self.statusLabel.hide()

        self.thread_pool = QThreadPool()

    def _update_progress(self, val):
        self.progressBar.setValue(val)

    def _update_text(self, text):
        self.textOutput.insertPlainText(text)
        self.textOutput.moveCursor(QTextCursor.End)

    def _setup_vara_test(self):
        print("Test setup")
        worker = SetupWorker()
        self.thread_pool.start(worker)

    def _setup_vara(self):
        """
        Downloads VaRA to the current working directory.
        """
        self.statusLabel.setText("Setting up VaRA")
        self.statusLabel.show()
        path = self.__get_root_path()
        if not os.path.exists(path):
            os.makedirs(path)

        if os.listdir(path) == []:
            worker = SetupWorker(path)
            worker.signals.finished.connect(self._setup_done)
            worker.signals.update.connect(self._update_progress)
            worker.signals.text_update.connect(self._update_text)
            self.progressBar.setMaximum(worker.get_steps())
            self.thread_pool.start(worker)
        else:
            self.statusLabel.setText("VaRA already checkout.")

    def _setup_done(self):
        self.statusLabel.setText("Finished setup")


    def _build_vara(self):
        self.statusLabel.setText("Building VaRA")
        if self.checkDev.isChecked():
            vara_manager.build_vara(self.__get_llvm_path(),
                                    self.__get_install_path(),
                                    vara_manager.BuildType.DEV)

        if self.checkOpt.isChecked():
            raise NotImplementedError

        self.statusLabel.setText("Finished build")

    def __get_root_path(self):
        return self.folderPath.text()

    def __get_llvm_path(self):
        return self.__get_root_path() + "llvm/"

    def __get_install_path(self):
        return self.installPath.text()
