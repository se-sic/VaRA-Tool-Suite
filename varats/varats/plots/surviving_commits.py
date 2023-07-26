"""Plots for the analysis of loc and interactions over time."""
import math
import typing as tp

import click
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import style
from pandas import DataFrame
from pygtrie import CharTrie

from varats.data.databases.commit_interaction_aggregate_database import (
    SurvivingInteractionsDatabase,
)
from varats.data.databases.survivng_lines_database import SurvivingLinesDatabase
from varats.mapping.commit_map import get_commit_map, CommitMap
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.project.project_util import get_primary_project_source
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import (
    ShortCommitHash,
    FullCommitHash,
    create_commit_lookup_helper,
    CommitRepoPair,
)


def get_lines_per_commit_long(
    case_study: CaseStudy, filter_cs=True
) -> DataFrame:
    """Get a data frame with the surviving lines of each commit at the revisions
    of a case study in the format Revision | Commit | Lines."""
    project_name = case_study.project_name
    data = SurvivingLinesDatabase.get_data_for_project(
        project_name, ["revision", "commit_hash", "lines"],
        get_commit_map(project_name), case_study
    )
    data.rename(columns={'commit_hash': 'base_hash'}, inplace=True)

    def cs_filter(data_frame: DataFrame) -> DataFrame:
        """Filter out all commits that are not in the case study if one was
        selected."""
        if case_study is None or data_frame.empty:
            return data_frame
        # use a trie for fast prefix lookup
        revisions = CharTrie()
        for revision in case_study.revisions:
            revisions[revision.hash] = True
        return data_frame[
            data_frame["base_hash"].apply(lambda x: revisions.has_node(x) != 0)]

    return cs_filter(data) if filter_cs else data


def get_normalized_lines_per_commit_long(
    case_study: CaseStudy, filter_cs=True
) -> DataFrame:
    """Get a data frame with the surviving lines of each commit at the revisions
    of a case study normalized by the maximum lines of the commit in the format
    Revision | Commit | Lines."""
    data = get_lines_per_commit_long(case_study, filter_cs)
    max_lines = data.drop(columns=["revision"]).groupby("base_hash").max()
    data = data.apply(
        lambda x: [
            x['revision'], x['base_hash'],
            (x['lines'] * 100 / max_lines['lines'][x['base_hash']])
        ],
        axis=1,
        result_type='broadcast'
    )

    return data


def get_normalized_lines_per_commit_wide(case_study: CaseStudy) -> DataFrame:
    """
    Get a data frame with the surviving lines of each commit at the revisions of
    a case study normalized by the maximum lines of the commit.

    each commit is a row , the revisions are the columns.
    """
    case_study_data = get_normalized_lines_per_commit_long(case_study)
    case_study_data = case_study_data.pivot(
        index="base_hash", columns='revision', values='lines'
    )
    cmap = get_commit_map(case_study.project_name)
    case_study_data.sort_index(
        key=lambda x: x.map(lambda y: cmap.short_time_id(ShortCommitHash(y))),
        inplace=True
    )
    case_study_data.sort_index(
        axis=1, key=lambda x: x.map(cmap.short_time_id), inplace=True
    )

    return case_study_data.astype(float)


def get_interactions_per_commit_long(case_study: CaseStudy, filter_cs=True):
    """Get a data frame with the surviving interactions of each commit at the
    revisions of a case study in the format Revision | Commit | Interactions."""
    project_name = case_study.project_name
    data = SurvivingInteractionsDatabase.get_data_for_project(
        project_name, ["revision", "base_hash", "interactions"],
        get_commit_map(project_name), case_study
    )

    def cs_filter(data_frame: DataFrame) -> DataFrame:
        """Filter out all commits that are not in the case study if one was
        selected."""
        if case_study is None or data_frame.empty:
            return data_frame
        # use a trie for fast prefix lookup
        revisions = CharTrie()
        for revision in case_study.revisions:
            revisions[revision.hash] = True
        return data_frame[
            data_frame["base_hash"].apply(lambda x: revisions.has_node(x) != 0)]

    return cs_filter(data) if filter_cs else data


