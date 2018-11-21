"""
VaRA-TS MainWindow
"""

from os import path, getcwd

from varats.settings import CFG, save_config
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
        super(self.__class__, self).__init__()
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

        # Local to lazy initialize BenchBuild config
        from benchbuild.settings import CFG as BB_CFG
        projects_conf = BB_CFG["plugins"]["projects"]
        projects_conf.value[:] = []
        # If we want later to use default BB projects
        # projects_conf.value[:] = [ x for x in projects_conf.value
        #                           if not x.endswith('gzip')]
        projects_conf.value[:] += ['varats.projects.c_projects.gzip']

        BB_CFG["env"] = {
            # TODO (sattlerf): add path to vara install here
            "path": "",
        }

        def replace_bb_cwd_path(cfg_varname, cfg_node=BB_CFG):
            cfg_node[cfg_varname] = str(CFG["benchbuild_root"]) +\
                str(cfg_node[cfg_varname])[len(getcwd()):]

        replace_bb_cwd_path("build_dir")
        replace_bb_cwd_path("tmp_dir")
        replace_bb_cwd_path("test_dir")
        replace_bb_cwd_path("node_dir", BB_CFG["slurm"])

        bb_config_path = str(CFG["benchbuild_root"]) + "/.benchbuild.yml"
        BB_CFG.store(bb_config_path)

    def __remove_tab(self, index):
        tab = self.tabWidget.widget(index)
        if tab is not None:
            self.views.remove(tab)

            self.tabWidget.removeTab(index)
