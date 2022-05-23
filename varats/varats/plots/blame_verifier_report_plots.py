"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import numpy.typing as npt
import pandas as pd
from matplotlib import style
from sklearn import preprocessing

from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabase,
    OptLevel,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.plots.case_study_overview import SUCCESS_COLOR, FAILED_COLOR
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import FullCommitHash

LOG = logging.getLogger(__name__)


def _get_named_df_for_case_study(
    case_study: CaseStudy, opt_level: OptLevel, plot_kwargs: tp.Dict[str,
                                                                     tp.Any]
) -> tp.Optional[tp.Dict[str, tp.Union[str, pd.DataFrame]]]:
    project_name = case_study.project_name
    commit_map = get_commit_map(project_name)

    verifier_plot_df = BlameVerifierReportDatabase.get_data_for_project(
        project_name, [
            "revision", "time_id", "opt_level", "total", "successful", "failed",
            "undetermined"
        ], commit_map, case_study
    )

    # Filter results for current optimization level
    verifier_plot_df = verifier_plot_df.loc[verifier_plot_df['opt_level'] ==
                                            opt_level.value]
    if verifier_plot_df.empty or len(
        verifier_plot_df['revision'].unique()
    ) == 0:
        if len(plot_kwargs["case_study"]) > 1:
            return None

        # Need more than one data point
        LOG.warning(
            f"No data found for project {project_name} with optimization level "
            f"{opt_level.value}"
        )
        raise PlotDataEmpty

    named_verifier_df: tp.Dict[str, tp.Union[str, pd.DataFrame]] = {
        "project_name": project_name,
        "dataframe": verifier_plot_df
    }

    return named_verifier_df


def _extract_data_from_named_dataframe(
    named_verifier_plot_df: tp.Dict[str, tp.Union[str, pd.DataFrame]]
) -> tp.Tuple[tp.Union[str, pd.DataFrame], tp.Dict[str, tp.Any]]:
    current_verifier_plot_df = tp.cast(
        pd.DataFrame, named_verifier_plot_df['dataframe']
    )
    current_verifier_plot_df.sort_values(by=['time_id'], inplace=True)

    revision_strs = [rev.hash for rev in current_verifier_plot_df['revision']]
    successes = current_verifier_plot_df['successful'].to_numpy()
    failures = current_verifier_plot_df['failed'].to_numpy()
    total = current_verifier_plot_df['total'].to_numpy()

    success_ratio = successes / total
    failure_ratio = failures / total
    average_success_ratio = round((success_ratio.sum() / success_ratio.size) *
                                  100, 2)
    average_failure_ratio = round((failure_ratio.sum() / failure_ratio.size) *
                                  100, 2)

    result_data = named_verifier_plot_df['project_name'], {
        "revisions": revision_strs,
        "success_ratio": success_ratio,
        "failure_ratio": failure_ratio,
        "average_success_ratio": average_success_ratio,
        "average_failure_ratio": average_failure_ratio
    }

    return result_data


def _load_all_named_dataframes(
    opt_level: OptLevel, plot_kwargs: tp.Dict[str, tp.Any]
) -> tp.List[tp.Dict[str, tp.Union[str, pd.DataFrame]]]:
    all_named_dataframes: tp.List[tp.Dict[str, tp.Union[str,
                                                        pd.DataFrame]]] = []

    # https://github.com/python/mypy/issues/9590
    k = lambda cs: cs.project_name
    for case_study in sorted(plot_kwargs["case_study"], key=k):
        named_df = _get_named_df_for_case_study(
            case_study, opt_level, plot_kwargs
        )

        if named_df:
            all_named_dataframes.append(named_df)

    return all_named_dataframes


def _build_default_suptitle_str(
    plot_kwargs: tp.Dict[str, tp.Any], opt_level: OptLevel
) -> str:
    opt_str: str = "with" if opt_level == OptLevel.OPT else "without"
    suptitle: str = f'Annotated project revisions {opt_str} ' \
                    f'optimization - '
    num_cs: int = len(plot_kwargs['case_study'])
    project_names_str: str = ""
    delimiter: str = " | "

    for i in range(num_cs):
        project_names_str += plot_kwargs['case_study'][i].project_name
        project_names_str += delimiter

    project_names_str = project_names_str[:-len(delimiter)]
    project_quantity_str = "Projects" if num_cs > 1 else "Project"
    suptitle += f"{project_quantity_str} {project_names_str}"

    return suptitle


def _verifier_plot(
    opt_level: OptLevel, plot_config: PlotConfig, plot_kwargs: tp.Dict[str,
                                                                       tp.Any]
) -> None:
    # The project name of the dataframes is stored to remember the
    # correct title of the subplots
    named_verifier_plot_df_list = _load_all_named_dataframes(
        opt_level, plot_kwargs
    )

    final_plot_data: tp.List[tp.Tuple[str, tp.Dict[str, tp.Any]]] = []

    for named_dataframe in named_verifier_plot_df_list:
        final_plot_data.append(
            _extract_data_from_named_dataframe(named_dataframe)
        )

    if not final_plot_data:
        raise PlotDataEmpty

    default_fig_suptitle: str = _build_default_suptitle_str(
        plot_kwargs, opt_level
    )

    if len(plot_kwargs["case_study"]) > 1 and len(final_plot_data) > 1:
        _verifier_plot_multiple(
            default_fig_suptitle, plot_config, final_plot_data
        )
    else:
        # Pass the only list item of the plot data
        _verifier_plot_single(
            default_fig_suptitle, plot_config, final_plot_data[0]
        )


