"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp

import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from sklearn import preprocessing

import varats.paper_mgmt.paper_config as PC
from varats.data.databases.blame_verifier_report_database import (
    BlameVerifierReportDatabase,
    OptLevel,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import check_required_args
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.plots.blame_interaction_degree import (
    OPTIONAL_FIG_TITLE,
    OPTIONAL_LEGEND_TITLE,
    OPTIONAL_LEGEND_SIZE,
    OPTIONAL_SHOW_LEGEND,
)
from varats.plots.case_study_overview import SUCCESS_COLOR, FAILED_COLOR

LOG = logging.getLogger(__name__)


def _get_named_df_for_case_study(
    case_study: CaseStudy, opt_level: OptLevel, plot_kwargs: tp.Any
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
        np.unique(verifier_plot_df['revision'])
    ) == 1:
        if len(plot_kwargs["case_study"]) > 1:
            return None

        # Need more than one data point
        LOG.warning(
            f"No data found for project {project_name} with optimization level "
            f"{opt_level.value}"
        )
        raise PlotDataEmpty

    named_verifier_df = {
        "project_name": project_name,
        "dataframe": verifier_plot_df
    }

    return named_verifier_df


def _extract_data_from_named_dataframe(
    named_verifier_plot_df: tp.Dict[str, tp.Union[str, pd.DataFrame]]
) -> tp.Tuple[str, tp.Dict[str, tp.Any]]:

    current_verifier_plot_df = tp.cast(
        pd.DataFrame, named_verifier_plot_df['dataframe']
    )
    current_verifier_plot_df.sort_values(by=['time_id'], inplace=True)

    revisions = current_verifier_plot_df['revision'].to_numpy()
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
        "revisions": revisions,
        "success_ratio": success_ratio,
        "failure_ratio": failure_ratio,
        "average_success_ratio": average_success_ratio,
        "average_failure_ratio": average_failure_ratio
    }

    return result_data


def _load_all_named_dataframes(
    opt_level: OptLevel, plot_kwargs: tp.Any
) -> tp.List[tp.Dict[str, tp.Union[str, pd.DataFrame]]]:
    all_named_dataframes: tp.List[tp.Dict[str, tp.Union[str,
                                                        pd.DataFrame]]] = []

    for case_study in sorted(
        plot_kwargs["case_study"], key=lambda cs: cs.project_name
    ):
        named_df = _get_named_df_for_case_study(
            case_study, opt_level, plot_kwargs
        )

        if named_df:
            all_named_dataframes.append(named_df)

    return all_named_dataframes


def _verifier_plot(opt_level: OptLevel, plot_kwargs: tp.Any) -> None:

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

    if len(plot_kwargs["case_study"]) > 1 and len(final_plot_data) > 1:
        _verifier_plot_multiple(plot_kwargs, final_plot_data)
    else:
        # Pass the only list item of the plot data
        _verifier_plot_single(plot_kwargs, final_plot_data[0])


def _verifier_plot_single(
    plot_kwargs: tp.Any, plot_data: tp.Tuple[str, tp.Dict[str, tp.Any]]
) -> None:
    fig, main_axis = plt.subplots()

    fig.suptitle(
        str(plot_kwargs['fig_title']) + f' - Project {plot_data[0]}',
        fontsize=8
    )
    main_axis.grid(linestyle='--')
    main_axis.set_xlabel('Revisions')
    main_axis.set_ylabel('Success/Failure rate in %')
    main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)

    main_axis.stackplot(
        plot_data[1]["revisions"],
        plot_data[1]["success_ratio"],
        plot_data[1]["failure_ratio"],
        labels=[
            f"successes(\u2205 {plot_data[1]['average_success_ratio']}%)",
            f"failures(\u2205 {plot_data[1]['average_failure_ratio']}%)"
        ],
        colors=[SUCCESS_COLOR, FAILED_COLOR],
        alpha=0.5
    )

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
    )

    legend = main_axis.legend(
        title=plot_kwargs['legend_title'],
        loc='upper left',
        prop={
            'size': plot_kwargs['legend_size'],
            'family': 'monospace'
        }
    )
    legend.set_visible(plot_kwargs['show_legend'])

    plt.setp(
        legend.get_title(),
        fontsize=plot_kwargs['legend_size'],
        family='monospace'
    )


