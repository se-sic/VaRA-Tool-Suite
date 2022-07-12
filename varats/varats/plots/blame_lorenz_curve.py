"""Generate a plot to visualize revision impact inequality based on data-flow
interactions."""
import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import axes, style

from varats.data.databases.blame_interaction_database import (
    BlameInteractionDatabase,
)
from varats.data.metrics import gini_coefficient, lorenz_curve
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.plots.repository_churn import (
    build_repo_churn_table,
    draw_code_churn,
)
from varats.project.project_util import get_local_project_git
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    ChurnConfig,
    calc_repo_code_churn,
    ShortCommitHash,
    FullCommitHash,
)


def draw_interaction_lorenz_curve(
    axis: axes.SubplotBase, data: pd.DataFrame, unique_rev_strs: tp.List[str],
    consider_in_interactions: bool, consider_out_interactions: bool,
    line_width: float
) -> None:
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
            "At least one of the in/out interaction needs to be selected"
        )

    data.sort_values(by=[data_selector, 'time_id'], inplace=True)
    lor = lorenz_curve(data[data_selector])

    axis.plot(unique_rev_strs, lor, color='#cc0099', linewidth=line_width)


def draw_perfect_lorenz_curve(
    axis: axes.SubplotBase, unique_rev_strs: tp.List[str], line_width: float
) -> None:
    """
    Draws a perfect lorenz curve onto the given axis, i.e., a straight line from
    the point of origin to the right upper corner.

    Args:
        axis: axis to draw to
        data: plotting data
    """
    axis.plot(
        unique_rev_strs,
        np.linspace(0.0, 1.0, len(unique_rev_strs)),
        color='black',
        linestyle='--',
        linewidth=line_width
    )


def draw_interaction_code_churn(
    axis: axes.SubplotBase, data: pd.DataFrame, project_name: str,
    commit_map: CommitMap
) -> None:
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

    def remove_revisions_without_data(revision: ShortCommitHash) -> bool:
        """Removes all churn data where this plot has no data."""
        return revision.hash in unique_revs

    def apply_sorting(churn_data: pd.DataFrame) -> pd.DataFrame:
        churn_data.set_index('time_id', inplace=True)
        churn_data = churn_data.reindex(index=data['time_id'])
        return churn_data.reset_index()

    draw_code_churn(
        axis, project_name, commit_map, remove_revisions_without_data,
        apply_sorting
    )


def filter_non_code_changes(
    blame_data: pd.DataFrame, project_name: str
) -> pd.DataFrame:
    """
    Filter all revision from data frame that are not code change related.

    Args:
        blame_data: data to filter
        project_name: name of the project

    Returns:
        filtered data frame without rows related to non code changes
    """
    repo = get_local_project_git(project_name)
    code_related_changes = [
        x.hash for x in calc_repo_code_churn(
            repo, ChurnConfig.create_c_style_languages_config()
        )
    ]
    return blame_data[blame_data.apply(
        lambda x: x['revision'] in code_related_changes, axis=1
    )]


