import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import SymLogNorm
from pandas import DataFrame

from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.author_contribution_survival import (
    get_lines_per_author,
    get_interactions_per_author,
)
from varats.plots.surviving_commits import (
    get_normalized_lines_per_commit_long,
    get_normalized_interactions_per_commit_long,
    get_lines_per_commit_long,
    get_interactions_per_commit_long,
)
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.git_util import (
    FullCommitHash,
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)


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


def lines_per_interactions(case_study: CaseStudy, cs_filter=False) -> DataFrame:
    print("Getting Lines per commit")
    lines: DataFrame = get_lines_per_commit_long(case_study, cs_filter)
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


def lines_per_interactions_squashed(
    case_study: CaseStudy, cs_filter=False
) -> DataFrame:
    print("Getting Lines per commit")
    lines: DataFrame = get_lines_per_commit_long(case_study, cs_filter)
    print("Getting Interactions")
    interactions: DataFrame = get_interactions_per_commit_long(
        case_study, cs_filter
    )
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
    starting_ratio = data.drop_duplicates(['base_hash'], keep='first')
    starting_ratio.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    starting_ratio.set_index("base_hash", inplace=True)
    print("calculating lines/interaction")
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"], (x["interactions"] / x["lines"]) / (
                starting_ratio.loc[x["base_hash"]]["interactions"] /
                starting_ratio.loc[x["base_hash"]]["lines"]
            )
        ),
        axis=1,
        result_type='broadcast'
    )
    return data


def lines_per_interactions_squashed_with_threshold(
    case_study: CaseStudy
) -> DataFrame:
    data = lines_per_interactions_squashed(case_study)
    data_sub = data.groupby("base_hash", sort=False)["interactions"].diff()
    data_sub = data_sub.groupby("base_hash", sort=False)["interactions"].sum()
    print(data_sub)
    data = data[data["base_hash"].
                apply(lambda x: data_sub[x] > 0.5 or data_sub[x] < -0.5)]
    return data


def lines_per_interactions_author(
    case_study: CaseStudy, dummy=True
) -> DataFrame:
    lines: DataFrame = get_lines_per_author(case_study)
    interactions: DataFrame = get_interactions_per_author(case_study)
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
    data.sort_values(by="revision", inplace=False)
    print(data)
    starting_ratio = data.drop_duplicates(['author'], keep='first')
    starting_ratio.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    starting_ratio.set_index("author", inplace=False)
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
    data = lines_per_interactions_author(case_study)
    data["interactiosn_diff"] = data.groupby("author",
                                             sort=False)["interactions"].diff()
    print(data)
    data_sub = data.groupby("author", sort=False)["interactions_diff"].sum()

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
        fig, axis = plt.subplots(1, 1)
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
        # plt.yscale("symlog")
        sns.lineplot(data=data, ax=axis)
        axis.set_xlim(xmin, xmax)
        axis.tick_params(axis="x", labelrotation=90)
        axis.set_xlabel("Time")
        axis.set_ylabel("Interactions/LoC")
        plt.title(self.title + " " + case_study.project_name)
        sns.move_legend(axis, "upper left", bbox_to_anchor=(1, 1))
        # for line, name in zip(axis.lines, data.columns.tolist()):
        #     y = line.get_ydata()[-1]
        #     x = line.get_xdata()[-1]
        #     if not np.isfinite(y):
        #         y = next(reversed(line.get_ydata()[~line.get_ydata().mask]),
        #                  float("nan"))
        #     if not np.isfinite(y) or not np.isfinite(x):
        #         continue
        #     text = axis.annotate(name,
        #                        xy=(x, y),
        #                        xytext=(0, 0),
        #                        color=line.get_color(),
        #                        xycoords=(axis.get_xaxis_transform(),
        #                                  axis.get_yaxis_transform()),
        #                        textcoords="offset points")
        #     text_width = (text.get_window_extent(
        #         fig.canvas.get_renderer()).transformed(
        #         axis.transData.inverted()).width)
        #     if np.isfinite(text_width):
        #         axis.set_xlim(axis.get_xlim()[0], text.xy[0] + text_width * 1.05)


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
            size="lines",
            hue=self.columns_label,
            style=self.columns_label
        )
        axis.set_xlim(xmin, xmax)
        plt.ticklabel_format(axis='x', useOffset=False)
        axis.tick_params(axis="x", labelrotation=90)
        axis.set_xlabel("Time")
        axis.set_ylabel("Interactions/LoC")
        sns.move_legend(axis, "upper left", bbox_to_anchor=(1, 1))
        plt.title(case_study.project_name + " " + self.NAME)


