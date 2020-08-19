"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
import pandas as pd
from matplotlib import cm

from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabase,
)
from varats.data.reports.commit_report import CommitMap
from varats.experiments.wllvm import BCFileExtensions
from varats.plots.cve_annotation import draw_cves
from varats.plots.plot import Plot, PlotDataEmpty
from varats.plots.plot_utils import check_required_args
from varats.plots.repository_churn import draw_code_churn
from varats.utils.project_util import get_project_cls_by_name

LOG = logging.getLogger(__name__)


def _filter_data_frame(
    opt_level: BCFileExtensions, verifier_plot_df: pd.DataFrame,
    commit_map: CommitMap
) -> tp.Tuple[tp.List[str], tp.List[pd.Series]]:
    pass


class BlameVerifierReportPlot(Plot):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def _get_verifier_data(self) -> pd.DataFrame:
        commit_map: CommitMap = self.plot_kwargs["get_cmap"]()
        project_name = self.plot_kwargs['project']
        verifier_plot_df = BlameVerifierReportDatabase.get_data_for_project(
            project_name,
            ["opt_level", "total", "successes", "failures", "undetermined"],
            commit_map
        )
        return verifier_plot_df

    def _verifier_plot(
        self,
        view_mode: bool,
        opt_level: BCFileExtensions,
        extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
            'lable_modif': lambda x: x,
            'legend_title': 'MISSING legend_title',
            'legend_visible': True,
            'fig_title': 'MISSING figure title',
            'edgecolor': 'black',
            'color_map': cm.get_cmap('gist_stern'),
        }
        if extra_plot_cfg is not None:
            plot_cfg.update(extra_plot_cfg)

        style.use(self.style)
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        verifier_plot_df = self._get_verifier_data()
        """
        unique_revisions, sub_df_list = _filter_data_frame(
            opt_level, verifier_plot_df, commit_map
        )
        """
        fig = plt.figure()
        main_axis = fig.add_subplot(111)

        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        fig.suptitle(
            str(plot_cfg['fig_title']) +
            f' - Project {self.plot_kwargs["project"]}',
            fontsize=8
        )

        legend = main_axis.legend(
            title=plot_cfg['legend_title'],
            loc='upper left',
            prop={
                'size': plot_cfg['legend_size'],
                'family': 'monospace'
            }
        )
        legend.set_visible(plot_cfg['legend_visible'])

        # annotate CVEs
        with_cve = self.plot_kwargs.get("with_cve", False)
        if with_cve:
            if "project" not in self.plot_kwargs:
                LOG.error("with_cve is true but no project is given.")
            else:
                project = get_project_cls_by_name(self.plot_kwargs["project"])
                draw_cves(main_axis, project, unique_revisions, plot_cfg)
        """
        t = np.arange(0.0, 2.0, 0.01)
        s1 = np.sin(2 * np.pi * t)
        s2 = np.sin(4 * np.pi * t)

        plt.figure(1)
        plt.subplot(211)
        plt.plot(t, s1)
        plt.subplot(212)
        plt.plot(t, 2 * s1)
        """

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        pass


class BlameVerifierReportNoOptPlot(BlameVerifierReportPlot):

    NAME = 'b_verifier_report_no_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        self._verifier_plot(view_mode=True, opt_level=BCFileExtensions.NO_OPT)


class BlameVerifierReportOptPlot(BlameVerifierReportPlot):

    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        self._verifier_plot(view_mode=True, opt_level=BCFileExtensions.OPT)
