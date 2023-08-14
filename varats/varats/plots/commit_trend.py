import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import SymLogNorm
from pandas import DataFrame

from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.surviving_commits import (
    get_lines_per_commit_long,
    get_interactions_per_commit_long,
)
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    FullCommitHash,
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)


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
