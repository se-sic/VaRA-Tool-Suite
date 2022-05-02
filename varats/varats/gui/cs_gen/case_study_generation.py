"""Main Window of the case study generation Gui."""
import sys
import typing as tp
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

import benchbuild as bb
import pygit2
from PyQt5.QtCore import (
    QModelIndex,
    QDateTime,
    Qt,
    QSortFilterProxyModel,
    QAbstractTableModel,
)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox

from varats.base.sampling_method import NormalSamplingMethod
from varats.gui.cs_gen.case_study_generation_ui import Ui_MainWindow
from varats.mapping.commit_map import (
    create_lazy_commit_map_loader,
    get_commit_map,
    CommitMap,
)
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
    get_primary_project_source,
)
from varats.projects.discover_projects import initialize_projects
from varats.revision.revisions import is_revision_blocked
from varats.tools.research_tools.vara_manager import ProcessManager
from varats.utils import settings
from varats.utils.git_util import (
    get_initial_commit,
    get_all_revisions_between,
    ShortCommitHash,
    create_commit_lookup_helper,
    FullCommitHash,
    CommitRepoPair,
)
from varats.utils.settings import vara_cfg


class GenerationStrategie(Enum):
    """Enum for the Startegie used when Generating a CaseStudy."""
    SELECT_REVISION = 0
    SAMPLE = 1
    REVS_PER_YEAR = 2


