"""
Generate plots for the degree of blame interactions.
"""

import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.style as style
import pandas as pd
import numpy as np

from varats.jupyterhelper.file import load_blame_report
from varats.plots.plot import Plot
from varats.data.revisions import get_processed_revisions
from varats.data.reports.blame_report import (BlameReport,
                                              generate_degree_tuples)
from varats.plots.plot_utils import check_required_args


def _build_interaction_table(report_files: tp.List[Path],
                             project_name: str) -> pd.DataFrame:
    # TODO: maybe caching ?
    cached_df = None
    if cached_df is None:
        cached_df = pd.DataFrame(columns=[
            'revision', 'degree', 'amount', 'fraction'
        ])
        cached_df.degree = cached_df.degree.astype('int64')
        cached_df.amount = cached_df.amount.astype('int64')
        cached_df.fraction = cached_df.fraction.astype('int64')

    reports = []
    # TODO: refactor?
    total_missing_reports = len(report_files)
    for num, file_path in enumerate(report_files):
        print(
            "Loading missing file ({num}/{total}): ".format(
                num=(num + 1), total=total_missing_reports), file_path)
        try:
            reports.append(load_blame_report(file_path))
        except KeyError:
            print("KeyError: ", file_path)
        except StopIteration:
            print("YAML file was incomplete: ", file_path)

    def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
        # TODO: rename
        list_of_degree_accurences = generate_degree_tuples(report)

        degrees, amounts = map(list, zip(*list_of_degree_accurences))
        total = sum(amounts)
        return pd.DataFrame({
            'revision':
            [report.head_commit] * len(degrees),
            'degree':
            degrees,
            'amount':
            amounts,
            'fraction':
            np.divide(amounts, total),
        },
                            index=range(0, len(degrees)))

    new_data_frames = [
        create_data_frame_for_report(report) for report in reports
    ]

    new_df = pd.concat(
        [cached_df] + new_data_frames, ignore_index=True, sort=False)

    return new_df


@check_required_args(["result_folder", "project", 'get_cmap'])
def _gen_blame_interaction_data(**kwargs: tp.Any) -> pd.DataFrame:
    # TODO: add case-study filter
    commit_map = kwargs['get_cmap']()
    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    processed_revisions = get_processed_revisions(project_name, BlameReport)
    print(processed_revisions)

    # get proccessed files TODO: refactor out
    report_files = []
    for file_path in result_dir.iterdir():
        if BlameReport.is_correct_report_type(
                file_path.name) and BlameReport.result_file_has_status_success(
                    file_path.name):
            commit_hash = BlameReport.get_commit_hash_from_result_file(
                file_path.name)
            if commit_hash in processed_revisions:
                # TODO: case study checking
                report_files.append(file_path)

    data_frame = _build_interaction_table(report_files,
                                          str(project_name))

    data_frame['revision'] = data_frame['revision'].apply(
        lambda x: "{num}-{head}".format(head=x,
                                        num=commit_map.short_time_id(x)))

    return data_frame


class BlameInteractionDegree(Plot):
    """
    Plotting the degree of blame interactions.
    """

    def __init__(self, **kwargs: tp.Any):
        super(BlameInteractionDegree, self).__init__('b_interaction_degree')
        self.__saved_extra_args = kwargs

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 2 if view_mode else 1,
            'legend_size': 8 if view_mode else 4,
            'xtick_size': 10 if view_mode else 2
        }

        style.use(self.style)

        interaction_plot_df = _gen_blame_interaction_data(
            **self.__saved_extra_args)

        interaction_plot_df['cm_idx'] = interaction_plot_df['revision'].apply(
            lambda x: int(x.split('-')[0]))
        interaction_plot_df.sort_values(by=['cm_idx'], inplace=True)

        degree_levels = sorted(np.unique(interaction_plot_df['degree']))

        interaction_plot_df = interaction_plot_df.set_index(
            ['revision', 'degree'])
        interaction_plot_df = interaction_plot_df.reindex(
            pd.MultiIndex.from_product(interaction_plot_df.index.levels,
                                       names=interaction_plot_df.index.names),
            fill_value=0).reset_index()

        sub_df_list = [
            interaction_plot_df.loc[interaction_plot_df['degree'] == x]
            ['fraction'] for x in degree_levels
        ]

        # color_map = cm.get_cmap('plasma')
        # color_map = cm.get_cmap('hot')
        # color_map = cm.get_cmap('YlOrRd')
        color_map = cm.get_cmap('gist_stern')

        _, axis = plt.subplots()
        axis.stackplot(np.unique(interaction_plot_df['revision']),
                       sub_df_list,
                       edgecolor='black',
                       colors=reversed(
                           color_map(
                               np.linspace(
                                   0, 1,
                                   len(np.unique(
                                       interaction_plot_df['degree']))))),
                       labels=sorted(np.unique(interaction_plot_df['degree'])))

        axis.legend(title='Interaction degrees', loc='upper left')

        for x_label in axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def save(self, filetype: str = 'svg') -> None:
        # TODO: provide default implementation
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
        return set()