class ChangesHeatMap(Plot, plot_name=None):
    """plot trendlines."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        cs_data = self.data_function(case_study, False)
        cs_data["interactions_diff"] = \
        cs_data.groupby(self.columns_label, sort=False)[
            self.value_label].diff().astype(float)
        if self.value_label == "lines":
            vmin = cs_data["interactions_diff"].min()
            vmax = 0
        else:
            vmax = max(
                cs_data["interactions_diff"].max(),
                -cs_data["interactions_diff"].min()
            )
            vmin = -vmax
        cs_data.drop(
            cs_data[cs_data[self.columns_label] ==
                    UNCOMMITTED_COMMIT_HASH.to_short_commit_hash()].index,
            inplace=True
        )

        cs_data = cs_data.pivot(
            index=self.columns_label,
            columns="revision",
            values="interactions_diff"
        )
        cmap = get_commit_map(case_study.project_name)
        if self.columns_label == "base_hash":
            cs_data.sort_index(
                key=lambda x: x.map(cmap.short_time_id), inplace=True
            )
        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        axis = sns.heatmap(
            cs_data,
            center=0,
            cmap="RdYlGn",
            vmax=vmax,
            vmin=vmin,
            norm=SymLogNorm(linthresh=0.01, vmax=vmax, vmin=vmin)
        )
        plt.setp(
            axis.get_yticklabels(),
            family='monospace',
        )
        new_labels = [
            f"\\texttt{{{i.get_text()[0:5]}}}"
            if len(i.get_text()) > 5 else i.get_text()
            for i in axis.yaxis.get_ticklabels()
        ]
        axis.set_yticklabels(new_labels)
        axis.set_ylabel("Commits")
        axis.set_xlabel("Revisions")
        axis.set_xticklabels([])

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(
        self,
        plot_config: PlotConfig,
        data_function,
        columns_label="base_hash",
        value_label="interactions",
        **kwargs
    ):
        super().__init__(plot_config, **kwargs)
        self.color_commits = False
        self.data_function = data_function
        self.columns_label = columns_label
        self.value_label = value_label


def interactions_and_lines_per_commit_wrapper(
    case_study: CaseStudy, cs_filter=True
):
    print(f"Getting Lines per commit for {case_study.project_name}")
    lines: DataFrame = get_lines_per_commit_long(case_study, cs_filter)
    print("Getting Interactions")
    interactions: DataFrame = get_interactions_per_commit_long(
        case_study, cs_filter
    )
    print("Merging")
    data = lines.merge(interactions, how='right', on=["base_hash", "revision"])
    data.dropna(
        axis=0, how='any', inplace=True, subset=["lines", "interactions"]
    )
    cmap = get_commit_map(case_study.project_name)
    data = data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"], x["interactions"]
        ),
        axis=1,
        result_type="broadcast"
    )
    return data.sort_values(by="revision")


class InteractionChangeHeatmap(
    ChangesHeatMap, plot_name="interactions-change-heatmap"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config, interactions_and_lines_per_commit_wrapper, **kwargs
        )


class LineChangeHeatmap(ChangesHeatMap, plot_name="line-change-heatmap"):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config,
            interactions_and_lines_per_commit_wrapper,
            value_label="lines",
            **kwargs
        )


class InteractionPerLineChangeHeatmap(
    ChangesHeatMap, plot_name="interactions-per-line-change-heatmap"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(plot_config, lines_per_interactions_squashed, **kwargs)


class InteractionPerLineChangeAuthorHeatmap(
    ChangesHeatMap, plot_name="interactions-per-line-change-heatmap"
):

    def __init__(self, plot_config: PlotConfig, **kwargs):
        super().__init__(
            plot_config,
            lines_per_interactions_author,
            columns_label="author",
            **kwargs
        )


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
            plot_config, lines_per_interactions_squashed, "base_hash",
            "Changes to Interactions / LoC", **kwargs
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
            CommitTrendLinesSquashed(self.plot_config, **self.plot_kwargs),
            CommitInteractionsTrendLines(self.plot_config, **self.plot_kwargs),
            CommitTrendLinesNormalized(self.plot_config, **self.plot_kwargs),
            CommitTrendLines(self.plot_config, **self.plot_kwargs),
            AuthorTrendLines(self.plot_config, **self.plot_kwargs),
            # AuthorTrendLinesSquashed(self.plot_config, **self.plot_kwargs),
        ]


class ChangesMapGenerator(
    PlotGenerator,
    generator_name="change-map",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['Plot']:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        plots: tp.List[Plot] = []
        for case_study in case_studys:
            kwargs = self.plot_kwargs.copy()
            kwargs["case_study"] = case_study
            plots.append(InteractionChangeHeatmap(self.plot_config, **kwargs))
            plots.append(LineChangeHeatmap(self.plot_config, **kwargs))
        return plots