def get_normalized_interactions_per_commit_long(
    case_study: CaseStudy, filter_cs=True
) -> DataFrame:
    """Get a data frame with the surviving interactions of each commit at the
    revisions of a case study normalized by the maximum interactions of the
    commit in the format Revision | Commit | Interactions."""
    data = get_interactions_per_commit_long(case_study, filter_cs)
    max_interactions = data.drop(columns=["revision"]
                                ).groupby("base_hash").max()
    data = data.apply(
        lambda x: [
            x['base_hash'], x['revision'],
            (
                x['interactions'] * 100 / max_interactions['interactions'][x[
                    'base_hash']]
            ) if max_interactions['interactions'][x['base_hash']] is not math.
            nan else math.nan
        ],
        axis=1,
        result_type='broadcast'
    )

    return data


def get_normalized_interactions_per_commit_wide(
    case_study: CaseStudy
) -> DataFrame:
    """
    Get a data frame with the surviving interactions of each commit at the
    revisions of a case study normalized by the maximum interactions of the
    commit.

    each commit is a row , the revisions are the columns.
    """
    data = get_normalized_interactions_per_commit_long(case_study)
    data = data.pivot(
        index="base_hash", columns="revision", values="interactions"
    )
    cmap = get_commit_map(case_study.project_name)
    data.sort_index(
        key=lambda x: x.map(lambda y: cmap.short_time_id(ShortCommitHash(y))),
        inplace=True
    )
    data.sort_index(
        axis=1, key=lambda x: x.map(cmap.short_time_id), inplace=True
    )
    return data.astype(float)


