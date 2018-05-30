"""
Module to manage the CommitReport BarView
"""

from os.path import isfile

from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt

from varats.gui.views.ui_CRBarView import Ui_Form
from varats.data.data_manager import VDM
from varats.data.commit_report import CommitReport, CommitReportMeta


class CRBarView(QWidget, Ui_Form):
    """
    Bar view for commit reports
    """
    __GRP_CR = "CommitReport"
    __OPT_CR_MR = "Merge reports"

    __OPT_SCF = "Show CF graph"
    __OPT_SDF = "Show DF graph"

    def __init__(self):
        super(CRBarView, self).__init__()

        self.commit_reports = []
        self.commit_report_merged_meta = CommitReportMeta()
        self.current_report = None
        self.loading_files = 0

        self.setupUi(self)
        self.plot_up.set_cf_plot(True)
        self.plot_up.hide()
        self.plot_down.set_cf_plot(False)
        self.plot_down.hide()

        self.loadCRButton.clicked.connect(self.load_commit_report)
        self.treeWidget.itemChanged.connect(self._update_option)

        self.fileSlider.sliderReleased.connect(self._slider_moved)
        self.fileSlider.setTickPosition(2)
        self._adjust_slider()

    def load_commit_report(self):
        """
        Load new CommitReport from file_path.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Load CommitReport file", "",
            "Yaml Files (*.yaml *.yml);;All Files (*)", options=options)

        for file_path in file_paths:
            if not isfile(file_path):
                err = QMessageBox()
                err.setIcon(QMessageBox.Warning)
                err.setWindowTitle("File not found.")
                err.setText("Could not find selected file.")
                err.setStandardButtons(QMessageBox.Ok)
                err.exec_()
                return

            if not (file_path.endswith(".yaml")
                    or file_path.endswith(".yml")):
                err = QMessageBox()
                err.setIcon(QMessageBox.Warning)
                err.setWindowTitle("Wrong File ending.")
                err.setText("File seems not to be a yaml file.")
                err.setStandardButtons(QMessageBox.Ok)
                err.exec_()
                return

        for file_path in file_paths:
            skip = False
            for current_report in self.commit_reports:
                # skip files that were loaded bevor
                if current_report.path == file_path:
                    skip = True
                    continue
            if skip:
                continue
            self.loading_files += 1
            self.statusLabel.setText("Loading files... " +
                                     str(self.loading_files))
            VDM.load_data_class(file_path, CommitReport,
                                self._set_new_commit_report)

    def _update_option(self, item, col):
        text = item.text(col)
        if text == self.__OPT_CR_MR:
            self._draw_plots()
        elif text == self.__OPT_SCF:
            self.enable_cf_plot(item.checkState(col))
        elif text == self.__OPT_SDF:
            self.enable_df_plot(item.checkState(col))
        else:
            raise LookupError("Could not find matching option")

    def _set_new_commit_report(self, commit_report):
        self.loading_files -= 1

        if commit_report not in self.commit_reports:
            self.commit_reports.append(commit_report)
            self.commit_report_merged_meta.merge(commit_report)
            self._adjust_slider()

        if self.loading_files is 0:
            self.statusLabel.setText("")
        else:
            self.statusLabel.setText("Loading files... " +
                                     str(self.loading_files))

    def _draw_plots(self):
        if self.current_report is None:
            return
        meta = None
        if self.__get_mr_state() != Qt.Unchecked:
            meta = self.commit_report_merged_meta

        if self.__get_scf_state() != Qt.Unchecked:
            self.plot_up.update_plot(self.current_report, meta)
        if self.__get_sdf_state() != Qt.Unchecked:
            self.plot_down.update_plot(self.current_report, meta)

    def _adjust_slider(self):
        self.fileSlider.setMaximum(len(self.commit_reports) - 1)
        self._slider_moved()

    def _slider_moved(self):
        if len(self.commit_reports) >= 1:
            self.current_report = self\
                .commit_reports[self.fileSlider.value()]
            self._draw_plots()

    def enable_cf_plot(self, state: int):
        """
        Enable control-flow plot
        """
        if state == Qt.Unchecked:  # turned off
            self.plot_up.hide()
        else:
            self._draw_plots()
            self.plot_up.show()

    def enable_df_plot(self, state: int):
        """
        Enable data-flow plot
        """
        if state == Qt.Unchecked:  # turned off
            self.plot_down.hide()
        else:
            self._draw_plots()
            self.plot_down.show()

    def __get_mr_state(self):
        items = self.treeWidget.findItems(self.__GRP_CR, Qt.MatchExactly)
        if not items:
            return Qt.Unchecked
        grp = items[0]
        for i in range(0, grp.childCount()):
            if grp.child(i).text(0) == self.__OPT_CR_MR:
                return grp.child(i).checkState(0)
        return Qt.Unchecked

    def __get_scf_state(self):
        items = self.treeWidget.findItems(self.__OPT_SCF, Qt.MatchExactly)
        if not items:
            return Qt.Unchecked
        return items[0].checkState(0)

    def __get_sdf_state(self):
        items = self.treeWidget.findItems(self.__OPT_SDF, Qt.MatchExactly)
        if not items:
            return Qt.Unchecked
        return items[0].checkState(0)
