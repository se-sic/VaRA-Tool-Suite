import math
import typing as tp

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import style
from pandas import DataFrame

from varats.data.databases.blame_library_interactions_database import (
    BlameLibraryInteractionsDatabase,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig, REQUIRE_CASE_STUDY
from varats.project.project_util import get_local_project_git
from varats.utils.git_util import (
    ShortCommitHash,
    FullCommitHash,
    calc_surviving_lines,
)


def get_normalized_interactions_per_commit(case_study: CaseStudy) -> DataFrame:
    project_name = case_study.project_name
    data = BlameLibraryInteractionsDatabase().get_data_for_project(
        project_name, ["base_hash", "amount", "revision"],
        get_commit_map(project_name), case_study
    )
    data = data.groupby(["base_hash", "revision"], sort=False).sum()
    data_dict = data.to_dict()["amount"]
    base_interactions = {
        k1: v
        for ((k1, k2), v) in data_dict.items()
        if ShortCommitHash(k1) == k2
    }
    print(base_interactions)
    normalized_interactions_dict = {}
    for revision in case_study.revisions.__reversed__():
        normalized_interactions_dict[revision] = {
            k1: v / (
                base_interactions[k1]
                if base_interactions.__contains__(k1) else 1
            ) * 100
            for ((k1, k2), v) in data_dict.items()
            if k2 == revision.to_short_commit_hash()
        }
    return DataFrame(normalized_interactions_dict).transpose()


def get_normalized_locs_per_commit(case_study: CaseStudy) -> DataFrame:
    project_repo = get_local_project_git(case_study.project_name)
    starting_lines = {}
    data_dict = {}
    for revision in case_study.revisions.__reversed__():
        lines_per_revision = calc_surviving_lines(
            project_repo, revision, case_study.revisions
        )
        starting_lines[revision] = lines_per_revision[revision] \
            if lines_per_revision.__contains__(revision) else 1
        data_dict[revision] = {
            k.__str__():
            ((v / starting_lines[k]) * 100) if not math.isnan(v) else v
            for (k, v) in lines_per_revision.items()
            if case_study.revisions.__contains__(k)
        }
    return DataFrame(data_dict)


class SurvivingInteractionsPlot(Plot, plot_name="surviving_interactions_plot"):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = 'surviving_interactions_plot'

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(self.NAME, plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())
        _, axis = plt.subplots(1, 1)

        data = get_normalized_interactions_per_commit(
            self.plot_kwargs['case_study']
        )
        sns.heatmap(data, cmap='RdYlGn', vmin=0.1, vmax=100)
        plt.setp(
            axis.get_xticklabels(), fontsize=self.plot_config.x_tick_size()
        )


class SurvivingLinesPlot(Plot, plot_name="surviving_commit_plot"):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    NAME = 'surviving_commit_plot'

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(self.NAME, plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        style.use(self.plot_config.style())
        _, axis = plt.subplots(1, 1)

        data = get_normalized_locs_per_commit(self.plot_kwargs['case_study'])
        sns.heatmap(data, cmap='RdYlGn', vmin=0.1, vmax=100)
        plt.setp(
            axis.get_xticklabels(), fontsize=self.plot_config.x_tick_size()
        )


class SurvivingCommitPlotGenerator(
    PlotGenerator,
    generator_name="commit_survival",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        return [
            SurvivingInteractionsPlot(self.plot_config, **self.plot_kwargs),
            SurvivingLinesPlot(self.plot_config, **self.plot_kwargs)
        ]
