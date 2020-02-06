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
from varats.plots.repository_churn import (draw_code_churn,
                                           build_repo_churn_table)
from varats.utils.project_util import get_local_project_git
from varats.utils.git_util import calc_repo_code_churn
from varats.plots.plot import Plot


def _build_commit_interaction_table(report_files: tp.List[Path],
                                    project_name: str,
                                    commit_map: CommitMap) -> pd.DataFrame:

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
                                  consider_out_interactions: bool,
                                  plot_cfg: tp.Dict[str, tp.Any]) -> None:
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
    axis.plot(data['revision'],
              lor,
              color='#cc0099',
              linewidth=plot_cfg['linewidth'])


def draw_perfect_lorenz_curve(axis: axes.SubplotBase, data: pd.DataFrame,
                              plot_cfg: tp.Dict[str, tp.Any]) -> None:
    """
    Draws a perfect lorenz curve onto the given axis, i.e., a straight line
    from the point of origin to the right upper corner.

    Args:
        axis: axis to draw to
        data: plotting data
    """
    axis.plot(data['revision'],
              np.linspace(0.0, 1.0, len(data['revision'])),
              color='black',
              linestyle='--',
              linewidth=plot_cfg['linewidth'])


def _gen_blame_head_interaction_data(**kwargs: tp.Any) -> pd.DataFrame:
    commit_map = kwargs['get_cmap']()
    case_study = kwargs.get('plot_case_study', None)  # can be None
    project_name = kwargs["project"]

    report_files = get_processed_revisions_files(
        project_name, BlameReport, get_case_study_file_name_filter(case_study))

    data_frame = _build_commit_interaction_table(report_files,
                                                 str(project_name), commit_map)
    return data_frame


def draw_interaction_code_churn(axis: axes.SubplotBase, data: pd.DataFrame,
                                project_name: str,
                                commit_map: CommitMap) -> None:
    """
    Helper function to draw parts of the code churn that are related to our
    data.

    Args:
        axis: to draw on
        data: plotting data
        project_name: name of the project
        commit_map: CommitMap for the given project(by project_name)
    """

    unique_revs = data['revision'].unique()

    def remove_revisions_without_data(revision: str) -> bool:
        """Removes all churn data where this plot has no data"""
        return revision[:10] in unique_revs

    def apply_sorting(churn_data: pd.DataFrame) -> pd.DataFrame:
        churn_data.set_index('rev_id', inplace=True)
        churn_data = churn_data.reindex(index=data['rev_id'])
        return churn_data.reset_index()

    draw_code_churn(axis, project_name, commit_map,
                    remove_revisions_without_data, apply_sorting)


def filter_non_code_changes(blame_data: pd.DataFrame,
                            project_name: str) -> pd.DataFrame:
    """
    Filter all revision from data frame that are not code change related.

    Args:
        blame_data: data to filter
        project_name: name of the project

    Returns:
        filtered data frame without rows related to non code changes
    """
    repo = get_local_project_git(project_name)
    code_related_changes = [x[:10] for x in calc_repo_code_churn(repo)]
    return blame_data[blame_data.apply(
        lambda x: x['revision'][:10] in code_related_changes, axis=1)]


