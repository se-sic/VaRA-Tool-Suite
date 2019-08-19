"""
Generate commit interaction graphs.
"""

import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.style as style
from matplotlib import cm
import pandas as pd
import numpy as np

from varats.plots.plot import Plot
from varats.data.cache_helper import load_cached_df_or_none, cache_dataframe,\
    GraphCacheType
from varats.data.reports.commit_report import CommitMap, CommitReport, FilteredCommitReport
from varats.data.report import MetaReport
from varats.jupyterhelper.file import load_commit_report, load_filtered_commit_report
from varats.plots.plot_utils import check_required_args
from varats.data.revisions import get_proccessed_revisions
from varats.paper.case_study import CaseStudy, CSStage


def _build_interaction_table(report_files: tp.List[Path],
                             report_files_filtered: tp.List[Path],
                             commit_map: CommitMap,
                             project_name: str) -> pd.DataFrame:
    """
    Create a table with commit interaction data.

    Returns:
        A pandas data frame with following rows:
            - head_cm
            - CFInteractions
            - DFInteractions
            - HEAD CF Interactions
            - HEAD DF Interactions

    """
    def report_in_data_frame(report_file: Path, df_col: pd.Series) -> bool:
        commit_hash = CommitReport.get_commit_hash_from_result_file(
            Path(report_file).name)
        return tp.cast(bool, (commit_hash == df_col).any())

    new_reports = []
    total_reports = len(report_files)
    for num, file_path in enumerate(report_files):
        print(
            "Loading file ({num}/{total}): ".format(num=(num + 1),
                                                    total=total_reports),
            file_path)
        try:
            new_reports.append(load_commit_report(file_path))
        except KeyError:
            print("KeyError: ", file_path)
        except StopIteration:
            print("YAML file was incomplete: ", file_path)

    new_filtered_reports = []
    total_filtered_reports = len(report_files_filtered)
    for num, file_path in enumerate(report_files_filtered):
        print(
            "Loading file ({num}/{total}): ".format(
                num=(num + 1), total=total_filtered_reports), file_path)
        try:
            new_filtered_reports.append(load_filtered_commit_report(file_path))
        except KeyError:
            print("KeyError: ", file_path)
        except StopIteration:
            print("YAML file was incomplete: ", file_path)

    def sorter(report: tp.Any) -> int:
        return commit_map.short_time_id(report.head_commit)

    new_reports = sorted(new_reports, key=sorter)
    new_filtered_reports = sorted(new_filtered_reports, key=sorter)

    def create_data_frame_for_report(report: CommitReport,
                                     filtered_report: FilteredCommitReport
                                     ) -> pd.DataFrame:
        unfiltered_time = report.time_real()
        filtered_time = filtered_report.time_real()

        return pd.DataFrame(
            {
                'head_cm':
                report.head_commit,
                'Unfiltered Run Time':
                unfiltered_time,
                'Filtered Run Time':
                filtered_time,
                'Run Time Improv.': (unfiltered_time - filtered_time),
                'Rel. Run Time Improv.':
                ((unfiltered_time - filtered_time) / unfiltered_time)
                if unfiltered_time else 0
            },
            index=[0])

    data_frames = [
        create_data_frame_for_report(report, filtered_report)
        for report, filtered_report in zip(new_reports, new_filtered_reports)
    ]

    new_df = pd.concat(data_frames, ignore_index=True, sort=False)

    return new_df


