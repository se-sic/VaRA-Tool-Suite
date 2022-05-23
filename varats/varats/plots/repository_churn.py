"""
Generate plots to visualize code churn of a software repository.

For code churn, we only consider changes in source files.
"""
import typing as tp
from itertools import islice

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import axes, style

from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.project.project_util import get_local_project_git_path
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    ChurnConfig,
    calc_repo_code_churn,
    calc_code_churn,
    ShortCommitHash,
    FullCommitHash,
)


def build_repo_churn_table(
    project_name: str, commit_map: CommitMap
) -> pd.DataFrame:
    """
    Build a pandas data table that contains all churn related data for an
    repository.

    Table layout:
            "revision", "time_id", "insertions", "deletions", "changed_files"

    Args:
        project_name: name of the project
        commit_map: CommitMap for the given project(by project_name)
    """

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(
            columns=[
                "revision", "time_id", "insertions", "deletions",
                "changed_files"
            ]
        )
        df_layout.time_id = df_layout.time_id.astype('int32')
        df_layout.insertions = df_layout.insertions.astype('int64')
        df_layout.deletions = df_layout.deletions.astype('int64')
        df_layout.changed_files = df_layout.changed_files.astype('int64')
        return df_layout

    repo_path = get_local_project_git_path(project_name)
    # By default we only look at c-style code files
    code_churn = calc_repo_code_churn(
        repo_path, ChurnConfig.create_c_style_languages_config()
    )
    churn_data = pd.DataFrame({
        "revision": list(code_churn),
        "time_id": [commit_map.time_id(x) for x in code_churn],
        "insertions": [x[1] for x in code_churn.values()],
        "deletions": [x[2] for x in code_churn.values()],
        "changed_files": [x[0] for x in code_churn.values()]
    })

    return pd.concat([create_dataframe_layout(), churn_data])


def build_revisions_churn_table(
    project_name: str, commit_map: CommitMap, revisions: tp.List[FullCommitHash]
) -> pd.DataFrame:
    """
    Build a pandas data frame that contains all churn related data for the given
    list of revisions.

    The churn is calculated as the diff between two successive revisions in
    the ``revisions`` list.

    Table layout:
            "revision", "time_id", "insertions", "deletions", "changed_files"

    Args:
        project_name: name of the project
        commit_map: CommitMap for the given project(by project_name)
        revisions: list of revisions used to calculate the churn data

    Returns:
        a data frame containing the churn data
    """

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(
            columns=[
                "revision", "time_id", "insertions", "deletions",
                "changed_files"
            ]
        )
        df_layout.time_id = df_layout.time_id.astype('int32')
        df_layout.insertions = df_layout.insertions.astype('int64')
        df_layout.deletions = df_layout.deletions.astype('int64')
        df_layout.changed_files = df_layout.changed_files.astype('int64')
        return df_layout

    repo_path = get_local_project_git_path(project_name)

    revision_pairs = zip(*(islice(revisions, i, None) for i in range(2)))
    code_churn = [(0, 0, 0)]
    code_churn.extend([
        calc_code_churn(
            repo_path, a, b, ChurnConfig.create_c_style_languages_config()
        ) for a, b in revision_pairs
    ])
    churn_data = pd.DataFrame({
        "revision": revisions,
        "time_id": [commit_map.time_id(x) for x in revisions],
        "insertions": [x[1] for x in code_churn],
        "deletions": [x[2] for x in code_churn],
        "changed_files": [x[0] for x in code_churn]
    })

    return pd.concat([create_dataframe_layout(), churn_data])


CODE_CHURN_INSERTION_LIMIT = 1500
CODE_CHURN_DELETION_LIMIT = 1500