class BlameLorenzCurve(Plot, plot_name="b_lorenz_curve"):
    """Plots the lorenz curve for IN/OUT interactions for a given project."""

    NAME = 'b_lorenz_curve'

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())

        case_study: CaseStudy = self.plot_kwargs['case_study']
        project_name: str = case_study.project_name
        commit_map = get_commit_map(project_name)

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

        data = BlameInteractionDatabase.get_data_for_project(
            project_name, [
                "revision", "time_id", "IN_HEAD_Interactions",
                "OUT_HEAD_Interactions", "HEAD_Interactions"
            ], commit_map, case_study
        )
        data = filter_non_code_changes(data, project_name)
        if data.empty:
            raise PlotDataEmpty

        unique_rev_strs: tp.List[str] = [rev.hash for rev in data['revision']]

        # Draw left side of the plot
        draw_interaction_lorenz_curve(
            main_axis, data, unique_rev_strs, True, False,
            self.plot_config.line_width()
        )
        draw_perfect_lorenz_curve(
            main_axis, unique_rev_strs, self.plot_config.line_width()
        )

        draw_interaction_code_churn(churn_axis, data, project_name, commit_map)

        # Draw right side of the plot
        draw_interaction_lorenz_curve(
            main_axis_r, data, unique_rev_strs, False, True,
            self.plot_config.line_width()
        )
        draw_perfect_lorenz_curve(
            main_axis_r, unique_rev_strs, self.plot_config.line_width()
        )

        draw_interaction_code_churn(
            churn_axis_r, data, project_name, commit_map
        )

        # Adapt axis to draw nicer plots
        for x_label in churn_axis.get_xticklabels():
            x_label.set_fontsize(self.plot_config.x_tick_size())
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

        for x_label in churn_axis_r.get_xticklabels():
            x_label.set_fontsize(self.plot_config.x_tick_size())
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class BlameLorenzCurveGenerator(
    PlotGenerator,
    generator_name="lorenz-curve-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates lorenz-curve plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            BlameLorenzCurve(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]


def draw_gini_churn_over_time(
    axis: axes.SubplotBase, blame_data: pd.DataFrame,
    unique_rev_strs: tp.List[str], project_name: str, commit_map: CommitMap,
    consider_insertions: bool, consider_deletions: bool, line_width: float
) -> None:
    """
    Draws the gini of the churn distribution over time.

    Args:
        axis: axis to draw to
        blame_data: blame data of the base plot
        project_name: name of the project
        commit_map: CommitMap for the given project(by project_name)
        consider_insertions: True, insertions should be included
        consider_deletions: True, deletions should be included
        line_width: line width of the plot lines
    """
    churn_data = build_repo_churn_table(project_name, commit_map)

    # clean data
    unique_revs = blame_data['revision'].unique()

    def remove_revisions_without_data(revision: ShortCommitHash) -> bool:
        """Removes all churn data where this plot has no data."""
        return revision.hash[:10] in unique_revs

    churn_data = churn_data[churn_data.apply(
        lambda x: remove_revisions_without_data(x['revision']), axis=1
    )]

    # reorder churn data to match blame_data
    churn_data.set_index('time_id', inplace=True)
    churn_data = churn_data.reindex(index=blame_data['time_id'])
    churn_data = churn_data.reset_index()

    gini_churn = []
    for time_id in blame_data['time_id']:
        if consider_insertions and consider_deletions:
            distribution = (
                churn_data[churn_data.time_id <= time_id].insertions +
                churn_data[churn_data.time_id <= time_id].deletions
            ).sort_values(ascending=True)
        elif consider_insertions:
            distribution = churn_data[churn_data.time_id <= time_id
                                     ].insertions.sort_values(ascending=True)
        elif consider_deletions:
            distribution = churn_data[churn_data.time_id <= time_id
                                     ].deletions.sort_values(ascending=True)
        else:
            raise AssertionError(
                "At least one of the in/out interaction needs to be selected"
            )

        gini_churn.append(gini_coefficient(distribution))
    if consider_insertions and consider_deletions:
        linestyle = '-'
        label = 'Insertions + Deletions'
    elif consider_insertions:
        linestyle = '--'
        label = 'Insertions'
    else:
        linestyle = ':'
        label = 'Deletions'

    axis.plot(
        unique_rev_strs,
        gini_churn,
        linestyle=linestyle,
        linewidth=line_width,
        label=label,
        color='orange'
    )


def draw_gini_blame_over_time(
    axis: axes.SubplotBase, blame_data: pd.DataFrame,
    unique_rev_strs: tp.List[str], consider_in_interactions: bool,
    consider_out_interactions: bool, line_width: float
) -> None:
    """
    Draws the gini coefficients of the blame interactions over time.

    Args:
        axis: axis to draw to
        blame_data: blame data of the base plot
        consider_in_interactions: True, IN interactions should be included
        consider_out_interactions: True, OUT interactions should be included
        line_width: line width of the plot lines
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
            "At least one of the in/out interaction needs to be selected"
        )

    gini_coefficients = []

    for time_id in blame_data.time_id:
        distribution = blame_data[blame_data.time_id <= time_id
                                 ][data_selector].sort_values(ascending=True)

        gini_coefficients.append(gini_coefficient(distribution))

    axis.plot(
        unique_rev_strs,
        gini_coefficients,
        linestyle=linestyle,
        linewidth=line_width,
        label=label,
        color='#cc0099'
    )


class BlameGiniOverTime(Plot, plot_name="b_gini_overtime"):
    """
    Plots the gini coefficient over time for a project.

    This shows how the distribution of the interactions/churn changes of time.
    """

    NAME = 'b_gini_overtime'

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())

        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        data = BlameInteractionDatabase.get_data_for_project(
            project_name, [
                "revision", "time_id", "IN_HEAD_Interactions",
                "OUT_HEAD_Interactions", "HEAD_Interactions"
            ], commit_map, case_study
        )
        data = filter_non_code_changes(data, project_name)
        if data.empty:
            raise PlotDataEmpty
        data.sort_values(by=['time_id'], inplace=True)

        fig = plt.figure()
        fig.subplots_adjust(top=0.95, hspace=0.05, right=0.95, left=0.07)
        grid_spec = fig.add_gridspec(3, 1)

        main_axis = fig.add_subplot(grid_spec[:-1, :])
        main_axis.set_title("Gini coefficient over the project lifetime")
        main_axis.get_xaxis().set_visible(False)

        churn_axis = fig.add_subplot(grid_spec[2, :], sharex=main_axis)

        unique_rev_strs: tp.List[str] = [rev.hash for rev in data['revision']]

        draw_gini_blame_over_time(
            main_axis, data, unique_rev_strs, True, True,
            self.plot_config.line_width()
        )
        draw_gini_blame_over_time(
            main_axis, data, unique_rev_strs, True, False,
            self.plot_config.line_width()
        )
        draw_gini_blame_over_time(
            main_axis, data, unique_rev_strs, False, True,
            self.plot_config.line_width()
        )
        draw_gini_churn_over_time(
            main_axis, data, unique_rev_strs, project_name, commit_map, True,
            True, self.plot_config.line_width()
        )
        draw_gini_churn_over_time(
            main_axis, data, unique_rev_strs, project_name, commit_map, True,
            False, self.plot_config.line_width()
        )
        draw_gini_churn_over_time(
            main_axis, data, unique_rev_strs, project_name, commit_map, False,
            True, self.plot_config.line_width()
        )
        main_axis.legend()

        main_axis.set_ylim((0., 1.))

        draw_interaction_code_churn(churn_axis, data, project_name, commit_map)

        # Adapt axis to draw nicer plots
        for x_label in churn_axis.get_xticklabels():
            x_label.set_fontsize(self.plot_config.x_tick_size())
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class BlameGiniOverTimeGenerator(
    PlotGenerator,
    generator_name="gini-overtime-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates gini-overtime plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            BlameGiniOverTime(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
