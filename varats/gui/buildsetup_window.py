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
        super(SetupWorker, self).__init__()
        self.path = path
        self.signals = WorkerSignals()
        self.steps = vara_manager.get_download_steps() + 2

    def _update_progress(self, val):
        self.signals.update.emit(val)

    def _update_text(self, text):
        self.signals.text_update.emit(text)

    def get_steps(self):
        """
        Get the amount of sets to init VaRA.
        """
        return self.steps

    @pyqtSlot()
    def run(self):
        """
        Run, initializes VaRA in a different thread.
        """
        vara_manager.download_vara(self.path, self._update_progress,
                                   self._update_text)

        self._update_progress(7)
        vara_manager.checkout_vara_version(self.path + "llvm/", 60, True)

        self._update_progress(8)
        self.signals.finished.emit()


class BuilderSignals(QObject):
    """
    Builder singals to communicate information back to the GUI.
    """
    finished = pyqtSignal()
    update = pyqtSignal(object)
    text_update = pyqtSignal(object)


class BuildWorker(QRunnable):
    """
    BuildWorker to build an install VaRA.
    """

    def __init__(self, path_to_llvm, install_prefix,
                 build_type: vara_manager.BuildType):
        super(BuildWorker, self).__init__()
        self.signals = BuilderSignals()
        self.path_to_llvm = path_to_llvm
        self.install_prefix = install_prefix
        self.build_type = build_type

    def _update_text(self, text):
        self.signals.text_update.emit(text)

    @pyqtSlot()
    def run(self):
        """
        Run, build an installs VaRA in a diffrent thread.
        """
        vara_manager.build_vara(self.path_to_llvm,
                                self.install_prefix,
                                self.build_type,
                                self._update_text)


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

    def _update_build_text(self, text):
        # TODO: handle extra progrssbar updates
        self._update_text(text)

    def _update_text(self, text):
        self.textOutput.insertPlainText(text)
        self.textOutput.moveCursor(QTextCursor.End)

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
            worker = BuildWorker(self.__get_llvm_path(),
                                 self.__get_install_path(),
                                 vara_manager.BuildType.DEV)
            worker.signals.finished.connect(self._build_done)
            worker.signals.text_update.connect(self._update_build_text)
            self.thread_pool.start(worker)

        if self.checkOpt.isChecked():
            raise NotImplementedError

    def _build_done(self):
        self.statusLabel.setText("Finished build")

    def __get_root_path(self):
        return self.folderPath.text()

    def __get_llvm_path(self):
        return self.__get_root_path() + "llvm/"

    def __get_install_path(self):
        return self.installPath.text()
