"""
Module for different CommitReport plots
"""

import seaborn as sns

from PyQt5.QtWidgets import QWidget, QGridLayout

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg \
    as FigureCanvas

from varats.data.commit_report import CommitReport, generate_inout_cfg_cf,\
    generate_inout_cfg_df


class CRBarPlotWidget(QWidget):
    """
    Bar plotting widget for CommitReports
    """

    def __init__(self, parent):
        super(CRBarPlotWidget, self).__init__(parent)

        self.cf_plot = True

        self.fig = plt.figure()
        plot_cfg_barplot(self.fig, None, self.cf_plot)
        self.canvas = FigureCanvas(self.fig)

        layout = QGridLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def __del__(self):
        """
        Clean up matplotlib figures.
        """
        if self.fig is not None:
            plt.close(self.fig)

    def set_cf_plot(self, is_cf_plot: bool):
        """
        Sets if the plot widget shows a control-flow graph
        or a data-flow graph
        """
        self.cf_plot = is_cf_plot

    def update_plot(self, commit_report: CommitReport):
        """
        Update the canvas with a new plot, generated from updated data.
        """
        plot_cfg_barplot(self.fig, commit_report, self.cf_plot)
        self.canvas.draw()


def plot_cfg_barplot(fig, commit_report: CommitReport, draw_cf: bool):
    """
    Generates a bar plot that visualizes the IN/OUT
    control-flow/data-flow edges of regions.
    """
    if commit_report is None:
        return
    if draw_cf:
        data = generate_inout_cfg_cf(commit_report)
        color_palette = "muted"
    else:
        data = generate_inout_cfg_df(commit_report)
        color_palette = "Set2"

    if data.empty:
        # TODO: add logging
        print("Error: CommitReport has no CF interactions")
        return

    plt.figure(fig.number)
    plt.clf()
    bar_p = sns.barplot(x="Region", y="Amount",
                        hue="Direction", data=data, palette=color_palette)
    for label in bar_p.get_xticklabels():
        label.set_rotation(20)

    fig.add_subplot(bar_p)
