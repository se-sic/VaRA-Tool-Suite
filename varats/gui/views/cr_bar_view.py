"""
Module to manage the CommitReport BarView
"""

from os.path import isfile

from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox

from varats.gui.views.ui_CRBarView import Ui_Form
from varats.data.commit_report import CommitReport


class CRBarView(QWidget):
    """
    Bar view for commit reports
    """

    def __init__(self):
        super().__init__()
        self.ui_mw = Ui_Form()

        self.commit_report = None

        self.setup_ui()

    def setup_ui(self):
        """
        Setup CR-BarView
        """
        self.ui_mw.setupUi(self)
        self.ui_mw.plot_up.set_cf_plot(True)
        self.ui_mw.plot_down.set_cf_plot(False)

        self.ui_mw.loadCRButton.clicked.connect(self.load_commit_report)
        self.ui_mw.check_cf_graph.stateChanged.connect(self.enable_cf_plot)
        self.ui_mw.check_df_graph.stateChanged.connect(self.enable_df_plot)

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
            self.commit_report = CommitReport(file_path)
            if self.ui_mw.check_cf_graph.isChecked():
                self.ui_mw.plot_up.update_plot(self.commit_report)
            if self.ui_mw.check_df_graph.isChecked():
                self.ui_mw.plot_down.update_plot(self.commit_report)

    def enable_cf_plot(self, state: int):
        """
        Enable control-flow plot
        """
        if state is 0:  # turned off
            self.ui_mw.plot_up.hide()
        else:
            if self.commit_report is not None:
                self.ui_mw.plot_up.update_plot(self.commit_report)
            self.ui_mw.plot_up.show()

    def enable_df_plot(self, state: int):
        """
        Enable data-flow plot
        """
        if state is 0:  # turned off
            self.ui_mw.plot_down.hide()
        else:
            if self.commit_report is not None:
                self.ui_mw.plot_down.update_plot(self.commit_report)
            self.ui_mw.plot_down.show()
