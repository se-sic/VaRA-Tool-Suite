import sys
import typing as tp
from pathlib import Path

import benchbuild as bb
import pygit2
from PyQt5 import Qt
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox

from varats.gui.cs_gen.main_window_ui import Ui_MainWindow
from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.paper.case_study import CaseStudy, store_case_study
from varats.paper_mgmt.case_study import extend_with_extra_revs
from varats.project.project_util import (
    get_loaded_vara_projects,
    get_local_project_git_path,
    get_project_cls_by_name,
)
from varats.projects.discover_projects import initialize_projects
from varats.tools.research_tools.vara_manager import ProcessManager
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.utils import settings
from varats.utils.git_util import (
    get_initial_commit,
    get_all_revisions_between,
    FullCommitHash,
    create_commit_lookup_helper,
)
from varats.utils.settings import vara_cfg


class CsGenMainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.selected_commit = None
        self.setupUi(self)
        initialize_projects()
        projects = get_loaded_vara_projects()
        self.selected_project = None
        self.revision_list_project = None
        self.project_names = [
            project.NAME
            for project in projects
            if project.GROUP not in ["test_projects", "perf_test"]
        ]
        self.project_list.addItems(self.project_names)
        self.project_list.clicked['QModelIndex'].connect(self.show_project_data)
        self.revision_list.clicked['QModelIndex'].connect(
            self.show_revision_data
        )
        self.selectspecific.clicked.connect(self.show_revisions_of_project)
        self.generate.clicked.connect(self.gen_specific)
        self.show()

    def gen_specific(self):
        cmap = create_lazy_commit_map_loader(
            self.revision_list_project, None, 'HEAD', None
        )()
        case_study = CaseStudy(self.revision_list_project, 0)
        extend_with_extra_revs(case_study, cmap, [self.selected_commit], 0)
        paper_config = vara_cfg()["paper_config"]["current_config"].value
        path = Path(
            vara_cfg()["paper_config"]["folder"].value
        ) / (paper_config + f"/{ self.revision_list_project}_0.case_study")
        store_case_study(case_study, path)

    def show_project_data(self, index: QModelIndex):
        project_name = index.data()
        if self.selected_project != project_name:
            self.selected_project = project_name
            project = get_project_cls_by_name(project_name)
            project_info = f"{project_name.upper()} : \nDomain: {project.DOMAIN}\nSource: {bb.source.primary(*project.SOURCE)._remote}"
            self.project_details.setText(project_info)
            self.project_details.update()
            if self.revisions.isEnabled():
                self.show_revisions_of_project()

    def show_revisions_of_project(self):
        if self.selected_project != self.revision_list_project:
            self.revision_list.clear()
            git_path = get_local_project_git_path(self.selected_project)
            initial_commit = get_initial_commit(git_path).hash
            commits = get_all_revisions_between(
                initial_commit, 'HEAD', str, git_path
            )
            self.revision_list.addItems(commits.__reversed__())
            self.revision_list.update()
            self.revision_list_project = self.selected_project

    def show_revision_data(self, index):
        commit_hash = FullCommitHash(index.data())
        commit_lookup_helper = create_commit_lookup_helper(
            self.selected_project
        )
        commit: pygit2.Commit = commit_lookup_helper(commit_hash)
        commit_info = f"{commit.hex}\nAuthor:{commit.author.name},{commit.author.email}\nMsg:{commit.message}"
        self.selected_commit = commit_hash.hash
        self.revision_details.setText(commit_info)
        self.revision_details.update()


class VaRATSGui:
    """Start VaRA-TS grafical user interface for graphs."""

    def __init__(self) -> None:
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.app = QApplication(sys.argv)

        if settings.vara_cfg()["config_file"].value is None:
            err = QMessageBox()
            err.setIcon(QMessageBox.Warning)
            err.setWindowTitle("Missing config file.")
            err.setText(
                "Could not find VaRA config file.\n"
                "Should we create a config file in the current folder?"
            )

            err.setStandardButtons(
                tp.cast(
                    QMessageBox.StandardButtons,
                    QMessageBox.Yes | QMessageBox.No
                )
            )
            answer = err.exec_()
            if answer == QMessageBox.Yes:
                settings.save_config()
            else:
                sys.exit()

        self.main_window = CsGenMainWindow()

    def main(self) -> None:
        """Setup and Run Qt application."""
        ret = self.app.exec_()
        ProcessManager.shutdown()
        sys.exit(ret)


def main() -> None:
    """Start VaRA-TS driver and run application."""
    initialize_cli_tool()
    driver = VaRATSGui()
    driver.main()


if __name__ == '__main__':
    main()
