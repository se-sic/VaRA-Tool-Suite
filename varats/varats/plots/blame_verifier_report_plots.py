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
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plots.case_study_overview import SUCCESS_COLOR, FAILED_COLOR

LOG = logging.getLogger(__name__)


def _get_named_df_for_case_study(
    case_study: CaseStudy
) -> tp.Dict[str, tp.Union[str, pd.DataFrame]]:
    project_name = case_study.project_name
    commit_map = get_commit_map(project_name)

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

    named_verifier_df = {
        "project_name": project_name,
        "dataframe": verifier_plot_df
    }

    return named_verifier_df


def _extract_data_from_named_dataframe(
    named_verifier_plot_df: tp.Dict[str, tp.Union[str, pd.DataFrame]],
    opt_level: OptLevel
) -> tp.Tuple[str, tp.Dict[str, tp.Any]]:
    current_project_name = str(named_verifier_plot_df["project_name"])
    current_verifier_plot_df = pd.DataFrame(named_verifier_plot_df["dataframe"])

    # Filter results for current optimization level
    current_verifier_plot_df = current_verifier_plot_df.loc[
        current_verifier_plot_df['opt_level'] == opt_level.value]

    # Raise exception if no data points were found after opt level filtering
    if current_verifier_plot_df.empty or len(
        np.unique(current_verifier_plot_df['revision'])
    ) == 1:
        # Need more than one data point
        raise PlotDataEmpty

    current_verifier_plot_df.sort_values(by=['time_id'], inplace=True)

    revisions = current_verifier_plot_df['revision']
    successes = current_verifier_plot_df['successful'].to_numpy()
    failures = current_verifier_plot_df['failed'].to_numpy()
    total = current_verifier_plot_df['total'].to_numpy()

    successes_in_percent = successes / total
    failures_in_percent = failures / total

    result_data = current_project_name, {
        "revisions": revisions,
        "successes_in_percent": successes_in_percent,
        "failures_in_percent": failures_in_percent
    }

    return result_data


def _load_all_named_dataframes(
    current_config: PC.PaperConfig
) -> tp.List[tp.Dict[str, tp.Union[str, pd.DataFrame]]]:
    all_case_studies = current_config.get_all_case_studies()
    all_named_dataframes: tp.List[tp.Dict[str, tp.Union[str,
                                                        pd.DataFrame]]] = []

    for case_study in sorted(all_case_studies, key=lambda cs: cs.project_name):
        all_named_dataframes.append(_get_named_df_for_case_study(case_study))

    return all_named_dataframes


def _verifier_plot(
    opt_level: OptLevel,
    extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None
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

    # The project name of the dataframes is stored to remember the
    # correct title of the subplots
    named_verifier_plot_df_list = _load_all_named_dataframes(current_config)

    final_plot_data: tp.List[tp.Tuple[str, tp.Dict[str, tp.Any]]] = []

    for named_dataframe in named_verifier_plot_df_list:
        final_plot_data.append(
            _extract_data_from_named_dataframe(named_dataframe, opt_level)
        )

    grid = gs.GridSpec(len(final_plot_data), 1)

    fig = plt.figure()

    for i, plot_data in enumerate(final_plot_data):
        main_axis = fig.add_subplot(grid[i])

        fig.subplots_adjust(top=0.95, hspace=1.1, right=0.95, left=0.07)
        main_axis.title.set_text(
            str(plot_cfg['fig_title']) + f' - Project {plot_data[0]}'
        )
        main_axis.set_xlabel('Revisions')
        main_axis.set_ylabel('Success/Failure rate in %')
        main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        main_axis.stackplot(
            plot_data[1]["revisions"],
            plot_data[1]["successes_in_percent"],
            plot_data[1]["failures_in_percent"],
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
        )
