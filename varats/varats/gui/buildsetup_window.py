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


class BuilderSignals(QObject):
    """Builder singals to communicate information back to the GUI."""
    finished = pyqtSignal()
    update = pyqtSignal(object)
    text_update = pyqtSignal(object)


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
        raise RuntimeError("Was removed")

    def _setup_done(self):
        self.statusLabel.setText("Finished setup")
        self._check_state()

    def _build_vara(self):
        raise RuntimeError("Was removed")

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
        pass

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
