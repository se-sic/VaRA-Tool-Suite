import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pandas import DataFrame

from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.author_contribution_survival import (
    get_lines_per_author_normalized_per_revision,
    get_interactions_per_author_normalized_per_revision,
)
from varats.plots.surviving_commits import (
    get_normalized_lines_per_commit_long,
    get_normalized_interactions_per_commit_long,
    get_lines_per_commit_long,
    get_interactions_per_commit_long,
)
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import FullCommitHash, ShortCommitHash


def lines_per_interactions_normalized(case_study: CaseStudy) -> DataFrame:
    print("Getting Lines per commit")
    lines: DataFrame = get_normalized_lines_per_commit_long(case_study, False)
    print("Getting Interactions")
    interactions: DataFrame = get_normalized_interactions_per_commit_long(
        case_study, False
    )
    print("Merging")
    data = lines.merge(interactions, how='left', on=["base_hash", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    print("calculating lines/interaction")
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"], x["interactions"] / x["lines"]
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions(case_study: CaseStudy) -> DataFrame:
    print("Getting Lines per commit")
    lines: DataFrame = get_lines_per_commit_long(case_study, False)
    print("Getting Interactions")
    interactions: DataFrame = get_interactions_per_commit_long(
        case_study, False
    )
    print("Merging")
    data = lines.merge(interactions, how='left', on=["base_hash", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    print("calculating lines/interaction")
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"], x["interactions"] / x["lines"]
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions_squashed(case_study: CaseStudy) -> DataFrame:
    print("Getting Lines per commit")
    lines: DataFrame = get_lines_per_commit_long(case_study, True)
    print("Getting Interactions")
    interactions: DataFrame = get_interactions_per_commit_long(case_study, True)
    print("Merging")
    data = lines.merge(interactions, how='left', on=["base_hash", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    cmap = get_commit_map(case_study.project_name)
    data.sort_values(
        by="revision",
        key=lambda col: col.map(cmap.short_time_id),
        inplace=True
    )
    print(data)
    starting_ratio = data.drop_duplicates(['base_hash'], keep='first')
    starting_ratio.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    starting_ratio.set_index("base_hash", inplace=True)
    print("calculating lines/interaction")
    print(starting_ratio)
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"], (x["interactions"] / x["lines"]) / (
                starting_ratio.loc[x["base_hash"]]["interactions"] /
                starting_ratio.loc[x["base_hash"]]["lines"]
            ) - 1
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions_squashed_with_threshold(
    case_study: CaseStudy
) -> DataFrame:
    data = lines_per_interactions_squashed(case_study)
    data_sub = data.groupby(
        "base_hash", sort=False
    )["interactions"].agg(lambda x: x.drop_duplicates().sum())
    print(data_sub)
    data = data[data["base_hash"].
                apply(lambda x: data_sub[x] > 0.5 or data_sub[x] < -0.5)]
    print(data)
    return data


def lines_per_interactions_author(case_study: CaseStudy) -> DataFrame:
    lines: DataFrame = get_lines_per_author_normalized_per_revision(case_study)
    interactions: DataFrame = get_interactions_per_author_normalized_per_revision(
        case_study
    )
    data = lines.merge(interactions, how='left', on=["author", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    print("calculating lines/interaction")
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), x["author"], x["lines"], x[
                "interactions"] / x["lines"]
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions_author_squashed(case_study: CaseStudy) -> DataFrame:
    data = lines_per_interactions_author(case_study)
    data.sort_values(by="revision", inplace=True)
    print(data)
    starting_ratio = data.drop_duplicates(['author'], keep='first')
    starting_ratio.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    starting_ratio.set_index("author", inplace=True)
    print("calculating lines/interaction")
    print(starting_ratio)
    data = data.apply(
        lambda x: (
            x["revision"], ShortCommitHash(x["author"]), x["lines"], (
                x["interactions"] / starting_ratio.loc[x["author"]][
                    "interactions"]
            ) - 1
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions_author_with_threshold(
    case_study: CaseStudy
) -> DataFrame:
    data = lines_per_interactions_author_squashed(case_study)
    data_sub = data.groupby(
        "author", sort=False
    )["interactions"].agg(lambda x: x.drop_duplicates().sum())
    print(data_sub)
    data = data[
        data["author"].apply(lambda x: data_sub[x] > 0.5 or data_sub[x] < -0.5)]
    print(data)
    return data


def interaction_trend(case_study: CaseStudy):
    data = get_interactions_per_commit_long(case_study, False)
    cmap = get_commit_map(case_study.project_name)
    print(data)
    return data.apply(
        lambda x:
        (x["base_hash"], cmap.short_time_id(x["revision"]), x["interactions"]),
        axis=1,
        result_type='broadcast'
    )


class Trendlines(Plot, plot_name=None):
    """plot trendlines."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(
        self,
        plot_config: PlotConfig,
        data_function: tp.Callable[[CaseStudy], DataFrame],
        columns_label: str,
        title: str = "",
        **kwargs
    ):
        super().__init__(plot_config, **kwargs)
        self.color_commits = False
        self.data_function = data_function
        self.columns_label = columns_label
        self.title = title

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        data = self.data_function(case_study)
        xmin, xmax = data["revision"].min(), data["revision"].max()
        print(data)
        data = data.pivot(
            index="revision",
            columns=self.columns_label,
            values="interactions",
        )
        data.sort_index(axis=0, inplace=True)
        _, axis = plt.subplots(1, 1)
        print("Plotting")
        plt.setp(
            axis.get_xticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace',
        )
        plt.setp(
            axis.get_yticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace'
        )
        plt.yscale("symlog")
        sns.lineplot(data=data, ax=axis, legend=False)
        axis.set_xlim(xmin, xmax)
        axis.tick_params(axis="x", labelrotation=90)
        axis.set_xlabel("Time")
        axis.set_ylabel("Interactions/LoC")
        plt.title(self.title + " " + case_study.project_name)


class TrendlinesWide(Plot, plot_name=None):
    """plot trendlines."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(
        self, plot_config: PlotConfig, data_function: tp.Callable[[CaseStudy],
                                                                  DataFrame],
        columns_label: str, **kwargs
    ):
        super().__init__(plot_config, **kwargs)
        self.color_commits = False
        self.data_function = data_function
        self.columns_label = columns_label

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        data = self.data_function(case_study)
        xmin, xmax = data["revision"].min(), data["revision"].max()
        _, axis = plt.subplots(1, 1)
        print("Plotting")
        plt.setp(
            axis.get_xticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace',
        )
        plt.setp(
            axis.get_yticklabels(),
            fontsize=self.plot_config.x_tick_size(),
            family='monospace'
        )
        sns.lineplot(
            data=data,
            x="revision",
            y="interactions",
            ax=axis,
            legend=None,
            size="lines",
            hue=self.columns_label,
            style=self.columns_label
        )
        axis.set_xlim(xmin, xmax)
        plt.ticklabel_format(axis='x', useOffset=False)
        axis.tick_params(axis="x", labelrotation=90)
        axis.set_xlabel("Time")
        axis.set_ylabel("Interactions/LoC")
        plt.title(case_study.project_name + " " + self.NAME)


class CommitTrendLinesNormalized(
    Trendlines, plot_name="commit-trend-lines-normalized"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions_normalized, "base_hash",
            "Interactions/LoC Normalized", **kwargs
        )


class CommitTrendLinesSquashed(
    Trendlines, plot_name="commit-trend-lines-squashed"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions_squashed_with_threshold,
            "base_hash", "Changes to Interactions / LoC", **kwargs
        )


class CommitInteractionsTrendLines(
    Trendlines, plot_name="commit-interaction-trend-lines"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, interaction_trend, "base_hash", "Interactions",
            **kwargs
        )


class CommitTrendLines(Trendlines, plot_name="commit-trend-lines"):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions, "base_hash",
            "Interactions per LoC", **kwargs
        )


class AuthorTrendLines(Trendlines, plot_name="author-trend-lines-normalized"):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions_author, "author", **kwargs
        )


class AuthorTrendLinesSquashed(
    Trendlines, plot_name="author-trend-lines-squashed"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions_author_with_threshold, "author",
            **kwargs
        )


class TrendlinesPlotGenerator(
    PlotGenerator, generator_name="trend_lines", options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['Plot']:
        return [
            #CommitTrendLinesSquashed(self.plot_config, **self.plot_kwargs),
            #CommitInteractionsTrendLines(self.plot_config, **self.plot_kwargs),
            #CommitTrendLinesNormalized(self.plot_config, **self.plot_kwargs),
            #CommitTrendLines(self.plot_config, **self.plot_kwargs),
            #AuthorTrendLines(self.plot_config, **self.plot_kwargs),
            AuthorTrendLinesSquashed(self.plot_config, **self.plot_kwargs),
        ]
