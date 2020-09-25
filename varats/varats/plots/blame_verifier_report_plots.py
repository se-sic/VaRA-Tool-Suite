"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib import gridspec as gs

import varats.paper_mgmt.paper_config as PC
from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabase,
    OptLevel,
)
from varats.data.databases.file_status_database import FileStatusDatabase
from varats.data.reports.empty_report import EmptyReport
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_revisions_status_for_case_study
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import check_required_args, find_missing_revisions
from varats.plots.case_study_overview import SUCCESS_COLOR, FAILED_COLOR
from varats.project.project_util import get_local_project_git
from varats.report.report import FileStatusExtension, MetaReport

LOG = logging.getLogger(__name__)


@check_required_args(["get_cmap", "project"])
def _get_df_for_case_study(
    case_study: CaseStudy, **kwargs: tp.Any
) -> pd.DataFrame:
    commit_map: CommitMap = kwargs["get_cmap"]

    project_name = kwargs["project"]
    verifier_plot_df = BlameVerifierReportDatabase.get_data_for_project(
        project_name, [
            "revision", "time_id", "opt_level", "total", "successful", "failed",
            "undetermined"
        ], commit_map, case_study
    )

    if verifier_plot_df.empty or len(
        np.unique(verifier_plot_df['revision'])
    ) == 1:
        # Need more than one data point
        raise PlotDataEmpty

    return verifier_plot_df


def _load_dataframes_of_projects(
    current_config: PC.PaperConfig, **kwargs: tp.Any
) -> tp.List[pd.DataFrame]:
    all_dataframes: tp.List[pd.DataFrame] = []
    all_case_studies = current_config.get_all_case_studies()

    for case_study in all_case_studies:
        current_df = _get_df_for_case_study(case_study, **kwargs)
        all_dataframes.append(current_df)

    return all_dataframes


def _extract_data_from_dataframes(
    verifier_plot_df: pd.DataFrame, opt_level: OptLevel
) -> tp.Dict[str, tp.Any]:

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

    result_data: tp.Dict[str, tp.Any] = {
        "revisions": revisions,
        "successes_in_percent": successes_in_percent,
        "failures_in_percent": failures_in_percent
    }

    return result_data


def _verifier_plot(
    opt_level: OptLevel,
    extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None,
    **kwargs
) -> None:

    current_config = PC.get_paper_config()

    plot_cfg = {
        'legend_size': 8,
        'legend_visible': True,
        'legend_title': 'MISSING legend_title',
        'fig_title': 'MISSING figure title',
    }
    if extra_plot_cfg is not None:
        plot_cfg.update(extra_plot_cfg)

    verifier_plot_df_list = _load_dataframes_of_projects(
        current_config, **kwargs
    )

    final_plot_data: tp.List[tp.Dict[str, tp.Any]] = []

    for dataframe in verifier_plot_df_list:
        final_plot_data.append(
            _extract_data_from_dataframes(dataframe, opt_level)
        )

    grid = gs.GridSpec(len(final_plot_data), 1)

    fig = plt.figure()

    for i, plot_data in enumerate(final_plot_data):
        main_axis = fig.add_subplot(grid[i])

        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        fig.suptitle(
            str(plot_cfg['fig_title']) + f' - Project {kwargs["project"]}',
            fontsize=8
        )
        main_axis.set_xlabel('Revisions')
        main_axis.set_ylabel('Success/Failure rate in %')
        main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        main_axis.stackplot(
            plot_data["revisions"],
            plot_data["successes_in_percent"],
            plot_data["failures_in_percent"],
            labels=['successes', 'failures'],
            colors=[SUCCESS_COLOR, FAILED_COLOR],
            alpha=0.5
        )

        plt.setp(
            main_axis.get_xticklabels(),
            rotation=30,
            horizontalalignment='right'
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


class BlameVerifierReportPlot(Plot):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        style.use(self.style)

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
            'fig_title': 'Annotated project revisions without optimization',
            'legend_title': 'Annotation types'
        }
        _verifier_plot(
            opt_level=OptLevel.NO_OPT,
            extra_plot_cfg=extra_plot_cfg,
            **self.plot_kwargs
        )


class BlameVerifierReportOptPlot(BlameVerifierReportPlot):
    """Plotting the successful and failed annotations of reports with
    optimization."""
    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        extra_plot_cfg = {
            'fig_title': 'Annotated project revisions with optimization',
            'legend_title': 'Annotation types'
        }
        _verifier_plot(
            opt_level=OptLevel.OPT,
            extra_plot_cfg=extra_plot_cfg,
            **self.plot_kwargs
        )