def lines_and_interactions(case_study: CaseStudy) -> DataFrame:
    """
    Get a data frame with the surviving lines and interactions of each commit at
    the revisions of a case study each commit is a row , the revisions are the
    columns, lines and interactions are sublevels.

    An additionla sublevel called space is added for better readability when
    plotted.
    """
    lines: DataFrame = get_normalized_lines_per_commit_long(case_study)

    interactions: DataFrame = get_normalized_interactions_per_commit_long(
        case_study
    )
    data = lines.merge(interactions, how='left', on=["base_hash", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    data.insert(3, "space", np.nan)
    data = data.pivot(
        index="base_hash",
        columns="revision",
        values=["lines", "interactions", 'space']
    )
    data = data.stack(level=0, dropna=False)
    cmap = get_commit_map(case_study.project_name)
    data.sort_index(
        level=0,
        key=lambda x: x.map(lambda y: cmap.short_time_id(ShortCommitHash(y))),
        inplace=True
    )
    data.sort_index(
        axis=1, key=lambda x: x.map(cmap.short_time_id), inplace=True
    )
    return data.astype(float)


def get_author_color_map(data, case_study) -> dict[tp.Any, tp.Any]:
    """Generate a color map for authors to collor commits based on theyr
    authors."""
    commit_lookup_helper = create_commit_lookup_helper(case_study.project_name)
    author_set: set = set()
    for commit_hash in data.index.get_level_values(0):
        repo = get_primary_project_source(case_study.project_name).local
        commit = commit_lookup_helper(
            CommitRepoPair(FullCommitHash(commit_hash), repo)
        )
        author_set.add(commit.author.name)
    author_list = list(author_set)
    colormap = plt.get_cmap("nipy_spectral")
    colors = colormap(np.linspace(0, 1, len(author_list)))
    return dict(zip(author_list, colors))


class SingleCommitPlot(Plot, plot_name="single_commit_survival"):
    """Plot for the evolution of a single commit."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(
        self, plot_config: PlotConfig, revision: str, **kwargs: tp.Any
    ):
        self._revision = revision
        super().__init__(plot_config, **kwargs)

    @property
    def name(self) -> str:
        return "single_commit_survival_" + ShortCommitHash(self._revision).hash

    def plot(self, view_mode: bool) -> None:
        """Plot the evolution of a single commit."""
        _, axis = plt.subplots(1, 1)
        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        case_study = self.plot_kwargs['case_study']
        lines: DataFrame = get_lines_per_commit_long(case_study, False)

        interactions: DataFrame = get_interactions_per_commit_long(
            case_study, False
        )
        data = lines.merge(
            interactions, how='left', on=["base_hash", "revision"]
        )
        data.dropna(
            axis=0, how='any', inplace=True, subset=["lines", "interactions"]
        )

        data = data[
            data["base_hash"].apply(lambda x: x.startswith(self._revision))]
        data.set_index("revision", inplace=True)
        cmap = get_commit_map(case_study.project_name)
        data.sort_index(
            axis=0, key=lambda x: x.map(cmap.short_time_id), inplace=True
        )
        data.drop(columns="base_hash")
        _, axis = plt.subplots(1, 1)
        plt.setp(
            axis.get_xticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace',
        )
        ax = axis.twinx()
        x_axis = range(len(data))
        ax.scatter(x_axis, data['lines'], color="green")
        ax.set_ylabel("Lines", color="g", fontsize=14)
        axis.scatter(x_axis, data['interactions'], color="orange")
        axis.set_ylabel("Interactions", color="orange", fontsize=14)
        axis.tick_params(axis="y", labelsize=14)
        ax.set_ylim(ymin=0)
        axis.set_ylim(ymin=0)
        axis.set_xlabel("Revisions", fontsize=14)
        axis.set_xticklabels([])
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)


class HeatMapPlot(Plot, plot_name=None):
    """
    Base Heatmap plot for to plot wide data frames.

    Subclases need to provide data functions to get the dataframes.
    """
    colormap = 'RdYlGn'
    vmin = 0
    vmax = 100
    xticklabels = 1
    yticklabels = 1
    XLABEL = "Sampled revisions"
    y_label = None

    def __init__(
        self, plot_config: PlotConfig,
        data_function: tp.Callable[[CaseStudy], DataFrame], **kwargs
    ):
        super().__init__(plot_config, **kwargs)
        self.color_commits = False
        self.data_function = data_function

    def plot(self, view_mode: bool) -> None:
        """Plot the heatmap."""
        style.use(self.plot_config.get_dict())
        _, axis = plt.subplots(1, 1)
        case_study = self.plot_kwargs['case_study']
        data = self.data_function(case_study)
        axis.set_title(case_study.project_name.capitalize())
        axis = sns.heatmap(
            data,
            cmap=self.colormap,
            vmin=self.vmin,
            vmax=self.vmax,
            xticklabels=self.xticklabels,
            yticklabels=self.yticklabels,
            linewidth=0.1,
            linecolor="grey"
        )
        if self.XLABEL:
            axis.set_xlabel(self.XLABEL)
        if self.y_label:
            axis.set_ylabel(self.y_label)
        if self.color_commits:
            color_map = get_author_color_map(data, case_study)
            commit_lookup_helper = create_commit_lookup_helper(
                case_study.project_name
            )
            repo = get_primary_project_source(case_study.project_name).local
            for label in axis.get_yticklabels():
                commit = commit_lookup_helper(
                    CommitRepoPair(FullCommitHash(label.get_text()), repo)
                )
                label.set(
                    color=color_map[commit.author.name],
                    text=label.get_text()[:ShortCommitHash.hash_length()] + " █"
                )
            legend = []
            for author, color in color_map.items():
                legend.append(mpatches.Patch(color=color, label=author))
            plt.legend(
                fontsize=8,
                handles=legend,
                bbox_to_anchor=(1.2, 0.5),
                loc=2,
                borderaxespad=0.
            )
        plt.setp(
            axis.get_xticklabels(),
            fontsize=self.plot_config.x_tick_size() - 1,
            family='monospace',
        )
        plt.setp(
            axis.get_yticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace'
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        """Calculate."""
        commit_map: CommitMap = get_commit_map(
            self.plot_kwargs['case_study'].project_name
        )

        def head_cm_neighbours(
            lhs_cm: ShortCommitHash, rhs_cm: ShortCommitHash
        ) -> bool:
            return commit_map.short_time_id(
                lhs_cm
            ) + 1 == commit_map.short_time_id(rhs_cm)

        new_revs: tp.Set[FullCommitHash] = set()

        data = self.data_function(self.plot_kwargs['case_study'])
        data.fillna(value=0, inplace=True)
        df_iter = data.items()
        last_revision, last_column = next(df_iter)
        for revision, column in df_iter:
            gradient = abs(column - last_column)
            if any(gradient > (boundary_gradient * 100)):
                lhs_cm = last_revision
                rhs_cm = revision
                if head_cm_neighbours(lhs_cm, rhs_cm):
                    print(
                        "Found steep gradient between neighbours " +
                        f"{lhs_cm} - {rhs_cm}: {round(max(gradient), 5)}"
                    )
                else:
                    print(
                        "Unusual gradient between " +
                        f"{lhs_cm} - {rhs_cm}: {round(max(gradient), 5)}"
                    )
                    new_rev_id = round((
                        commit_map.short_time_id(lhs_cm) +
                        commit_map.short_time_id(rhs_cm)
                    ) / 2.0)
                    new_rev = commit_map.c_hash(new_rev_id)
                    print(
                        f"-> Adding {new_rev} as new revision to the sample set"
                    )
                    new_revs.add(new_rev)
                print()
            last_revision = revision
            last_column = column
        return new_revs


class SurvivingInteractionsPlot(
    HeatMapPlot, plot_name="surviving_interactions_plot"
):
    """Plot the normalized evolution of commit interactions."""
    NAME = 'surviving_interactions_plot'
    YLABEL = "Surviving Interactions"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config, get_normalized_interactions_per_commit_wide, **kwargs
        )
        self.color_commits = True


class SurvivingLinesPlot(HeatMapPlot, plot_name="surviving_commit_plot"):
    """Plot the normalized evolution of LOC."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = 'surviving_lines_plot'
    y_label = "Surviving Lines"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(
            plot_config, get_normalized_lines_per_commit_wide, **kwargs
        )
        self.color_commits = True


class CompareSurvivalPlot(HeatMapPlot, plot_name="compare_survival"):
    """Plot the normalized evolution of commit interactions and LOC."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = 'compare_survival'

    y_label = "Commit Interactions vs. Lines"

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, lines_and_interactions, **kwargs)
        self.yticklabels = 3
        self.color_commits = True


class SingleCommitSurvivalPlotGenerator(
    PlotGenerator,
    generator_name="single-survival",
    options=[
        REQUIRE_CASE_STUDY,
        click.argument("revisions", nargs=-1, type=str)
    ]
):
    """Generator for the Plot of the evolution of a single commit."""

    def generate(self) -> tp.List['Plot']:

        return [
            SingleCommitPlot(
                self.plot_config, revision=revision, **self.plot_kwargs
            ) for revision in self.plot_kwargs['revisions']
        ]


class SurvivingCommitPlotGenerator(
    PlotGenerator,
    generator_name="commit-survival",
    options=[REQUIRE_CASE_STUDY]
):
    """Generator for the Plot of the evolution of all commits."""

    def generate(self) -> tp.List['Plot']:
        return [
            SurvivingInteractionsPlot(self.plot_config, **self.plot_kwargs),
            SurvivingLinesPlot(self.plot_config, **self.plot_kwargs),
            CompareSurvivalPlot(self.plot_config, **self.plot_kwargs)
        ]
