"""Module to manage the CommitReport BarView."""

from os import path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget

from varats.data.data_manager import VDM
from varats.data.reports.commit_report import (
    CommitMap,
    CommitReport,
    CommitReportMeta,
)
from varats.gui.options import OptionTreeWidget
from varats.gui.views.ui_CRBarView import Ui_Form


class CRBarView(QWidget, Ui_Form):
    """Bar view for commit reports."""

    def __init__(self):
        super().__init__()

        self.commit_reports = []
        self.commit_report_merged_meta = CommitReportMeta()
        self.__current_report = None
        self.c_map = None
        self.loading_files = 0

        self.setupUi(self)
        self.plot_up.set_cf_plot(True)
        self.plot_up.hide()
        self.plot_down.set_cf_plot(False)
        self.plot_down.hide()

        self.loadCRButton.clicked.connect(self.load_commit_report)
        self.optionsTree.connect_cb_cic(self._update_report_order)
        self.optionsTree.itemChanged.connect(self._update_option)

        self.fileSlider.sliderReleased.connect(self._slider_moved)
        self.fileSlider.setTickPosition(2)
        self.playButton.clicked.connect(self._start_play)
        self.stopButton.clicked.connect(self._click_stop)
        self.__preview = False
        self._adjust_slider()
        self._play_timer = QTimer()
        self._play_timer.timeout.connect(self._click_next)

        self._update_report_order()

    @property
    def current_report(self):
        """Current shown commit report."""
        return self.__current_report

    @current_report.setter
    def current_report(self, report):
        self.__current_report = report
        c_hash = path.basename(self.current_report.path)[5:-5]
        self.infoTree.c_hash = c_hash
        if self.c_map is not None:
            self.infoTree.h_id = self.c_map.time_id(c_hash)

    def load_commit_report(self):
        """Load new CommitReport from file_path."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Load CommitReport file",
            "",
            "Yaml Files (*.yaml *.yml);;All Files (*)",
            options=options
        )

        for file_path in file_paths:
            if not path.isfile(file_path):
                err = QMessageBox()
                err.setIcon(QMessageBox.Warning)
                err.setWindowTitle("File not found.")
                err.setText("Could not find selected file.")
                err.setStandardButtons(QMessageBox.Ok)
                err.exec_()
                return

            if not (file_path.endswith(".yaml") or file_path.endswith(".yml")):
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
            self.statusLabel.setText(
                "Loading files... " + str(self.loading_files)
            )
            VDM.load_data_class(
                file_path, CommitReport, self._set_new_commit_report
            )

    def _update_option(self, item, col):
        text = item.text(0)
        if text == OptionTreeWidget.OPT_CR_MR:
            self._draw_plots()
        elif text == self.optionsTree.OPT_SCF:
            self.enable_cf_plot(item.checkState(1))
        elif text == self.optionsTree.OPT_SDF:
            self.enable_df_plot(item.checkState(1))
        elif text == self.optionsTree.OPT_CR_RORDER:
            self._update_report_order()
        elif text == self.optionsTree.OPT_CR_CMAP:
            c_map_path = item.text(1)
            if path.isfile(c_map_path):
                with open(c_map_path, "r") as c_map_file:
                    self.c_map = CommitMap(c_map_file.readlines())

                if self.current_report is not None:
                    self.current_report = self.current_report
            else:
                self.c_map = None
            self._update_report_order()
        else:
            raise LookupError("Could not find matching option")

    def _set_new_commit_report(self, commit_report):
        self.loading_files -= 1

        if commit_report not in self.commit_reports:
            self.commit_reports.append(commit_report)
            self.commit_report_merged_meta.merge(commit_report)
            self._adjust_slider()

        if self.loading_files == 0:
            self.statusLabel.setText("")
        else:
            self.statusLabel.setText(
                "Loading files... " + str(self.loading_files)
            )

        self._update_report_order()

    def _draw_plots(self) -> None:
        if self.current_report is None:
            return
        meta = None
        if self.optionsTree.merge_report_checkstate != Qt.Unchecked:
            meta = self.commit_report_merged_meta

        if self.optionsTree.show_cf_checkstate != Qt.Unchecked:
            self.plot_up.update_plot(self.current_report, meta)
        if self.optionsTree.show_df_checkstate != Qt.Unchecked:
            self.plot_down.update_plot(self.current_report, meta)

    def _adjust_slider(self):
        self.fileSlider.setMaximum(max(len(self.commit_reports) - 1, 0))
        self._slider_moved()

    def _slider_moved(self):
        if len(self.commit_reports) >= 1:
            self.current_report = self\
                .commit_reports[self.fileSlider.value()]
            self._draw_plots()

    def enable_cf_plot(self, state: int) -> None:
        """Enable control-flow plot."""
        if state == Qt.Unchecked:  # turned off
            self.plot_up.hide()
        else:
            self._draw_plots()
            self.plot_up.show()

    def enable_df_plot(self, state: int):
        """Enable data-flow plot."""
        if state == Qt.Unchecked:  # turned off
            self.plot_down.hide()
        else:
            self._draw_plots()
            self.plot_down.show()

    def _update_report_order(self):
        text = self.optionsTree.report_order

        if text == 'Linear History':

            def order_func(x):
                file_path = x.path
                filename = path.basename(file_path)
                c_hash = filename[5:-5]
                if self.c_map is not None:
                    return self.c_map.time_id(c_hash)
                return c_hash
        else:

            def order_func(x):
                return x

        self.commit_reports.sort(key=order_func)
        if self.current_report is not None:
            idx = self.commit_reports.index(self.current_report)
            self.fileSlider.setSliderPosition(idx)

    def _start_play(self):
        self._play_timer.start(self.optionsTree.play_time)

    def _click_next(self):
        self.__preview = True
        self._next_commit_report()
        if self.fileSlider.value() >= self.fileSlider.maximum():
            self._click_stop()

    def _next_commit_report(self):
        if self.__preview:
            self.fileSlider.setSliderPosition(self.fileSlider.value() + 1)
            self._slider_moved()

    def _click_stop(self):
        self.__preview = False
        self._play_timer.stop()
