"""Plot the performance evolution of a configurable software system."""
import ast
import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import leaves_list, linkage, fcluster
from scipy.stats import mannwhitneyu

from varats.data.databases.performance_evolution_database import (
    PerformanceEvolutionDatabase,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)
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

    config_ids = case_study.get_config_ids_for_revision(case_study.revisions[0])
    df = df[df["config_id"].apply(lambda x: x in config_ids)]
    df["wall_clock_time"] = df["wall_clock_time"].apply(
        lambda x: np.average(ast.literal_eval(x))
    )

    def map_index(index: pd.Index) -> pd.Index:
        return pd.Index([commit_map.short_time_id(c) for c in index])

    heatmap = df.pivot_table(
        index="config_id",
        columns="revision",
        values="wall_clock_time",
        sort=False,
    )
    heatmap.sort_index(axis="columns", inplace=True, key=map_index)
    return heatmap


class PerformanceEvolutionPlot(Plot, plot_name="performance_evolution_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        heatmap = create_heatmap(case_study, project_name, commit_map)
        heatmap_linkage = linkage(
            heatmap,
            method="average",
            metric="cityblock",
            optimal_ordering=True
        )

        ax = sns.heatmap(
            heatmap.iloc[reversed(leaves_list(heatmap_linkage))],
            robust=True,
            cmap="plasma"
        )

        ax.set_title(f"Performance – {project_name}", fontsize=28)
        ax.set_xlabel("Revisions", fontsize=20)
        ax.set_ylabel("Configurations", fontsize=20)
        ax.tick_params(axis='x', labelsize=14)
        plt.setp(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            rotation_mode="anchor"
        )
        ax.set_yticks([])

        fig = ax.get_figure()
        fig.set_size_inches(20.92, 11.77)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerformanceEvolutionGenerator(
    PlotGenerator,
    generator_name="performance-evolution-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            PerformanceEvolutionPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]


class PerformanceEvolutionDiffPlot(
    Plot, plot_name="performance_evolution_diff_plot"
):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        project_name: str = case_study.project_name
        commit_map: CommitMap = get_commit_map(project_name)

        heatmap = create_heatmap(case_study, project_name, commit_map)
        heatmap_diff = heatmap.transpose().pct_change().transpose()
        heatmap_linkage = linkage(
            heatmap,
            method="average",
            metric="cityblock",
            optimal_ordering=True
        )

        # plot
        ax = sns.heatmap(
            heatmap_diff.iloc[reversed(leaves_list(heatmap_linkage))],
            cmap="vlag",
            center=0,
            robust=True
        )

        ax.set_title(f"Performance Differences – {project_name}", fontsize=28)
        ax.set_xlabel("Revisions", fontsize=20)
        ax.set_ylabel("Configurations", fontsize=20)
        xticklabels = ax.get_xticklabels()
        ax.set_xticks([x + 0.5 for x in ax.get_xticks()])
        ax.set_xticklabels(xticklabels)
        ax.tick_params(axis='x', labelsize=14)
        plt.setp(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            rotation_mode="anchor"
        )
        ax.set_yticks([])

        fig = ax.get_figure()
        fig.set_size_inches(20.92, 11.77)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerformanceEvolutionDiffGenerator(
    PlotGenerator,
    generator_name="performance-evolution-diff-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            PerformanceEvolutionDiffPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
