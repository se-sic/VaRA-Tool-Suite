
from varats.gui.views.ui_CRBarView import Ui_Form
from varats.data.commit_report import CommitReport, generate_cfg_barplot

from PyQt5.QtWidgets import QWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class CRBarView(QWidget):
    """
    Bar view for commit reports
    """

    def __init__(self):
        super().__init__()
        self.ui_mw = Ui_Form()

        self.commit_report = CommitReport(
            "")

        self.fig = generate_cfg_barplot(self.commit_report)
        self.canvas = FigureCanvas(self.fig)

        self.setup_ui()

    def setup_ui(self):
        """
        Setup CR-BarView
        """
        self.ui_mw.setupUi(self)
        self.ui_mw.gridLayout.addWidget(self.canvas)

    def clean(self):
        """
        Clean up View, e.g., figures
        """
        if self.fig is not None:
            plt.close(self.fig)