class CsGenMainWindow(QMainWindow, Ui_MainWindow):
    """Main Application."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.selected_commit = None
        self.setupUi(self)
        initialize_projects()
        self.proxy_model = CommitTableFilterModel()
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.revision_list.setModel(self.proxy_model)
        self.selected_project = None
        self.revision_list_project = None
        self.update_project_list()
        self.project_list.clicked['QModelIndex'].connect(self.show_project_data)
        self.sampling_method.addItems([
            x.name()
            for x in NormalSamplingMethod.normal_sampling_method_types()
        ])
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.SELECT_REVISION.value
        )
        self.revision_list.clicked.connect(self.show_revision_data)
        self.select_specific.clicked.connect(self.revisions_of_project)
        self.sample.clicked.connect(self.sample_view)
        self.per_year.clicked.connect(self.revs_per_year_view)
        self.generate.clicked.connect(self.gen)
        self.project_search.textChanged.connect(self.update_project_list)
        self.revision_list.horizontalHeader().sortIndicatorChanged.connect(
            self.revision_list.sortByColumn
        )
        self.commit_search.textChanged.connect(
            self.proxy_model.setFilterFixedString
        )
        self.show()

    def update_project_list(self, filter_string: str = "") -> None:
        """Update the project list when a filter is applied."""
        self.project_list.clear()
        filter_string = filter_string.lower()
        projects = get_loaded_vara_projects()

        def match(project):
            return (filter_string in str(
                project.NAME
            ).lower()) or (filter_string in str(
                project.DOMAIN
            ).lower()) or (filter_string in str(project.GROUP).lower())

        self.project_names = [
            project.NAME
            for project in projects
            if project.GROUP not in ["test_projects", "perf_tests"] and
            match(project)
        ]
        self.project_list.addItems(self.project_names)

    def revs_per_year_view(self) -> None:
        """Switch to revision per year strategy view."""
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.REVS_PER_YEAR.value
        )
        self.strategie_forms.update()

    def sample_view(self):
        """Switch to sampling strategy view."""
        self.strategie_forms.setCurrentIndex(GenerationStrategie.SAMPLE.value)
        self.strategie_forms.update()

    def gen(self) -> None:
        """Generate the case study using the selected strategy, project and
        strategy specific arguments."""
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
                True, self.code_commits.clicked
            )
        elif self.strategie_forms.currentIndex(
        ) == GenerationStrategie.SELECT_REVISION.value:
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

    def show_project_data(self, index: QModelIndex) -> None:
        """Update the project data field."""
        project_name = index.data()
        if self.selected_project != project_name:
            self.selected_project = project_name
            project = get_project_cls_by_name(project_name)
            project_info = f"{project_name.upper()} : " \
                           f"\nDomain: {project.DOMAIN}" \
                           f"\nSource: " \
                           f"{bb.source.primary(*project.SOURCE).remote}"
            self.project_details.setText(project_info)
            self.project_details.update()
            if self.strategie_forms.currentIndex(
            ) == GenerationStrategie.SELECT_REVISION.value:
                self.revisions_of_project()

    def revisions_of_project(self) -> None:
        """Generate the Revision list for the selected project if select
        specific is enabled."""
        self.strategie_forms.setCurrentIndex(
            GenerationStrategie.SELECT_REVISION.value
        )
        if self.selected_project != self.revision_list_project:
            self.revision_details.setText("Loading Revisions")
            self.revision_details.repaint()
            get_local_project_git(self.selected_project).remotes[0].fetch()
            git_path = get_local_project_git_path(self.selected_project)
            initial_commit = get_initial_commit(git_path).hash
            commits = get_all_revisions_between(
                initial_commit, 'HEAD', FullCommitHash, git_path
            )
            commit_lookup_helper = create_commit_lookup_helper(
                self.selected_project
            )
            project = get_project_cls_by_name(self.selected_project)
            repo_name = get_primary_project_source(self.selected_project).local
            commits = map(
                lambda commit: CommitRepoPair(commit, repo_name), commits
            )

            cmap = get_commit_map(self.selected_project)
            commit_model = CommitTableModel(
                list(map(commit_lookup_helper, commits)), cmap, project
            )
            self.proxy_model.setSourceModel(commit_model)
            self.revision_list_project = self.selected_project
            self.revision_details.clear()
            self.revision_details.update()

    def show_revision_data(self, index: QModelIndex) -> None:
        """Update the revision data field."""
        commit = self.revision_list.model().data(index, Qt.WhatsThisRole)
        commit_info = f"{commit.hex}\nAuthor:{commit.author.name}," \
                      f"{commit.author.email}\n" \
                      f"Msg:{commit.message}"
        self.selected_commit = commit.hex
        self.revision_details.setText(commit_info)
        self.revision_details.update()


class CommitTableFilterModel(QSortFilterProxyModel):
    """Filter Model for the revision table."""
    filter_string = ""

    def setFilterFixedString(self, pattern: str) -> None:
        self.filter_string = pattern
        self.invalidate()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        commit_index = self.sourceModel().index(source_row, 0, source_parent)
        author_index = self.sourceModel().index(source_row, 1, source_parent)
        return self.sourceModel().data(commit_index,
                                       Qt.DisplayRole).lower() \
                   .__contains__(self.filter_string.lower()) \
               or self.sourceModel().data(author_index,
                                          Qt.DisplayRole).lower() \
                   .__contains__(self.filter_string.lower())


class CommitTableModel(QAbstractTableModel):
    """Date Model for the revision Table."""
    header_labels = ["Commit", "Author", "Date", "Time Id"]

    def __init__(
        self, data: tp.List[pygit2.Commit], cmap: CommitMap,
        project: tp.Type['bb.Project']
    ):
        super().__init__()
        self._project = project
        self._data = data
        self._cmap = cmap

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def sort(self, column: int, order: Qt.SortOrder = ...) -> None:
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda x: self.__split_commit_data(x, column),
            reverse=bool(order)
        )
        self.layoutChanged.emit()

    def __split_commit_data(self, commit: pygit2.Commit, column: int) -> tp.Any:
        if column == 0:
            return ShortCommitHash(commit.hex).hash
        if column == 1:
            return commit.author.name
        if column == 2:
            tzinfo = timezone(timedelta(minutes=commit.author.offset))
            date = datetime.fromtimestamp(float(commit.author.time), tzinfo)
            return QDateTime(date)
        if column == 3:
            return self._cmap.short_time_id(ShortCommitHash(commit.hex))

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> tp.Any:
        commit = self._data[index.row()]
        if role == Qt.DisplayRole:
            return self.__split_commit_data(commit, index.column())
        if is_revision_blocked(FullCommitHash(commit.hex), self._project):
            if role == Qt.ForegroundRole:
                return QColor(50, 100, 255)
            if role == Qt.ToolTipRole:
                return "Blocked"
        if role == Qt.WhatsThisRole:
            return commit

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 4


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


def start_gui() -> None:
    """Start VaRA-TS driver and run application."""
    driver = VaRATSGui()
    driver.main()


if __name__ == '__main__':
    start_gui()