def draw_code_churn(
    axis: axes.Axes,
    project_name: str,
    commit_map: CommitMap,
    revision_selector: tp.Callable[[ShortCommitHash], bool] = lambda x: True,
    sort_df: tp.Callable[
        [pd.DataFrame],
        pd.DataFrame] = lambda data: data.sort_values(by=['time_id'])
) -> None:
    """
    Draws a churn plot onto an axis, showing insertions with green and deletions
    with red.

    Args:
        axis: axis to plot on
        project_name: name of the project to plot churn for
        commit_map: CommitMap for the given project(by project_name)
        revision_selector: takes a revision string and returns True if this rev
                           should be included
        sort_df: function that returns a sorted data frame to plot
    """
    code_churn = build_repo_churn_table(project_name, commit_map)

    code_churn = code_churn[
        code_churn.apply(lambda x: revision_selector(x['revision']), axis=1)]

    code_churn = sort_df(code_churn)

    revision_strs = code_churn.time_id.astype(
        str
    ) + '-' + code_churn.revision.map(lambda x: x.short_hash)

    clipped_insertions = [
        x if x < CODE_CHURN_INSERTION_LIMIT else 1.3 *
        CODE_CHURN_INSERTION_LIMIT for x in code_churn.insertions
    ]
    clipped_deletions = [
        -x if x < CODE_CHURN_DELETION_LIMIT else -1.3 *
        CODE_CHURN_DELETION_LIMIT for x in code_churn.deletions
    ]

    axis.set_ylim(-CODE_CHURN_DELETION_LIMIT, CODE_CHURN_INSERTION_LIMIT)
    axis.fill_between(revision_strs, clipped_insertions, 0, facecolor='green')
    axis.fill_between(
        revision_strs,
        # we need a - here to visualize deletions as negative additions
        clipped_deletions,
        0,
        facecolor='red'
    )


def draw_code_churn_for_revisions(
    axis: axes.Axes, project_name: str, commit_map: CommitMap,
    revisions: tp.List[FullCommitHash]
) -> None:
    """
    Draws a churn plot onto an axis, showing insertions with green and deletions
    with red.

    The churn is calculated as the diff between two successive revisions in
    the ``revisions`` list.

    Args:
        axis: axis to plot on
        project_name: name of the project to plot churn for
        commit_map: CommitMap for the given project(by project_name)
        revisions: list of revisions used to calculate the churn data
    """

    churn_data = build_revisions_churn_table(
        project_name, commit_map, revisions
    )
    clipped_insertions = [
        x if x < CODE_CHURN_INSERTION_LIMIT else 1.3 *
        CODE_CHURN_INSERTION_LIMIT for x in churn_data.insertions
    ]
    clipped_deletions = [
        -x if x < CODE_CHURN_DELETION_LIMIT else -1.3 *
        CODE_CHURN_DELETION_LIMIT for x in churn_data.deletions
    ]
    revision_strs: tp.List[str] = [rev.short_hash for rev in revisions]

    axis.set_ylim(-CODE_CHURN_DELETION_LIMIT, CODE_CHURN_INSERTION_LIMIT)
    axis.fill_between(revision_strs, clipped_insertions, 0, facecolor='green')
    axis.fill_between(
        revision_strs,
        # we need a - here to visualize deletions as negative additions
        clipped_deletions,
        0,
        facecolor='red'
    )
    revision_strs = churn_data.time_id.astype(
        str
    ) + '-' + churn_data.revision.map(lambda x: x.short_hash)
    axis.set_xticks(axis.get_xticks())
    axis.set_xticklabels(revision_strs)


class RepoChurnPlot(Plot, plot_name="repo_churn"):
    """Plot to visualize code churn for a git repository."""

    NAME = 'repo_churn'

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())
        case_study: CaseStudy = self.plot_kwargs['case_study']
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        _, axis = plt.subplots()
        draw_code_churn(
            axis, project_name, commit_map,
            case_study.has_revision if case_study else lambda x: True
        )

        for x_label in axis.get_xticklabels():
            x_label.set_fontsize(self.plot_config.x_tick_size())
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class RepoChurnPlotGenerator(
    PlotGenerator,
    generator_name="repo-churn-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates repo-churn plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            RepoChurnPlot(self.plot_config, case_study=cs, **self.plot_kwargs)
            for cs in case_studies
        ]
