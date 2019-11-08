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

from varats.data.cache_helper import build_cached_report_table, GraphCacheType
from varats.jupyterhelper.file import load_blame_report
from varats.plots.plot import Plot
from varats.data.revisions import get_processed_revisions_files
from varats.data.reports.blame_report import (BlameReport,
                                              generate_degree_tuples)
from varats.plots.plot_utils import check_required_args
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter


def _build_interaction_table(report_files: tp.List[Path],
                             project_name: str) -> pd.DataFrame:
    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(
            columns=['revision', 'degree', 'amount', 'fraction'])
        df_layout.degree = df_layout.degree.astype('int64')
        df_layout.amount = df_layout.amount.astype('int64')
        df_layout.fraction = df_layout.fraction.astype('int64')
        return df_layout

    def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
        list_of_degree_occurences = generate_degree_tuples(report)

        degrees, amounts = map(list, zip(*list_of_degree_occurences))
        total = sum(amounts)
        return pd.DataFrame(
            {
                'revision': [report.head_commit] * len(degrees),
                'degree': degrees,
                'amount': amounts,
                'fraction': np.divide(amounts, total),
            },
            index=range(0, len(degrees)))

    return build_cached_report_table(GraphCacheType.BlameInteractionDegreeData,
                                     project_name, create_dataframe_layout,
                                     create_data_frame_for_report,
                                     load_blame_report, report_files)


@check_required_args(["result_folder", "project", 'get_cmap'])
def _gen_blame_interaction_data(**kwargs: tp.Any) -> pd.DataFrame:
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    result_dir = Path(kwargs["result_folder"])
    project_name = kwargs["project"]

    report_files = get_processed_revisions_files(
        project_name, result_dir, BlameReport,
        get_case_study_file_name_filter(case_study))

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
        super(BlameInteractionDegree, self).__init__('b_interaction_degree',
                                                     **kwargs)

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2
        }

        style.use(self.style)

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commit that are not in the case study, if one was
            selected. This allows us to only load file related to the
            case-study.
            """
            if self.plot_kwargs['plot_case_study'] is None:
                return data_frame
            case_study: CaseStudy = self.plot_kwargs['plot_case_study']
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x['revision'].split('-')[1]),
                axis=1)]

        interaction_plot_df = cs_filter(
            _gen_blame_interaction_data(**self.plot_kwargs))

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
                       labels=sorted(np.unique(interaction_plot_df['degree'])),
                       linewidth=plot_cfg['linewidth'])

        legend = axis.legend(title='Interaction degrees',
                             loc='upper left',
                             prop={
                                 'size': plot_cfg['legend_size'],
                                 'family': 'monospace'
                             })
        plt.setp(legend.get_title(),
                 fontsize=plot_cfg['legend_size'],
                 family='monospace')

        for y_label in axis.get_yticklabels():
            y_label.set_fontsize(8)
            y_label.set_fontfamily('monospace')

        for x_label in axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return set()