def _verifier_plot_multiple(
    plot_kwargs: tp.Any,
    final_plot_data: tp.List[tp.Tuple[str, tp.Dict[str, tp.Any]]]
) -> None:
    fig = plt.figure()
    main_axis = fig.subplots()
    main_axis.set_xlim(0, 1)
    project_names: str = "| "
    main_axis.grid(linestyle='--')
    main_axis.set_xlabel('Revisions normalized')
    main_axis.set_ylabel('Success rate in %')
    main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
    mean_over_all_project_successes = 0

    for plot_data in final_plot_data:
        project_names += plot_data[0] + " | "
        mean_over_all_project_successes += plot_data[1]["average_success_ratio"
                                                       ] / len(final_plot_data)

        # Save an unique int for each varying revision to prepare the data
        # for the normalization on the x-axis
        revisions_as_numbers = np.array([
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

    main_axis.title.set_text(
        str(plot_kwargs['fig_title']) + f' - Project(s): \n{project_names}'
    )

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
    )

    legend = main_axis.legend(
        title=f"{plot_kwargs['legend_title']}"
        f"(\u2205 {round(mean_over_all_project_successes, 2)}%):",
        loc='upper left',
        prop={
            'size': plot_kwargs['legend_size'],
            'family': 'monospace'
        }
    )
    legend.set_visible(plot_kwargs['show_legend'])

    plt.setp(
        legend.get_title(),
        fontsize=plot_kwargs['legend_size'],
        family='monospace'
    )


class BlameVerifierReportPlot(Plot, plot_name=None):
    """Base plot for blame verifier plots."""

    @abc.abstractmethod
    def plot(self, view_mode: bool) -> None:
        """Plot the current plot to a file."""
        style.use(self.style)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        pass

    def plot_file_name(self, filetype: str) -> str:
        return f"{self.name}.{filetype}"


class BlameVerifierReportNoOptPlot(
    BlameVerifierReportPlot, plot_name="b_verifier_report_no_opt_plot"
):
    """Plotting the successful and failed annotations of reports without
    optimization."""
    NAME = 'b_verifier_report_no_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:

        if len(self.plot_kwargs["case_study"]) > 1:
            self.plot_kwargs["legend_title"] = "Success rate of projects"
        else:
            self.plot_kwargs["legend_title"] = "Annotation types:"

        if not self.plot_kwargs["fig_title"]:
            self.plot_kwargs[
                "fig_title"
            ] = "Annotated project revisions without optimization"

        _verifier_plot(OptLevel.NO_OPT, self.plot_kwargs)


class BlameVerifierReportNoOptPlotGenerator(
    PlotGenerator,
    generator_name="verifier-no-opt-plot",
    plot=BlameVerifierReportNoOptPlot,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE,
        PlotGenerator.REQUIRE_MULTI_CASE_STUDY,
        OPTIONAL_FIG_TITLE,
        OPTIONAL_LEGEND_TITLE,
        OPTIONAL_LEGEND_SIZE,
        OPTIONAL_SHOW_LEGEND,
    ]
):
    """Generates a verifier-no-opt plot for the selected case study(ies)."""

    @check_required_args("report_type", "case_study")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_studies: tp.List[CaseStudy] = plot_kwargs["case_study"]
        self.__fig_title: str = plot_kwargs["fig_title"]
        self.__legend_title: str = plot_kwargs["legend_title"]
        self.__legend_size: int = plot_kwargs["legend_size"]
        self.__show_legend: bool = plot_kwargs["show_legend"]

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=self.__case_studies,
                fig_title=self.__fig_title,
                legend_title=self.__legend_title,
                legend_size=self.__legend_size,
                show_legend=self.__show_legend,
            )
        ]


class BlameVerifierReportOptPlot(
    BlameVerifierReportPlot, plot_name="b_verifier_report_opt_plot"
):
    """Plotting the successful and failed annotations of reports with
    optimization."""
    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:

        if len(self.plot_kwargs["case_study"]) > 1:
            self.plot_kwargs["legend_title"] = "Success rate of projects"
        else:
            self.plot_kwargs["legend_title"] = "Annotation types:"

        if not self.plot_kwargs["fig_title"]:
            self.plot_kwargs["fig_title"
                            ] = "Annotated project revisions with optimization"

        _verifier_plot(OptLevel.OPT, self.plot_kwargs)


class BlameVerifierReportOptPlotGenerator(
    PlotGenerator,
    generator_name="verifier-opt-plot",
    plot=BlameVerifierReportOptPlot,
    options=[
        PlotGenerator.REQUIRE_REPORT_TYPE,
        PlotGenerator.REQUIRE_MULTI_CASE_STUDY,
        OPTIONAL_FIG_TITLE,
        OPTIONAL_LEGEND_TITLE,
        OPTIONAL_LEGEND_SIZE,
        OPTIONAL_SHOW_LEGEND,
    ]
):
    """Generates a verifier-opt plot for the selected case study(ies)."""

    @check_required_args("report_type", "case_study")
    def __init__(self, plot_config: PlotConfig, **plot_kwargs: tp.Any):
        super().__init__(plot_config, **plot_kwargs)
        self.__report_type: str = plot_kwargs["report_type"]
        self.__case_studies: tp.List[CaseStudy] = plot_kwargs["case_study"]
        self.__fig_title: str = plot_kwargs["fig_title"]
        self.__legend_title: str = plot_kwargs["legend_title"]
        self.__legend_size: int = plot_kwargs["legend_size"]
        self.__show_legend: bool = plot_kwargs["show_legend"]

    def generate(self) -> tp.List[Plot]:
        return [
            self.PLOT(
                report_type=self.__report_type,
                case_study=self.__case_studies,
                fig_title=self.__fig_title,
                legend_title=self.__legend_title,
                legend_size=self.__legend_size,
                show_legend=self.__show_legend,
            )
        ]
