import typing as tp

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from pandas import DataFrame

from varats.data.databases.blame_library_interactions_database import (
    BlameLibraryInteractionsDatabase,
)
from varats.data.databases.survivng_lines_database import SurvivingLinesDatabase
from varats.mapping.commit_map import get_commit_map
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import FullCommitHash


class ProjectEvolutionPlot(Plot, plot_name='project_evolution'):

    NAME = 'project-evolution'

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs['case_study']
        project_name = case_study.project_name
        lines: DataFrame = SurvivingLinesDatabase.get_data_for_project(
            project_name, ["revision", "commit_hash", "lines"],
            get_commit_map(project_name), case_study
        ).rename(columns={'commit_hash': 'base_hash'})

        interactions: DataFrame = BlameLibraryInteractionsDatabase(
        ).get_data_for_project(
            project_name, ["base_hash", "amount", "revision", "base_lib"],
            get_commit_map(project_name), case_study
        ).rename(columns={'amount': 'interactions'})
        data = lines.merge(
            interactions, how='left', on=["base_hash", "revision"]
        )
        data.drop(['base_hash'], inplace=True, axis='columns')
        df: pd.DataFrame = data.groupby(by=['revision'], sort=False).sum()
        df.reset_index(inplace=True)
        print(df)
        _, axis = plt.subplots(1, 1)
        plt.setp(
            axis.get_xticklabels(), fontsize=self.plot_config.x_tick_size()
        )
        plt.setp(
            axis.get_yticklabels(), fontsize=self.plot_config.x_tick_size()
        )
        ax = axis.twinx()
        plt.setp(ax.get_yticklabels(), fontsize=self.plot_config.x_tick_size())
        x_axis = range(len(df))
        ax.scatter(x_axis, df['lines'], color="green")
        axis.scatter(x_axis, df['interactions'], color="orange")
        ax.set_ylim(ymin=0)
        axis.set_ylim(ymin=0)
        lines_legend = mpatches.Patch(color='green', label="Lines")
        interactions_legend = mpatches.Patch(
            color="orange", label='Interactions'
        )
        plt.legend(handles=[lines_legend, interactions_legend])
        plt.ticklabel_format(axis='x', useOffset=False)
        plt.xticks(x_axis, df['revision'])

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(plot_config, **kwargs)


class ProjectEvolutionPlotGenerator(
    PlotGenerator,
    generator_name="project-evolution",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['Plot']:
        return [ProjectEvolutionPlot(self.plot_config, **self.plot_kwargs)]