def _verifier_plot_single(
    default_fig_suptitle: str, plot_config: PlotConfig,
    final_plot_data: tp.Tuple[str, tp.Dict[str, tp.Any]]
) -> None:
    fig, main_axis = plt.subplots()
    fig.suptitle(default_fig_suptitle, fontsize=plot_config.font_size(8))
    main_axis.grid(linestyle='--')
    main_axis.set_xlabel('Revisions')
    main_axis.set_ylabel('Success/Failure rate in %')
    main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)

    main_axis.stackplot(
        final_plot_data[1]["revisions"],
        final_plot_data[1]["success_ratio"],
        final_plot_data[1]["failure_ratio"],
        labels=[
            f"successes(\u2205 {final_plot_data[1]['average_success_ratio']}%)",
            f"failures(\u2205 {final_plot_data[1]['average_failure_ratio']}%)"
        ],
        colors=[SUCCESS_COLOR, FAILED_COLOR],
        alpha=0.5
    )

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
    )

    legend = main_axis.legend(
        title=plot_config.legend_title("Annotation types:"),
        loc='upper left',
        prop={
            'size': plot_config.legend_size(),
            'family': 'monospace'
        }
    )
    legend.set_visible(plot_config.show_legend)

    plt.setp(
        legend.get_title(),
        fontsize=plot_config.legend_size(),
        family='monospace'
    )


def _verifier_plot_multiple(
    default_fig_suptitle: str, plot_config: PlotConfig,
    final_plot_data: tp.List[tp.Tuple[str, tp.Dict[str, tp.Any]]]
) -> None:
    fig = plt.figure()
    main_axis = fig.subplots()
    main_axis.set_xlim(0, 1)
    main_axis.grid(linestyle='--')
    main_axis.set_xlabel('Revisions normalized')
    main_axis.set_ylabel('Success rate in %')
    main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
    mean_over_all_project_successes = 0

    for plot_data in final_plot_data:
        mean_over_all_project_successes += plot_data[1]["average_success_ratio"
                                                       ] / len(final_plot_data)

        # Save an unique int for each varying revision to prepare the data
        # for the normalization on the x-axis
        revisions_as_numbers: npt.NDArray[np.int_] = np.array([
            x + 1 for x, y in enumerate(plot_data[1]["revisions"])
        ]).reshape(-1, 1)

        normalized_revisions = preprocessing.minmax_scale(
            revisions_as_numbers, (0, 1), axis=0, copy=False
        )
        main_axis.plot(
            normalized_revisions,
            plot_data[1]["success_ratio"],
            label=
            f"{plot_data[0]}(\u2205 {plot_data[1]['average_success_ratio']}%)"
        )

    main_axis.title.set_text(f"{plot_config.fig_title(default_fig_suptitle)}")

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
    )

    legend = main_axis.legend(
        title=f"{plot_config.legend_title('Success rate of projects')}"
        f"(\u2205 {round(mean_over_all_project_successes, 2)}%):",
        loc='upper left',
        prop={
            'size': plot_config.legend_size(),
            'family': 'monospace'
        }
    )
    legend.set_visible(plot_config.show_legend())

    plt.setp(
        legend.get_title(),
        fontsize=plot_config.legend_size(),
        family='monospace'
    )


class BlameVerifierReportPlot(Plot, plot_name=None):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        style.use(self.plot_config.style())

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot_file_name(self, filetype: str) -> str:
        return f"{self.name}.{filetype}"


class BlameVerifierReportNoOptPlot(
    BlameVerifierReportPlot, plot_name="b_verifier_report_no_opt_plot"
):
    """Plotting the successful and failed annotations of reports without
    optimization."""
    NAME = 'b_verifier_report_no_opt_plot'

    def plot(self, view_mode: bool) -> None:
        _verifier_plot(OptLevel.NO_OPT, self.plot_config, self.plot_kwargs)


class BlameVerifierReportNoOptPlotGenerator(
    PlotGenerator,
    generator_name="verifier-no-opt-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a verifier-no-opt plot for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        return [
            BlameVerifierReportNoOptPlot(self.plot_config, **self.plot_kwargs)
        ]


class BlameVerifierReportOptPlot(
    BlameVerifierReportPlot, plot_name="b_verifier_report_opt_plot"
):
    """Plotting the successful and failed annotations of reports with
    optimization."""
    NAME = 'b_verifier_report_opt_plot'

    def plot(self, view_mode: bool) -> None:
        _verifier_plot(OptLevel.OPT, self.plot_config, self.plot_kwargs)


class BlameVerifierReportOptPlotGenerator(
    PlotGenerator,
    generator_name="verifier-opt-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a verifier-opt plot for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        return [
            BlameVerifierReportOptPlot(self.plot_config, **self.plot_kwargs)
        ]
