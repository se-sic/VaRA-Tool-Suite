import typing as tp

import matplotlib.pyplot as plt
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
)
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import FullCommitHash, ShortCommitHash


def lines_per_interactions(case_study: CaseStudy) -> DataFrame:
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
            x["lines"] / x["interactions"], x["interactions"] / x["lines"]
        ),
        axis=1,
        result_type='broadcast'
    )
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
            cmap.short_time_id(x["revision"]), x["author"], x["lines"] / x[
                "interactions"], x["interactions"] / x["lines"]
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


class Trendlines(Plot, plot_name=None):
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
        data = data.pivot(
            index="revision", columns=self.columns_label, values="interactions"
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
        sns.lineplot(data=data, ax=axis)
        axis.set_xlim(xmin, xmax)
        plt.ticklabel_format(axis='x', useOffset=False)
        axis.tick_params(axis="x", labelrotation=90)
        sns.move_legend(axis, "upper left", bbox_to_anchor=(1, 1))


class CommitTrendLines(Trendlines, plot_name="commit-trend-lines"):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions, "base_hash", **kwargs
        )


class AuthorTrendLines(Trendlines, plot_name="author-trend-lines"):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, lines_per_interactions_author, "author", **kwargs
        )


class TrendlinesPlotGenerator(
    PlotGenerator, generator_name="trend_lines", options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['Plot']:
        return [
            CommitTrendLines(self.plot_config, **self.plot_kwargs),
            AuthorTrendLines(self.plot_config, **self.plot_kwargs)
        ]
