"""
Generate a plot to visualize revision impact inequality based on data-flow
interactions.
"""
import typing as tp
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.axes as axes

from varats.data.reports.commit_report import CommitMap
from varats.jupyterhelper.file import load_blame_report
from varats.data.cache_helper import \
    (GraphCacheType, build_cached_report_table)
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter
from varats.data.revisions import get_processed_revisions_files
from varats.data.reports.blame_report import (BlameReport,
                                              generate_in_head_interactions,
                                              generate_out_head_interactions)
from varats.plots.repository_churn import draw_code_churn
from varats.plots.plot import Plot


def _build_commit_interaction_table(report_files: tp.List[Path],
                                    project_name: str,
                                    commit_map: CommitMap) -> pd.DataFrame:
    """
    TODO:
    """

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(columns=[
            'revision',
            'rev_id',
            'IN_HEAD_Interactions',
            'OUT_HEAD_Interactions',
            'HEAD_Interactions',
        ])
        df_layout.rev_id = df_layout.rev_id.astype('int32')
        df_layout.IN_HEAD_Interactions = df_layout.IN_HEAD_Interactions.astype(
            'int64')
        df_layout.OUT_HEAD_Interactions = \
            df_layout.OUT_HEAD_Interactions.astype('int64')
        df_layout.HEAD_Interactions = df_layout.HEAD_Interactions.astype(
            'int64')
        return df_layout

    def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
        in_head_interactions = len(generate_in_head_interactions(report))
        out_head_interactions = len(generate_out_head_interactions(report))

        return pd.DataFrame(
            {
                'revision':
                    report.head_commit,
                'rev_id':
                    commit_map.short_time_id(report.head_commit),
                'IN_HEAD_Interactions':
                    in_head_interactions,
                'OUT_HEAD_Interactions':
                    out_head_interactions,
                'HEAD_Interactions':
                    in_head_interactions + out_head_interactions
            },
            index=[0])

    return build_cached_report_table(GraphCacheType.BlameInteractionData,
                                     project_name, create_dataframe_layout,
                                     create_data_frame_for_report,
                                     load_blame_report, report_files)


def _transform_to_lorenz_values(data: pd.Series) -> pd.Series:
    """
    Calucaltes the values for lorenz curve, i.e., the scaled prefix sum.

    Args:
        data: data range to calc scaled-prefix sum on
    """
    scaled_prefix_sum = data.cumsum() / data.sum()
    return scaled_prefix_sum


def draw_interaction_lorenz_curve(axis: axes.SubplotBase, data: pd.DataFrame,
                                  consider_in_interactions: bool,
                                  consider_out_interactions: bool) -> None:
    """
    Draws a lorenz_curve onto the given axis.

    Args:
        axis: matplot axis to draw on
        data: plotting data
    """
    if consider_in_interactions and consider_out_interactions:
        data_selector = 'HEAD_Interactions'
    elif consider_in_interactions:
        data_selector = 'IN_HEAD_Interactions'
    elif consider_out_interactions:
        data_selector = 'OUT_HEAD_Interactions'
    else:
        raise AssertionError(
            "At least one of the in/out interaction needs to be selected")

    data.sort_values(by=[data_selector, 'revision'], inplace=True)
    lor = _transform_to_lorenz_values(data[data_selector])
    axis.plot(data['revision'], lor, color='blue')


def draw_perfect_lorenz_curve(axis: axes.SubplotBase,
                              data: pd.DataFrame) -> None:
    """
    Draws a perfect lorenz curve onto the given axis, i.e., a straight line
    from the point of origin to the right upper corner.

    Args:
        axis: axis to draw to
        data: plotting data
    """
    axis.plot(data['revision'],
              np.linspace(0.0, 1.0, len(data['revision'])),
              color='green')


def _gen_blame_head_interaction_data(**kwargs: tp.Any) -> pd.DataFrame:
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    project_name = kwargs["project"]

    report_files = get_processed_revisions_files(
        project_name, BlameReport, get_case_study_file_name_filter(case_study))

    data_frame = _build_commit_interaction_table(report_files,
                                                 str(project_name), commit_map)
    return data_frame


class BlameLorenzCurve(Plot):
    """
    TODO:
    """

    def __init__(self, **kwargs: tp.Any) -> None:
        super(BlameLorenzCurve, self).__init__("b_lorenz_curve", **kwargs)

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
        }
        style.use(self.style)

        case_study: CaseStudy = self.plot_kwargs['plot_case_study']

        fig = plt.figure()
        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        grid_spec = fig.add_gridspec(3, 1)

        main_axis = fig.add_subplot(grid_spec[:-1, :])
        main_axis.get_xaxis().set_visible(False)
        churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)

        data = _gen_blame_head_interaction_data(**self.plot_kwargs)
        # TODO (se-passau/VaRA#550): refactor cs_filter into helper function
        data = data[data.apply(lambda x: case_study.has_revision(x['revision'])
                               if case_study else True,
                               axis=1)]

        draw_interaction_lorenz_curve(main_axis, data, False, True)
        draw_perfect_lorenz_curve(main_axis, data)

        # Add code churn subplot
        if True:  # TODO: remove later to always draw churn
            unique_revs = data['revision'].unique()

            def remove_revisions_without_data(revision: str) -> bool:
                """Removes all churn data where this plot has no data"""
                return revision[:10] in unique_revs

            def apply_sorting(churn_data: pd.DataFrame) -> pd.DataFrame:
                churn_data.set_index('rev_id', inplace=True)
                churn_data = churn_data.reindex(index=data['rev_id'])
                return churn_data.reset_index()

            draw_code_churn(churn_axis, self.plot_kwargs['project'],
                            self.plot_kwargs['get_cmap'](),
                            remove_revisions_without_data, apply_sorting)

        for x_label in churn_axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
