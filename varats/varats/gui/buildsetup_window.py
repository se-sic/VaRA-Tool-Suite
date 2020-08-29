"""A module that manages the building of VaRa."""
import os
import re
from pathlib import Path

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence, QTextCursor
from PyQt5.QtWidgets import QShortcut, QWidget

from varats.gui.views.ui_BuildMenu import Ui_BuildSetup
from varats.tools.research_tools import vara_manager
from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.settings import get_value_or_default, save_config, vara_cfg


class WorkerSignals(QObject):
    """Worker signal to communicate information back to the GUI."""
    finished = pyqtSignal()
    update = pyqtSignal(object)
    text_update = pyqtSignal(object)


class SetupWorker(QRunnable):
    """Setup worker to handle the setup of VaRA."""

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
        """Get the amount of sets to init VaRA."""
        return self.steps

    @pyqtSlot()
    def run(self):
        """Run, initializes VaRA in a different thread."""
        try:
            vara_manager.download_vara(
                self.path, self._update_progress, self._update_text
            )

            self._update_progress(7)
            vara_manager.checkout_vara_version(
                self.path, True,
                vara_cfg()['vara']['version'], True
            )

            self._update_progress(8)
            self.signals.finished.emit()
        except ProcessTerminatedError:
            print("Process was terminated")


class BuilderSignals(QObject):
    """Builder singals to communicate information back to the GUI."""
    finished = pyqtSignal()
    update = pyqtSignal(object)
    text_update = pyqtSignal(object)


class BuildWorker(QRunnable):
    """BuildWorker to build an install VaRA."""

    def __init__(
        self, path_to_llvm, install_prefix, build_type: vara_manager.BuildType
    ):
        super(BuildWorker, self).__init__()
        self.signals = BuilderSignals()
        self.path_to_llvm = path_to_llvm
        self.install_prefix = install_prefix
        self.build_type = build_type

    def _update_text(self, text):
        self.signals.text_update.emit(text)

    @pyqtSlot()
    def run(self):
        """Run, build an installs VaRA in a diffrent thread."""
        try:
            vara_manager.build_vara(
                Path(self.path_to_llvm), self.install_prefix, self.build_type,
                self._update_text
            )
            self.signals.finished.emit()
        except ProcessTerminatedError:
            print("Process was terminated")


