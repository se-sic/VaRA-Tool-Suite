import sys
import typing as tp
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

import benchbuild as bb
import pygit2
from PyQt5.QtCore import QModelIndex, QDateTime, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QMessageBox,
    QTableWidgetItem,
    QStyledItemDelegate,
)

from varats.base.sampling_method import NormalSamplingMethod
from varats.gui.cs_gen.main_window_ui import Ui_MainWindow
from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.paper.case_study import CaseStudy, store_case_study
from varats.paper_mgmt.case_study import (
    extend_with_extra_revs,
    extend_with_distrib_sampling,
    extend_with_revs_per_year,
)
from varats.project.project_util import (
    get_loaded_vara_projects,
    get_local_project_git_path,
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.projects.discover_projects import initialize_projects
from varats.revision.revisions import is_revision_blocked
from varats.tools.research_tools.vara_manager import ProcessManager
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.utils import settings
from varats.utils.git_util import (
    get_initial_commit,
    get_all_revisions_between,
    ShortCommitHash,
    create_commit_lookup_helper,
)
from varats.utils.settings import vara_cfg


class GenerationStrategie(Enum):
    SELECTREVISION = 0
    SAMPLE = 1
    REVS_PER_YEAR = 2


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
            if project.GROUP not in ["test_projects", "perf_tests"]
        ]
        self.project_list.addItems(self.project_names)
        self.project_list.clicked['QModelIndex'].connect(self.show_project_data)
        self.sampling_method.addItems([
            x.name()
            for x in NormalSamplingMethod.normal_sampling_method_types()
        ])
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.SELECTREVISION.value
        )
        self.revision_list.cellClicked.connect(self.show_revision_data)
        self.select_specific.clicked.connect(self.show_revisions_of_project)
        self.sample.clicked.connect(self.sample_view)
        self.per_year.clicked.connect(self.revs_per_year_view)
        self.generate.clicked.connect(self.gen)
        self.show()

    def revs_per_year_view(self):
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.REVS_PER_YEAR.value
        )
        self.strategie_forms.update()

    def sample_view(self):
        self.strategie_forms.setCurrentIndex(GenerationStrategie.SAMPLE.value)
        self.strategie_forms.update()

    def gen(self):
        cmap = create_lazy_commit_map_loader(
            self.selected_project, None, 'HEAD', None
        )()
        version = self.cs_version.value()
        case_study = CaseStudy(self.revision_list_project, version)
        paper_config = vara_cfg()["paper_config"]["current_config"].value
        path = Path(vara_cfg()["paper_config"]["folder"].value) / (
            paper_config + f"/{self.revision_list_project}_{version}.case_study"
        )

        if self.strategie_forms.currentIndex(
        ) == GenerationStrategie.SAMPLE.value:
            sampling_method = NormalSamplingMethod.get_sampling_method_type(
                self.sampling_method.currentText()
            )
            extend_with_distrib_sampling(
                case_study, cmap, sampling_method(), 0, self.num_revs.value(),
                True
            )
        elif self.strategie_forms.currentIndex(
        ) == GenerationStrategie.SELECTREVISION.value:
            selected_rows = self.revision_list.selectionModel().selectedRows(0)
            selected_commits = [row.data() for row in selected_rows]
            extend_with_extra_revs(case_study, cmap, selected_commits, 0)
            self.revision_list.clearSelection()
            self.revision_list.update()
        elif self.strategie_forms.currentIndex(
        ) == GenerationStrategie.REVS_PER_YEAR.value:
            extend_with_revs_per_year(
                case_study, cmap, 0, True,
                get_local_project_git_path(self.selected_project),
                self.revs_per_year.value(), self.seperate.checkState()
            )
        store_case_study(case_study, path)

    def show_project_data(self, index: QModelIndex):
        project_name = index.data()
        if self.selected_project != project_name:
            self.selected_project = project_name
            project = get_project_cls_by_name(project_name)
            project_info = f"{project_name.upper()} : \nDomain: {project.DOMAIN}\nSource: {bb.source.primary(*project.SOURCE).remote}"
            self.project_details.setText(project_info)
            self.project_details.update()
            if self.strategie_forms.currentIndex(
            ) == GenerationStrategie.SELECTREVISION.value:
                self.show_revisions_of_project()

    def show_revisions_of_project(self):
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.SELECTREVISION.value
        )
        if self.selected_project != self.revision_list_project:
            get_local_project_git(self.selected_project).remotes[0].fetch()
            self.revision_list.clearContents()
            self.revision_list.setRowCount(0)
            self.revision_list.repaint()
            self.revision_details.setText("Loading Revisions")
            self.revision_details.repaint()
            git_path = get_local_project_git_path(self.selected_project)
            initial_commit = get_initial_commit(git_path).hash
            commits = get_all_revisions_between(
                initial_commit, 'HEAD', ShortCommitHash, git_path
            )
            self.revision_list.setRowCount(len(commits))
            commit_lookup_helper = create_commit_lookup_helper(
                self.selected_project
            )

            project = get_project_cls_by_name(self.selected_project)
            for n, commit_hash in enumerate(commits):
                commit: pygit2.Commit = commit_lookup_helper(commit_hash)
                commit_hash = ShortCommitHash.from_pygit_commit(commit)

                self.revision_list.setItem(
                    n, 0, QTableWidgetItem(commit_hash.short_hash)
                )
                if is_revision_blocked(commit_hash, project):
                    self.revision_list.item(n,
                                            0).setForeground(QColor(125, 0, 0))
                    self.revision_list.item(n, 0).setToolTip("Blocked")
                self.revision_list.setItem(
                    n, 1, QTableWidgetItem(commit.author.name)
                )
                tzinfo = timezone(timedelta(minutes=commit.author.offset))
                date = datetime.fromtimestamp(float(commit.author.time), tzinfo)
                table_item = QTableWidgetItem()
                table_item.setData(Qt.DisplayRole, QDateTime(date))
                self.revision_list.setItem(n, 2, table_item)
            self.revision_list.setItemDelegateForColumn(
                2, DateDelegate(self.revision_list)
            )
            self.revision_list.resizeColumnsToContents()
            self.revision_list.setSortingEnabled(True)
            self.revision_details.clear()
            self.revision_details.update()
            self.revision_list.update()
            self.revision_list_project = self.selected_project

    def show_revision_data(self, row, column):
        index = self.revision_list.item(row, 0)
        commit_hash = ShortCommitHash(index.text())
        commit_lookup_helper = create_commit_lookup_helper(
            self.selected_project
        )
        commit: pygit2.Commit = commit_lookup_helper(commit_hash)
        commit_info = f"{commit.hex}\nAuthor:{commit.author.name},{commit.author.email}\nMsg:{commit.message}"
        self.selected_commit = commit_hash.hash
        self.revision_details.setText(commit_info)
        self.revision_details.update()


class DateDelegate(QStyledItemDelegate):

    def displayText(self, value, locale):
        if isinstance(value, QDateTime):
            return locale.toString(value, "dd-MM-yyyy")
        return super().displayText(value, locale)


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