class BlameLorenzCurve(Plot):
    """
    Plots the lorenz curve for IN/OUT interactions for a given project.
    """

    NAME = 'b_lorenz_curve'

    def __init__(self, **kwargs: tp.Any) -> None:
        super(BlameLorenzCurve, self).__init__("b_lorenz_curve", **kwargs)

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 2 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
        }
        style.use(self.style)

        case_study: CaseStudy = self.plot_kwargs['plot_case_study']
        project_name = self.plot_kwargs['project']

        fig = plt.figure()
        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        grid_spec = fig.add_gridspec(3, 2)

        main_axis = fig.add_subplot(grid_spec[:-1, :1])
        main_axis.set_title("Lorenz curve for incoming commit interactions")
        main_axis.get_xaxis().set_visible(False)

        main_axis_r = fig.add_subplot(grid_spec[:-1, -1])
        main_axis_r.set_title("Lorenz curve for outgoing commit interactions")
        main_axis_r.get_xaxis().set_visible(False)

        churn_axis = fig.add_subplot(grid_spec[2, :1], sharex=main_axis)
        churn_axis_r = fig.add_subplot(grid_spec[2, -1], sharex=main_axis_r)

        data = _gen_blame_head_interaction_data(**self.plot_kwargs)
        # TODO (se-passau/VaRA#550): refactor cs_filter into helper function
        data = data[data.apply(lambda x: case_study.has_revision(x['revision'])
                               if case_study else True,
                               axis=1)]
        data = filter_non_code_changes(data, project_name)

        # Draw left side of the plot
        draw_interaction_lorenz_curve(main_axis, data, True, False, plot_cfg)
        draw_perfect_lorenz_curve(main_axis, data, plot_cfg)

        draw_interaction_code_churn(churn_axis, data, project_name,
                                    self.plot_kwargs['get_cmap']())

        # Draw right side of the plot
        draw_interaction_lorenz_curve(main_axis_r, data, False, True, plot_cfg)
        draw_perfect_lorenz_curve(main_axis_r, data, plot_cfg)

        draw_interaction_code_churn(churn_axis_r, data,
                                    self.plot_kwargs['project'],
                                    self.plot_kwargs['get_cmap']())

        # Adapt axis to draw nicer plots
        for x_label in churn_axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

        for x_label in churn_axis_r.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


def gini(lorenz_values: pd.Series) -> pd.Series:
    """
    Calculates the gini coefficient:  half of the relative mean absolute
    difference between the lorenz values

    Args:
        lorenz_values: the scaled prefix sum of an ordered values range
    """
    return 0.5 * (
        (np.abs(np.subtract.outer(lorenz_values, lorenz_values)).mean()) /
        np.mean(lorenz_values))


def draw_gini_churn_over_time(axis: axes.SubplotBase, blame_data: pd.DataFrame,
                              project_name: str, commit_map: CommitMap,
                              consider_insertions: bool,
                              consider_deletions: bool,
                              plot_cfg: tp.Dict[str, tp.Any]) -> None:
    """
    Draws the gini of the churn distribution over time.

    Args:
        axis: axis to draw to
        blame_data: blame data of the base plot
        project_name: name of the project
        commit_map: CommitMap for the given project(by project_name)
        consider_insertions: True, insertions should be included
        consider_deletions: True, deletions should be included
    """
    churn_data = build_repo_churn_table(project_name, commit_map)

    # clean data
    unique_revs = blame_data['revision'].unique()

    def remove_revisions_without_data(revision: str) -> bool:
        """Removes all churn data where this plot has no data"""
        return revision[:10] in unique_revs

    churn_data = churn_data[churn_data.apply(
        lambda x: remove_revisions_without_data(x['revision']), axis=1)]

    # reorder churn data to match blame_data
    churn_data.set_index('rev_id', inplace=True)
    churn_data = churn_data.reindex(index=blame_data['rev_id'])
    churn_data = churn_data.reset_index()

    gini_churn = []
    for rev_id in blame_data['rev_id']:
        if consider_insertions and consider_deletions:
            lorenz_values = np.array(
                _transform_to_lorenz_values(
                    (churn_data[churn_data.rev_id <= rev_id].insertions +
                     churn_data[churn_data.rev_id <= rev_id].deletions
                    ).sort_values(ascending=True)))
        elif consider_insertions:
            lorenz_values = np.array(
                _transform_to_lorenz_values(churn_data[
                    churn_data.rev_id <= rev_id].insertions.sort_values(
                        ascending=True)))
        elif consider_deletions:
            lorenz_values = np.array(
                _transform_to_lorenz_values(churn_data[
                    churn_data.rev_id <= rev_id].deletions.sort_values(
                        ascending=True)))
        else:
            raise AssertionError(
                "At least one of the in/out interaction needs to be selected")

        gini_churn.append(gini(lorenz_values))
    if consider_insertions and consider_deletions:
        linestyle = '-'
        label = 'Insertions + Deletions'
    elif consider_insertions:
        linestyle = '--'
        label = 'Insertions'
    else:
        linestyle = ':'
        label = 'Deletions'

    axis.plot(blame_data['revision'],
              gini_churn,
              linestyle=linestyle,
              linewidth=plot_cfg['linewidth'],
              label=label,
              color='orange')


