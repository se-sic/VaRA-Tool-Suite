import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns
from pandas import DataFrame

from varats.mapping.commit_map import get_commit_map
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.surviving_commits import (
    get_normalized_lines_per_commit_long,
    get_normalized_interactions_per_commit_long,
)
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import FullCommitHash, ShortCommitHash


class Trendlines(Plot, plot_name="survival_trendlines"):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        lines: DataFrame = get_normalized_lines_per_commit_long(
            case_study, False
        )

        interactions: DataFrame = get_normalized_interactions_per_commit_long(
            case_study, False
        )
        data = lines.merge(
            interactions, how='left', on=["base_hash", "revision"]
        )
        data.dropna(
            axis=0, how='any', inplace=True, subset=["lines", "interactions"]
        )
        cmap = get_commit_map(case_study.project_name)
        data = data.apply(
            lambda x: (
                cmap.short_time_id(x["revision"]),
                ShortCommitHash(x["base_hash"]), x["lines"] / x["interactions"],
                x["interactions"] / x["lines"]
            ),
            axis=1,
            result_type='broadcast'
        )
        xmin, xmax = data["revision"].min(), data["revision"].max()
        data = data.pivot(
            index="revision", columns="base_hash", values="interactions"
        )
        data.sort_index(axis=0, inplace=True)
        _, axis = plt.subplots(1, 1)
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
        print(data)
        sns.lineplot(data=data, ax=axis)
        axis.set_xlim(xmin, xmax)
        plt.ticklabel_format(axis='x', useOffset=False)
        axis.tick_params(axis="x", labelrotation=90)


class TrendlinesPlotGenerator(
    PlotGenerator, generator_name="trend_lines", options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['Plot']:
        return [Trendlines(self.plot_config, **self.plot_kwargs)]
