"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib import cm

from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabase,
    OptLevel,
)
from varats.data.reports.commit_report import CommitMap
from varats.plot.plot import Plot, PlotDataEmpty
from varats.varats.plots.case_study_overview import SUCCESS_COLOR, FAILED_COLOR

LOG = logging.getLogger(__name__)


class BlameVerifierReportPlot(Plot):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""

    def _get_verifier_data(self) -> pd.DataFrame:
        commit_map: CommitMap = self.plot_kwargs["get_cmap"]()
        case_study = self.plot_kwargs.get('plot_case_study', None)
        project_name = self.plot_kwargs['project']
        verifier_plot_df = BlameVerifierReportDatabase.get_data_for_project(
            project_name, [
                "revision", "time_id", "opt_level", "total", "successful",
                "failed", "undetermined"
            ], commit_map, case_study
        )

        if verifier_plot_df.empty or len(
            np.unique(verifier_plot_df['revision'])
        ) == 1:
            # Need more than one data point
            raise PlotDataEmpty

        return verifier_plot_df

    def _verifier_plot(
        self,
        view_mode: bool,
        opt_level: OptLevel,
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
        verifier_plot_df = self._get_verifier_data()

        # Filter results for current optimization level
        verifier_plot_df = verifier_plot_df.loc[verifier_plot_df['opt_level'] ==
                                                opt_level.value]

        # Raise exception if no data points were found after opt level filtering
        if verifier_plot_df.empty or len(
            np.unique(verifier_plot_df['revision'])
        ) == 1:
            # Need more than one data point
            raise PlotDataEmpty

        verifier_plot_df.sort_values(by=['time_id'], inplace=True)

        revisions = verifier_plot_df['revision']
        successes = verifier_plot_df['successful'].to_numpy()
        failures = verifier_plot_df['failed'].to_numpy()
        total = verifier_plot_df['total'].to_numpy()

        successes_in_percent = successes / total
        failures_in_percent = failures / total

        fig, main_axis = plt.subplots()

        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        fig.suptitle(
            str(plot_cfg['fig_title']) +
            f' - Project {self.plot_kwargs["project"]}',
            fontsize=8
        )
        main_axis.set_xlabel('Revisions')
        main_axis.set_ylabel('Success/Failure rate in %')
        main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        main_axis.stackplot(
            revisions,
            successes_in_percent,
            failures_in_percent,
            labels=['successes', 'failures'],
            colors=[SUCCESS_COLOR, FAILED_COLOR],
            alpha=0.5
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

        plt.setp(
            legend.get_title(),
            fontsize=plot_cfg['legend_size'],
            family='monospace'
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        pass


class BlameVerifierReportNoOptPlot(BlameVerifierReportPlot):
    """Plotting the successful and failed annotations of reports without
    optimization."""
    NAME = 'b_verifier_report_no_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': True,
            'fig_title': 'Annotated project revisions without optimization',
            'legend_title': 'Annotation types'
        }
        self._verifier_plot(
            view_mode=True,
            opt_level=OptLevel.NO_OPT,
            extra_plot_cfg=extra_plot_cfg
        )


class BlameVerifierReportOptPlot(BlameVerifierReportPlot):
    """Plotting the successful and failed annotations of reports with
    optimization."""
    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': True,
            'fig_title': 'Annotated project revisions with optimization',
            'legend_title': 'Annotation types'
        }
        self._verifier_plot(
            view_mode=True,
            opt_level=OptLevel.OPT,
            extra_plot_cfg=extra_plot_cfg
        )