class BuildSetup(QWidget, Ui_BuildSetup):
    """Window to control the setup and status of the local VaRA installation."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.__quit_sc = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.__quit_sc.activated.connect(self.close)

        llvm_src_dir = get_value_or_default(
            vara_cfg()["vara"], "llvm_source_dir",
            str(os.getcwd()) + "/vara-llvm/"
        )
        self.sourcePath.insert(llvm_src_dir)
        self.sourcePath.editingFinished.connect(self._update_source_dir)

        llvm_install_dir = get_value_or_default(
            vara_cfg()["vara"], "llvm_install_dir",
            str(os.getcwd()) + "/VaRA/"
        )
        self.installPath.insert(llvm_install_dir)
        self.installPath.editingFinished.connect(self._update_install_dir)

        self.initButton.clicked.connect(self._setup_vara)
        self.buildButton.clicked.connect(self._build_vara)
        self.textOutput.setReadOnly(True)
        self.textOutput.ensureCursorVisible()

        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)

        self.statusLabel.hide()

        self.advanced_view = False
        self._set_advanced_view()
        self.advancedMode.clicked.connect(self._toggle_advanced_view)

        self.vara_state_mgr = \
            vara_manager.VaRAStateManager(self.__get_llvm_source_path())
        self.updateButton.clicked\
            .connect(self.vara_state_mgr.update_current_branch)
        self.vara_state_mgr.state_signal\
            .status_update.connect(self._update_version)

        self._update_source_dir()
        self._update_install_dir()

        self.thread_pool = QThreadPool()
        self._check_state()

    def _update_progress(self, val):
        self.progressBar.setValue(val)

    def _update_build_text(self, text):
        match = re.match(r"\[([0-9]+)/([0-9]+)\].*", text)
        if match is not None:
            processed_files = int(match.group(1))
            max_files = int(match.group(2))
            self.progressBar.setMaximum(max_files)
            self.progressBar.setValue(processed_files)
        self._update_text(text)

    def _update_text(self, text):
        self.textOutput.insertPlainText(text)
        self.textOutput.moveCursor(QTextCursor.End)

    def _setup_vara(self):
        """Downloads VaRA to the current working directory."""
        self.statusLabel.setText("Setting up VaRA...")
        self.statusLabel.show()
        path = self.__get_llvm_source_path()

        if os.path.exists(path):
            self.statusLabel.setText("VaRA already checkout.")
        else:
            worker = SetupWorker(path)
            worker.signals.finished.connect(self._setup_done)
            worker.signals.update.connect(self._update_progress)
            worker.signals.text_update.connect(self._update_text)
            self.progressBar.setMaximum(worker.get_steps())
            self.thread_pool.start(worker)

    def _setup_done(self):
        self.statusLabel.setText("Finished setup")
        self._check_state()

    def _build_vara(self):
        self.statusLabel.setText("Building VaRA")
        if self.checkDev.isChecked():
            worker = BuildWorker(
                self.__get_llvm_source_path(), self.__get_install_path(),
                vara_manager.BuildType.DEV
            )
            worker.signals.finished.connect(self._build_done)
            worker.signals.text_update.connect(self._update_build_text)
            self.thread_pool.start(worker)

        if self.checkOpt.isChecked():
            raise NotImplementedError

    def _build_done(self):
        self.progressBar.setValue(self.progressBar.maximum())
        self.statusLabel.setText("Finished build")

    def _toggle_advanced_view(self):
        self.advanced_view = not self.advanced_view
        self._set_advanced_view()

    def _set_advanced_view(self):
        if self.advanced_view:
            self.checkDev.setChecked(False)
            self.checkDev.show()
            self.checkOpt.show()
        else:
            self.checkDev.setChecked(True)
            self.checkDev.hide()
            self.checkOpt.hide()

    def _check_state(self):
        self._check_init()
        self._check_versions()

    def _check_init(self):
        path = self.__get_llvm_source_path()
        self.vara_state_mgr.change_llvm_source_folder(path)
        if not os.path.exists(path):
            self.initButton.setEnabled(True)
            self.updateButton.setDisabled(True)
            self.buildButton.setDisabled(True)
        else:
            self.initButton.setDisabled(True)
            self.updateButton.setEnabled(True)
            self.buildButton.setEnabled(True)

    def _check_versions(self):
        if not os.path.exists(self.__get_llvm_source_path()):
            self.llvmStatus.setText("---")
            self.llvmStatus.setStyleSheet("QLabel { color : black; }")
            self.clangStatus.setText("---")
            self.clangStatus.setStyleSheet("QLabel { color : black; }")
            self.varaStatus.setText("---")
            self.varaStatus.setStyleSheet("QLabel { color : black; }")
        else:
            self.llvmStatus.setText("checking...")
            self.llvmStatus.setStyleSheet("QLabel { color : black; }")
            self.clangStatus.setText("checking...")
            self.clangStatus.setStyleSheet("QLabel { color : black; }")
            self.varaStatus.setText("checking...")
            self.varaStatus.setStyleSheet("QLabel { color : black; }")
            self.vara_state_mgr.check_repo_state()

    def _update_version(self, llvm_status, clang_status, vara_status):
        self.llvmStatus.setText(str(llvm_status))
        if llvm_status.state == vara_manager.GitState.OK:
            self.llvmStatus.setStyleSheet("QLabel { color : green; }")
        else:
            self.llvmStatus.setStyleSheet("QLabel { color : orange; }")

        self.clangStatus.setText(str(clang_status))
        if clang_status.state == vara_manager.GitState.OK:
            self.clangStatus.setStyleSheet("QLabel { color : green; }")
        else:
            self.clangStatus.setStyleSheet("QLabel { color : orange; }")

        self.varaStatus.setText(str(vara_status))
        if vara_status.state == vara_manager.GitState.OK:
            self.varaStatus.setStyleSheet("QLabel { color : green; }")
        else:
            self.varaStatus.setStyleSheet("QLabel { color : orange; }")

    def _update_source_dir(self):
        vara_cfg()["vara"]["llvm_source_dir"] = self.__get_llvm_source_path()
        save_config()
        self._check_state()

    def _update_install_dir(self):
        vara_cfg()["vara"]["llvm_install_dir"] = self.__get_install_path()
        save_config()

    def __get_llvm_source_path(self):
        return self.sourcePath.text()

    def __get_install_path(self):
        return self.installPath.text()
