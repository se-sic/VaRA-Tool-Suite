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

    #cached_df = load_cached_df_or_none(GraphCacheType.CommitInteractionData,
    #                                   project_name)
    #cached_df_filtered = load_cached_df_or_none(
    #    GraphCacheType.FilteredCommitInteractionData, project_name)

    #if cached_df is None:
    #    cached_df = pd.DataFrame(columns=[
    #        'head_cm', 'CFInteractions', 'DFInteractions',
    #        'HEAD CF Interactions', 'HEAD DF Interactions'
    #    ])
    #    cached_df.CFInteractions = cached_df.CFInteractions.astype('int64')
    #    cached_df.DFInteractions = cached_df.DFInteractions.astype('int64')
    #    cached_df['HEAD CF Interactions'] = cached_df[
    #        'HEAD CF Interactions'].astype('int64')
    #    cached_df['HEAD DF Interactions'] = cached_df[
    #        'HEAD DF Interactions'].astype('int64')

    #if cached_df_filtered is None:
    #    cached_df_filtered = pd.DataFrame(columns=[
    #        'head_cm', 'CFInteractions', 'DFInteractions',
    #        'HEAD CF Interactions', 'HEAD DF Interactions'
    #    ])
    #    cached_df_filtered.CFInteractions = cached_df_filtered.CFInteractions.astype(
    #        'int64')
    #    cached_df_filtered.DFInteractions = cached_df_filtered.DFInteractions.astype(
    #        'int64')
    #    cached_df_filtered['HEAD CF Interactions'] = cached_df_filtered[
    #        'HEAD CF Interactions'].astype('int64')
    #    cached_df_filtered['HEAD DF Interactions'] = cached_df_filtered[
    #        'HEAD DF Interactions'].astype('int64')

    def report_in_data_frame(report_file: Path, df_col: pd.Series) -> bool:
        commit_hash = CommitReport.get_commit_hash_from_result_file(
            Path(report_file).name)
        return tp.cast(bool, (commit_hash == df_col).any())

    #missing_report_files = [
    #    report_file for report_file in report_files
    #    if not report_in_data_frame(report_file, cached_df['head_cm'])
    #]
    #missing_filtered_report_files = [
    #    report_file for report_file in report_files_filtered
    #    if not report_in_data_frame(report_file, cached_df['head_cm'])
    #]

    #missing_reports = []
    #total_missing_reports = len(missing_report_files)
    #for num, file_path in enumerate(missing_report_files):
    #    print(
    #        "Loading missing file ({num}/{total}): ".format(
    #            num=(num + 1), total=total_missing_reports), file_path)
    #    try:
    #        missing_reports.append(load_commit_report(file_path))
    #    except KeyError:
    #        print("KeyError: ", file_path)
    #    except StopIteration:
    #        print("YAML file was incomplete: ", file_path)

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
        cf_head_interactions_raw = report.number_of_head_cf_interactions()
        filtered_cf_head_interactions_raw = filtered_report.number_of_head_cf_interactions(
        )

        unfiltered_cf_interactions = report.number_of_cf_interactions()
        filtered_cf_interactions = filtered_report.number_of_cf_interactions()

        unfiltered_head_cf_interactions = cf_head_interactions_raw[
            0] + cf_head_interactions_raw[1]
        filtered_head_cf_interactions = filtered_cf_head_interactions_raw[
            0] + filtered_cf_head_interactions_raw[1]

        return pd.DataFrame(
            {
                'head_cm':
                report.head_commit,
                'CFInteractions':
                unfiltered_cf_interactions,
                'HEAD CF Interactions':
                unfiltered_head_cf_interactions,
                'Filtered CFInteractions':
                filtered_cf_interactions,
                'Filtered HEAD CF Interactions':
                filtered_head_cf_interactions,
                'Interaction Reduction':
                (unfiltered_cf_interactions - filtered_cf_interactions),
                'HEAD Interaction Reduction':
                (unfiltered_head_cf_interactions -
                 filtered_head_cf_interactions),
                'Rel. Interaction Reduction.':
                ((unfiltered_cf_interactions - filtered_cf_interactions) /
                 unfiltered_cf_interactions)
                if unfiltered_cf_interactions else 0,
                'Rel. HEAD Interaction Reduction.':
                ((unfiltered_head_cf_interactions -
                  filtered_head_cf_interactions) /
                 unfiltered_head_cf_interactions)
                if unfiltered_head_cf_interactions else 0
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
        'linewidth': 2 if view_mode else 1,
        'legend_size': 8 if view_mode else 10,
        'xtick_size': 10 if view_mode else 2
    }

    if stages is None:
        stages = []

    data_frame.sort_values(by=['head_cm'], inplace=True)

    # Interaction plot
    axis = plt.subplot(211)  # 211

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_visible(False)

    plt.plot('head_cm',
             'CFInteractions',
             data=data_frame,
             color='blue',
             linewidth=plot_cfg['linewidth'])
    plt.plot('head_cm',
             'Filtered CFInteractions',
             data=data_frame,
             color='red',
             linewidth=plot_cfg['linewidth'])

    # plt.ylabel("Interactions", **{'size': '10'})
    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})

    # Head interaction plot
    axis = plt.subplot(212)

    for y_label in axis.get_yticklabels():
        y_label.set_fontsize(8)
        y_label.set_fontfamily('monospace')

    for x_label in axis.get_xticklabels():
        x_label.set_fontsize(plot_cfg['xtick_size'])
        x_label.set_rotation(270)
        x_label.set_fontfamily('monospace')

    plt.plot('head_cm',
             'HEAD CF Interactions',
             data=data_frame,
             color='aqua',
             linewidth=plot_cfg['linewidth'])
    plt.plot('head_cm',
             'Filtered HEAD CF Interactions',
             data=data_frame,
             color='crimson',
             linewidth=plot_cfg['linewidth'])

    plt.xlabel("Revisions", **{'size': '10'})
    # plt.ylabel("HEAD Interactions", **{'size': '10'})
    axis.legend(prop={'size': plot_cfg['legend_size'], 'family': 'monospace'})


class InteractionPlotCfComp(Plot):
    """
    Plot showing the total amount of commit interactions.
    """
    def __init__(self, **kwargs: tp.Any) -> None:
        super(InteractionPlotCfComp,
              self).__init__("interaction_graph_cf_comp")
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

        interaction_plot_cf = _gen_interaction_graph(**self.__saved_extra_args)

        pd.set_option('display.max_rows', 500)
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.width', 1000)

        df_description = str(interaction_plot_cf.describe())

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
            cs_filter(interaction_plot_cf),
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
