"""Module for different CommitReport plots."""

import logging
import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QGridLayout, QSizePolicy, QWidget

from varats.data.reports.commit_report import (
    CommitReport,
    CommitReportMeta,
    generate_inout_cfg_cf,
    generate_inout_cfg_df,
)

LOG = logging.getLogger(__name__)


class CRBarPlotWidget(QWidget):
    """Bar plotting widget for CommitReports."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.cf_plot = True

        self.fig = plt.figure()
        plot_cfg_barplot(self.fig, None, self.cf_plot, None)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        layout = QGridLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def __del__(self) -> None:
        """Clean up matplotlib figures."""
        if self.fig is not None:
            plt.close(self.fig)

    def set_cf_plot(self, is_cf_plot: bool) -> None:
        """Sets if the plot widget shows a control-flow graph or a data-flow
        graph."""
        self.cf_plot = is_cf_plot

    def update_plot(
        self,
        commit_report: CommitReport,
        cr_meta: tp.Optional[CommitReportMeta] = None
    ) -> None:
        """Update the canvas with a new plot, generated from updated data."""
        plot_cfg_barplot(self.fig, commit_report, self.cf_plot, cr_meta)
        self.canvas.draw()


def plot_cfg_barplot(
    fig: plt.Figure, commit_report: tp.Optional[CommitReport], draw_cf: bool,
    cr_meta: tp.Optional[CommitReportMeta]
) -> None:
    """Generates a bar plot that visualizes the IN/OUT control-flow/data-flow
    edges of regions."""
    if commit_report is None:
        return

    ylimit = None
    if draw_cf:
        data = generate_inout_cfg_cf(commit_report, cr_meta)
        color_palette = sns.color_palette(["#004949", "#920000"])
        if cr_meta is not None:
            ylimit = cr_meta.cf_ylimit
    else:
        data = generate_inout_cfg_df(commit_report, cr_meta)
        color_palette = sns.color_palette(["#006DDB", "#920000"])
        if cr_meta is not None:
            ylimit = cr_meta.df_ylimit

    if data.empty:
        LOG.error("CommitReport has no CF interactions")
        return

    data['Region'] = data['Region'].apply(lambda x: x[0:6])

    plt.figure(fig.number)
    plt.clf()
    if ylimit is not None:
        plt.ylim(0, ylimit)
    bar_p = sns.barplot(
        x="Region",
        y="Amount",
        hue="Direction",
        data=data,
        palette=color_palette
    )

    for label in bar_p.get_xticklabels():
        label.set_rotation(90)
        label.set_family("monospace")

    fig.add_subplot(bar_p)
    # fig.tight_layout()
