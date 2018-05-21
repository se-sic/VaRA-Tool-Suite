"""
Module to manage the CommitReport BarView
"""

from os.path import isfile

from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox

from varats.gui.views.ui_CRBarView import Ui_Form
from varats.data.data_manager import VDM
from varats.data.commit_report import CommitReport


class CRBarView(QWidget, Ui_Form):
    """
    Bar view for commit reports
    """

    def __init__(self):
        super(CRBarView, self).__init__()

        self.commit_report = None

        self.setupUi(self)
        self.plot_up.set_cf_plot(True)
        self.plot_up.hide()
        self.plot_down.set_cf_plot(False)
        self.plot_down.hide()

        self.loadCRButton.clicked.connect(self.load_commit_report)
        self.check_cf_graph.stateChanged.connect(self.enable_cf_plot)
        self.check_df_graph.stateChanged.connect(self.enable_df_plot)

    def load_commit_report(self):
        """
        Load new CommitReport from file_path.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load CommitReport file", "",
            "Yaml Files (*.yaml *.yml);;All Files (*)", options=options)

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

        if self.commit_report is None or \
                (self.commit_report is not None
                 and self.commit_report.path != file_path):
            self.statusLabel.setText("Loading file...")
            VDM.load_data_class(file_path, CommitReport,
                                self._set_new_commit_report)

    def _set_new_commit_report(self, commit_report):
        self.commit_report = commit_report
        if self.check_cf_graph.isChecked():
            self.plot_up.update_plot(self.commit_report)
        if self.check_df_graph.isChecked():
            self.plot_down.update_plot(self.commit_report)
        self.statusLabel.setText("")

    def enable_cf_plot(self, state: int):
        """
        Enable control-flow plot
        """
        if state is 0:  # turned off
            self.plot_up.hide()
        else:
            if self.commit_report is not None:
                self.plot_up.update_plot(self.commit_report)
            self.plot_up.show()

    def enable_df_plot(self, state: int):
        """
        Enable data-flow plot
        """
        if state is 0:  # turned off
            self.plot_down.hide()
        else:
            if self.commit_report is not None:
                self.plot_down.update_plot(self.commit_report)
            self.plot_down.show()
