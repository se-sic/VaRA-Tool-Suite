"""Generate plots for the annotations of the blame verifier."""
import abc
import logging
import typing as tp
from pathlib import Path

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
        if _is_multi_cs_plot():
            raise RuntimeWarning(
                f"Project {project_name} did not provide any plot data"
            )

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

    revisions = current_verifier_plot_df['revision'].to_numpy()
    successes = current_verifier_plot_df['successful'].to_numpy()
    failures = current_verifier_plot_df['failed'].to_numpy()
    total = current_verifier_plot_df['total'].to_numpy()

    success_ratio = successes / total
    failure_ratio = failures / total

    result_data = current_project_name, {
        "revisions": revisions,
        "success_ratio": success_ratio,
        "failure_ratio": failure_ratio
    }

    return result_data


def _load_all_named_dataframes(
    current_config: PC.PaperConfig
) -> tp.List[tp.Dict[str, tp.Union[str, pd.DataFrame]]]:
    all_case_studies = current_config.get_all_case_studies()
    all_named_dataframes: tp.List[tp.Dict[str, tp.Union[str,
                                                        pd.DataFrame]]] = []

    for case_study in sorted(all_case_studies, key=lambda cs: cs.project_name):
        try:
            all_named_dataframes.append(
                _get_named_df_for_case_study(case_study)
            )
        except RuntimeWarning:
            continue

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

    if _is_multi_cs_plot():
        _verifier_plot_multiple(plot_cfg, final_plot_data)
    else:
        # Pass the only list item of the plot data
        _verifier_plot_single(plot_cfg, final_plot_data[0])


def _is_multi_cs_plot() -> bool:
    if len(PC.get_paper_config().get_all_case_studies()) > 1:
        return True

    return False


def _verifier_plot_single(
    plot_cfg: tp.Dict[str, tp.Any], plot_data: tp.Tuple[str, tp.Dict[str,
                                                                     tp.Any]]
) -> None:
    fig, main_axis = plt.subplots()

    fig.suptitle(
        str(plot_cfg['fig_title']) + f' - Project {plot_data[0]}', fontsize=8
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
        labels=['successes', 'failures'],
        colors=[SUCCESS_COLOR, FAILED_COLOR],
        alpha=0.5
    )

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
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


def _verifier_plot_multiple(
    plot_cfg: tp.Dict[str, tp.Any],
    final_plot_data: tp.List[tp.Tuple[str, tp.Dict[str, tp.Any]]]
) -> None:
    fig = plt.figure()
    main_axis = fig.subplots()
    project_names: str = "| "
    main_axis.grid(linestyle='--')
    main_axis.set_xlabel('Revisions normalized')
    main_axis.set_ylabel('Success rate in %')
    main_axis.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)

    for plot_data in final_plot_data:
        project_names += plot_data[0] + " | "
        revisions_as_number = np.array([
            x + 1 for x, y in enumerate(plot_data[1]["revisions"])
        ]).reshape(-1, 1)

        normalized_revisions = preprocessing.normalize(
            revisions_as_number, axis=0
        )
        main_axis.plot(
            normalized_revisions,
            plot_data[1]["success_ratio"],
            label=plot_data[0]
        )
    main_axis.title.set_text(
        str(plot_cfg['fig_title']) + f' - Project(s): \n{project_names}'
    )

    plt.setp(
        main_axis.get_xticklabels(), rotation=30, horizontalalignment='right'
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
        legend_title: str

        if _is_multi_cs_plot():
            legend_title = "Success rate of projects:"
        else:
            legend_title = "Annotation types:"

        extra_plot_cfg = {
            'fig_title': 'Annotated project revisions with optimization',
            'legend_title': legend_title
        }
        _verifier_plot(
            opt_level=OptLevel.NO_OPT,
            extra_plot_cfg=extra_plot_cfg,
        )

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'svg'
    ) -> None:
        """
        Save the current plot to a file.

        Args:
            path: The path where the file is stored (excluding the file name).
            filetype: The file type of the plot.
        """
        self.plot(False)

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        # TODO (se-passau/VaRA#545): refactor dpi into plot_config. see.
        plt.savefig(
            plot_dir / f"{self.name}.{filetype}",
            dpi=1200,
            format=filetype,
            bbox_inches='tight'
        )
        plt.close()


class BlameVerifierReportOptPlot(BlameVerifierReportPlot):
    """Plotting the successful and failed annotations of reports with
    optimization."""
    NAME = 'b_verifier_report_opt_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        legend_title: str

        if _is_multi_cs_plot():
            legend_title = "Success rate of projects:"
        else:
            legend_title = "Annotation types:"

        extra_plot_cfg = {
            'fig_title': 'Annotated project revisions with optimization',
            'legend_title': legend_title
        }
        _verifier_plot(
            opt_level=OptLevel.OPT,
            extra_plot_cfg=extra_plot_cfg,
        )

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'svg'
    ) -> None:
        """
        Save the current plot to a file.

        Args:
            path: The path where the file is stored (excluding the file name).
            filetype: The file type of the plot.
        """
        self.plot(False)

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        # TODO (se-passau/VaRA#545): refactor dpi into plot_config. see.
        plt.savefig(
            plot_dir / f"{self.name}.{filetype}",
            dpi=1200,
            format=filetype,
            bbox_inches='tight'
        )
        plt.close()
