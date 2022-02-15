import math
import typing as tp

import matplotlib.pyplot as plt
from pandas import DataFrame

from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator, REQUIRE_CASE_STUDY
from varats.plots.surviving_commits import (
    get_normalized_lines_per_commit_long,
    get_normalized_interactions_per_commit_long,
    get_interactions_per_commit_long,
    get_lines_per_commit_long,
)
from varats.utils.git_util import FullCommitHash


class CommitStructurePlot(Plot, plot_name='commit_structure'):

    NAME = 'commit_structure'

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        lines: DataFrame = get_lines_per_commit_long(case_study).rename(
            columns={'commit_hash': 'base_hash'}
        )

        interactions: DataFrame = get_interactions_per_commit_long(
            case_study
        ).rename(columns={'amount': 'interactions'})
        data = lines.merge(
            interactions, how='left', on=["base_hash", "revision"]
        )
        data.dropna(
            axis=0, how='any', inplace=True, subset=["lines", "interactions"]
        )
        data = data.apply(
            lambda x: [
                x['revision'], x['base_hash'], x['interactions'] / x['lines'],
                x['lines'] / x['interactions']
            ] if x['base_hash'].startswith(x['revision'].hash) else
            [math.nan, math.nan, math.nan, math.nan],
            axis=1,
            result_type='broadcast'
        )
        data.dropna(axis=0, how='any', inplace=True)
        print(data)
        _, axis = plt.subplots(1, 1)
        plt.setp(
            axis.get_xticklabels(), fontsize=self.plot_config.x_tick_size()
        )
        plt.setp(
            axis.get_yticklabels(), fontsize=self.plot_config.x_tick_size()
        )
        data.pivot(index="base_hash", columns="revision", values="lines").plot()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)


class CommitStructurePlotGenerator(
    PlotGenerator,
    generator_name="commit-structure",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        return [CommitStructurePlot(self.plot_config, **self.plot_kwargs)]