@check_required_args(["result_folder", "project", "get_cmap"])
def _gen_interaction_graph(**kwargs: tp.Any) -> pd.DataFrame:
    """
    Generate a DataFrame, containing the amount of interactions between commits
    and interactions between the HEAD commit and all others.
    """
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None

    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    processed_revisions = get_proccessed_revisions(project_name, CommitReport)

    reports = []
    reports_filtered = []
    for file_path in result_dir.iterdir():
        if file_path.stem.startswith("CR-" + str(project_name) + "-"):
            if MetaReport.is_result_file_success(file_path.name):
                commit_hash = CommitReport.get_commit_hash_from_result_file(
                    file_path.name)

                if commit_hash in processed_revisions:
                    if case_study is None or case_study.has_revision(
                            commit_hash):
                        reports.append(file_path)
        if file_path.stem.startswith("FCR-" + str(project_name) + "-"):
            if MetaReport.is_result_file_success(file_path.name):
                commit_hash = FilteredCommitReport.get_commit_hash_from_result_file(
                    file_path.name)

                if commit_hash in processed_revisions:
                    if case_study is None or case_study.has_revision(
                            commit_hash):
                        reports_filtered.append(file_path)

    data_frame = _build_interaction_table(reports, reports_filtered,
                                          commit_map, str(project_name))

    data_frame['head_cm'] = data_frame['head_cm'].apply(
        lambda x: "{num}-{head}".format(head=x,
                                        num=commit_map.short_time_id(x)))

    return data_frame


def _plot_interaction_graph(data_frame: pd.DataFrame,
                            stages: tp.Optional[tp.List[CSStage]] = None,
                            view_mode: bool = True) -> None:
    """
    Plot a plot, showing the amount of interactions between commits and
    interactions between the HEAD commit and all others.
    """
    plot_cfg = {
        'linewidth': 2 if view_mode else 2,
        'legend_size': 8 if view_mode else 12,
        'xtick_size': 10 if view_mode else 2
    }

    if stages is None:
        stages = []

    data_frame.sort_values(by=['head_cm'], inplace=True)

    axis = plt.subplot()

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_fontsize(plot_cfg['xtick_size'])
        x_label.set_rotation(270)
        x_label.set_fontfamily('monospace')

    plt.plot('head_cm',
             'Unfiltered Run Time',
             data=data_frame,
             color='blue',
             linewidth=plot_cfg['linewidth'])
    plt.plot('head_cm',
             'Filtered Run Time',
             data=data_frame,
             color='red',
             linewidth=plot_cfg['linewidth'])

    plt.xlabel("Revisions", **{'size': '12'})
    plt.ylabel("Experiment Run Time (sec)", **{'size': '12'})
    plt.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})
    axis.set_ylim(bottom=0)


class InteractionPlotTimeComp(Plot):
    """
    Plot showing the total amount of commit interactions.
    """
    def __init__(self, **kwargs: tp.Any) -> None:
        super(InteractionPlotTimeComp,
              self).__init__("interaction_graph_time_comp")
        self.__saved_extra_args = kwargs

    @staticmethod
    def supports_stage_separation() -> bool:
        return True

    def plot(self, view_mode: bool) -> None:
        style.use(self.style)

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commit that are not in the case study, if one was
            selected. This allows us to only load file related to the
            case-study.
            """
            if self.__saved_extra_args['plot_case_study'] is None:
                return data_frame
            case_study: CaseStudy = self.__saved_extra_args['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['head_cm'].split('-')[1]),
                axis=1)]

        interaction_plot_time = _gen_interaction_graph(
            **self.__saved_extra_args)

        pd.set_option('display.max_rows', 500)
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.width', 1000)

        df_description = str(interaction_plot_time.describe())

        print()
        print(df_description)

        result_dir = Path(self.__saved_extra_args["result_folder"])
        project_name = self.__saved_extra_args["project"]

        description_file_path = result_dir / (
            project_name + "_{graph_name}.{filetype}".format(
                graph_name=self.name, filetype="txt"))

        with open(description_file_path, "w+") as f:
            f.write(df_description)

        if self.__saved_extra_args['sep_stages']:
            case_study = self.__saved_extra_args.get('plot_case_study', None)
        else:
            case_study = None

        _plot_interaction_graph(
            cs_filter(interaction_plot_time),
            case_study.stages if case_study is not None else None, view_mode)

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def save(self, filetype: str = 'svg') -> None:
        self.plot(False)

        result_dir = Path(self.__saved_extra_args["result_folder"])
        project_name = self.__saved_extra_args["project"]

        plt.savefig(
            result_dir /
            (project_name + "_{graph_name}{stages}.{filetype}".format(
                graph_name=self.name,
                stages='S' if self.__saved_extra_args['sep_stages'] else '',
                filetype=filetype)),
            dpi=1200,
            bbox_inches="tight",
            format=filetype)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