def draw_gini_blame_over_time(axis: axes.SubplotBase, blame_data: pd.DataFrame,
                              consider_in_interactions: bool,
                              consider_out_interactions: bool,
                              plot_cfg: tp.Dict[str, tp.Any]) -> None:
    """
    Draws the gini coefficients of the blame interactions over time.

    Args:
        axis: axis to draw to
        blame_data: blame data of the base plot
        consider_in_interactions: True, IN interactions should be included
        consider_out_interactions: True, OUT interactions should be included
    """
    if consider_in_interactions and consider_out_interactions:
        data_selector = 'HEAD_Interactions'
        linestyle = '-'
        label = "Interactions"
    elif consider_in_interactions:
        data_selector = 'IN_HEAD_Interactions'
        linestyle = '--'
        label = "IN Interactions"
    elif consider_out_interactions:
        data_selector = 'OUT_HEAD_Interactions'
        linestyle = ':'
        label = "OUT Interactions"
    else:
        raise AssertionError(
            "At least one of the in/out interaction needs to be selected")

    gini_coefficients = []

    for rev_id in blame_data['rev_id']:
        lvalues = np.array(
            _transform_to_lorenz_values(
                blame_data[blame_data.rev_id <= rev_id]
                [data_selector].sort_values(ascending=True)))

        gini_coefficients.append(gini(lvalues))

    axis.plot(blame_data['revision'],
              gini_coefficients,
              linestyle=linestyle,
              linewidth=plot_cfg['linewidth'],
              label=label,
              color='#cc0099')


class BlameGiniOverTime(Plot):
    """
    Plots the gini coefficient over time for a project.
    This shows how the distribution of the interactions/churn changes of time.
    """

    NAME = 'b_gini_overtime'

    def __init__(self, **kwargs: tp.Any) -> None:
        super(BlameGiniOverTime, self).__init__("b_gini_overtime", **kwargs)

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 2 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
        }
        style.use(self.style)

        case_study: CaseStudy = self.plot_kwargs['plot_case_study']

        fig = plt.figure()
        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        grid_spec = fig.add_gridspec(3, 1)

        main_axis = fig.add_subplot(grid_spec[:-1, :])
        main_axis.set_title("Gini coefficient over the project lifetime")
        main_axis.get_xaxis().set_visible(False)

        churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)

        data = _gen_blame_head_interaction_data(**self.plot_kwargs)

        commit_map = self.plot_kwargs['get_cmap']()
        project_name = self.plot_kwargs["project"]

        # TODO (se-passau/VaRA#550): refactor cs_filter into helper function
        data = data[data.apply(lambda x: case_study.has_revision(x['revision'])
                               if case_study else True,
                               axis=1)]
        data = filter_non_code_changes(data, project_name)

        data.sort_values(by=['rev_id'], inplace=True)

        draw_gini_blame_over_time(main_axis, data, True, True, plot_cfg)
        draw_gini_blame_over_time(main_axis, data, True, False, plot_cfg)
        draw_gini_blame_over_time(main_axis, data, False, True, plot_cfg)
        draw_gini_churn_over_time(main_axis, data, project_name, commit_map,
                                  True, True, plot_cfg)
        draw_gini_churn_over_time(main_axis, data, project_name, commit_map,
                                  True, False, plot_cfg)
        draw_gini_churn_over_time(main_axis, data, project_name, commit_map,
                                  False, True, plot_cfg)
        main_axis.legend()

        main_axis.set_ylim((0., 1.))

        draw_interaction_code_churn(churn_axis, data,
                                    self.plot_kwargs['project'],
                                    self.plot_kwargs['get_cmap']())

        # Adapt axis to draw nicer plots
        for x_label in churn_axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
