"""VaRA-TS MainWindow."""

import typing as tp
from os import path

from PyQt5.QtWidgets import QMainWindow, QWidget

from varats.gui.buildsetup_window import BuildSetup
from varats.gui.filtertree_window import FilterWindow
from varats.gui.ui_MainWindow import Ui_MainWindow
from varats.gui.views.cr_bar_view import CRBarView
from varats.gui.views.example_view import ExampleView
from varats.settings import (
    CFG,
    create_missing_folders,
    generate_benchbuild_config,
    save_config,
)


class MainWindow(QMainWindow, Ui_MainWindow):  # type: ignore
    """Manages the GUI state and manages the different active views."""

    def __init__(self) -> None:
        super(MainWindow, self).__init__()
        self.views: tp.List[QWidget] = []
        self.bwg = None
        self.filter_window = None

        self.setupUi(self)  # type: ignore
        self.actionExampleView.triggered.connect(self._spawn_exampleview)
        self.actionCR_BarView.triggered.connect(self._spawn_cr_bar_view)

        # Signals for menubar
        self.actionVaRA_Setup.triggered.connect(self._spawn_vara_build_setup)
        self.actionInteractionFilter_Editor.triggered.connect(
            self._spawn_filter_editor
        )
        self.actionSave_Config.triggered.connect(self._save_config)
        self.actionCreate_BenchBuild_Config.triggered.connect(
            self._create_benchbuild_config
        )

        self.tabWidget.tabCloseRequested.connect(self.__remove_tab)

        self.show()

    def _spawn_exampleview(self) -> None:
        new_tab = ExampleView()  # type: ignore
        self.views.append(new_tab)

        self.tabWidget.addTab(new_tab, "ExampleView")

    def _spawn_cr_bar_view(self) -> None:
        new_tab = CRBarView()  # type: ignore
        self.views.append(new_tab)

        self.tabWidget.addTab(new_tab, "CR-BarView")

    def _spawn_vara_build_setup(self) -> None:
        """Spawn a setup window to configure and build VaRA."""
        self.bwg = BuildSetup()  # type: ignore
        if not isinstance(self.bwg, BuildSetup):
            raise AssertionError()
        self.bwg.show()

    def _spawn_filter_editor(self) -> None:
        """Spawn a filter editor window to configure interaction filters."""
        self.filter_window = FilterWindow()  # type: ignore
        if not isinstance(self.filter_window, FilterWindow):
            raise AssertionError()
        self.filter_window.show()

    @staticmethod
    def _save_config() -> None:
        """Save current config to file."""
        save_config()

    @staticmethod
    def _create_benchbuild_config() -> None:
        if CFG["config_file"].value is None:
            print(
                "No VaRA config found, please initialize a " +
                "VaRA config first."
            )
            return

        if CFG["benchbuild_root"].value is None:
            CFG["benchbuild_root"] = path.dirname(str(CFG["config_file"]))\
                                                  + "/benchbuild"
        create_missing_folders()

        generate_benchbuild_config(
            CFG,
            str(CFG["benchbuild_root"]) + "/.benchbuild.yml"
        )

    def __remove_tab(self, index: int) -> None:
        tab = self.tabWidget.widget(index)
        if tab is not None:
            self.views.remove(tab)

            self.tabWidget.removeTab(index)
