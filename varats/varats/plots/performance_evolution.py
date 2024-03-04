"""Plot the performance evolution of a configurable software system."""

import typing as tp

import pandas as pd
import scipy
import seaborn as sns

from varats.base.configuration import PlainCommandlineConfiguration
from varats.data.databases.performance_evolution_database import (
    PerformanceEvolutionDatabase,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


def create_heatmap(
    case_study: CaseStudy, project_name: str, commit_map: CommitMap
) -> pd.DataFrame:
    df = PerformanceEvolutionDatabase.get_data_for_project(
        project_name, ["revision", "config_id", "wall_clock_time"],
        commit_map,
        case_study,
        cached_only=True
    )

    def map_index(index: pd.Index) -> pd.Index:
        return pd.Index([commit_map.short_time_id(c) for c in index])

    heatmap = df.pivot(
        index="config_id", columns="revision", values="wall_clock_time"
    )
    heatmap.sort_index(axis="columns", inplace=True, key=map_index)
    return heatmap


class PerformanceEvolutionPlot(Plot, plot_name="performance_evolution_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        heatmap = create_heatmap(case_study, project_name, commit_map)
        ax = sns.heatmap(heatmap)
        ax.set_title(
            self.plot_config.fig_title("Performance Evolution Heatmap")
        )
        fig = ax.get_figure()
        fig.set_size_inches(20, 20)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerformanceEvolutionGenerator(
    PlotGenerator,
    generator_name="performance-evolution-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        return [PerformanceEvolutionPlot(self.plot_config, **self.plot_kwargs)]


class PerformanceEvolutionDiffPlot(
    Plot, plot_name="performance_evolution_diff_plot"
):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        heatmap = create_heatmap(case_study, project_name, commit_map)
        heatmap_diff = heatmap.diff(axis="columns")

        configs = load_configuration_map_for_case_study(
            get_paper_config(), case_study, PlainCommandlineConfiguration
        )
        config_flags = []
        for id, config in configs.id_config_tuples():
            for flag in config.options():
                config_flags.append({"id": id, "flag": flag.name})
        df = pd.DataFrame(config_flags)
        feature_matrix = pd.crosstab(df["id"], df["flag"])
        linkage = scipy.cluster.hierarchy.linkage(
            feature_matrix, method="average", optimal_ordering=True
        )

        # ax = sns.heatmap(heatmap_diff, cmap="vlag", center=0, robust=True)
        grid = sns.clustermap(
            heatmap_diff,
            row_linkage=linkage,
            col_cluster=False,
            cmap="vlag",
            center=0,
            robust=True
        )
        # grid.legend.set(loc="right")
        fig = grid.figure
        fig.set_size_inches(30, 20)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerformanceEvolutionDiffGenerator(
    PlotGenerator,
    generator_name="performance-evolution-diff-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        return [
            PerformanceEvolutionDiffPlot(self.plot_config, **self.plot_kwargs)
        ]
