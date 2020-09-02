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
from varats.plots.cve_annotation import draw_cves
from varats.plots.plot import Plot, PlotDataEmpty
from varats.plots.plot_utils import check_required_args
from varats.plots.repository_churn import draw_code_churn
from varats.utils.project_util import get_project_cls_by_name

LOG = logging.getLogger(__name__)


def _filter_data_frame(
    opt_level: OptLevel, verifier_plot_df: pd.DataFrame, commit_map: CommitMap
) -> tp.Tuple[tp.List[str], tp.List[pd.Series]]:
    """Reduce data frame to rows that match the optimization level."""

    verifier_plot_df = verifier_plot_df.loc[verifier_plot_df['opt_level'] ==
                                            opt_level.value]

    total_levels = sorted(np.unique(verifier_plot_df.total))
    verifier_plot_df = verifier_plot_df.set_index(['revision'])
    verifier_plot_df = verifier_plot_df.reindex(
        pd.MultiIndex.from_product(
            verifier_plot_df.index.names, names=verifier_plot_df.index.names
        ),
        fill_value=0
    ).reset_index()

    # fix missing time_ids introduced by the product index
    verifier_plot_df['time_id'] = verifier_plot_df['revision'].apply(
        commit_map.short_time_id
    )
    verifier_plot_df.sort_values(by=['time_id'], inplace=True)

    sub_df_list = [
        verifier_plot_df.loc[verifier_plot_df.total == x].successful
        for x in total_levels
    ]

    unique_revisions = verifier_plot_df.revision.unique()

    return unique_revisions, sub_df_list


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
        commit_map: CommitMap = self.plot_kwargs['get_cmap']()
        verifier_plot_df = self._get_verifier_data()

        unique_revisions, sub_df_list = _filter_data_frame(
            opt_level, verifier_plot_df, commit_map
        )

        fig = plt.figure()
        # grid_spec = fig.add_gridspec(3, 1)

        main_axis = fig.subplots()
        main_axis.get_xaxis().set_visible(False)
        # churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)
        # x_axis = churn_axis

        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        fig.suptitle(
            str(plot_cfg['fig_title']) +
            f' - Project {self.plot_kwargs["project"]}',
            fontsize=8
        )

        revisions = verifier_plot_df['revision']
        values = verifier_plot_df['successful']

        # main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(
        #    verifier_plot_df['total'][0]))

        main_axis.stackplot(
            unique_revisions,
            sub_df_list,
            edgecolor=plot_cfg['edgecolor'],
            colors=reversed(
                plot_cfg['color_map'](np.linspace(0, 1, len(sub_df_list)))
            ),
            # TODO (se-passau/VaRA#545): remove cast with plot config rework
            labels=map(
                tp.cast(tp.Callable[[str], str], plot_cfg['lable_modif']),
                sorted(np.unique(verifier_plot_df['total']))
            ),
            linewidth=plot_cfg['linewidth']
        )

        legend = main_axis.legend(
            title=plot_cfg['legend_title'],
            loc='upper left',
            prop={
                'size': plot_cfg['legend_size'],
                'family': 'monospace'
            }
        )
        plt.setp(
            legend.get_title(),
            fontsize=plot_cfg['legend_size'],
            family='monospace'
        )
        legend.set_visible(plot_cfg['legend_visible'])
        """
        # annotate CVEs
        with_cve = self.plot_kwargs.get("with_cve", False)
        if with_cve:
            if "project" not in self.plot_kwargs:
                LOG.error("with_cve is true but no project is given.")
            else:
                project = get_project_cls_by_name(self.plot_kwargs["project"])
                draw_cves(main_axis, project, unique_revisions, plot_cfg)

        plt.setp(x_axis.get_yticklabels(), fontsize=8, fontfamily='monospace')
        plt.setp(
            x_axis.get_xticklabels(),
            fontsize=plot_cfg['xtick_size'],
            fontfamily='monospace',
            rotation=270
        )
        """

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        pass


class BlameVerifierReportNoOptPlot(BlameVerifierReportPlot):
    NAME = 'b_verifier_report_no_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': True,
            'fig_title': 'Annotated project revisions without optimization',
            'edgecolor': None,
        }
        self._verifier_plot(
            view_mode=True,
            opt_level=OptLevel.NO_OPT,
            extra_plot_cfg=extra_plot_cfg
        )


class BlameVerifierReportOptPlot(BlameVerifierReportPlot):
    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'legend_visible': True,
            'fig_title': 'Annotated project revisions with optimization',
            'edgecolor': None,
        }
        self._verifier_plot(
            view_mode=True,
            opt_level=OptLevel.OPT,
            extra_plot_cfg=extra_plot_cfg
        )
