"""Plot the performance evolution of a configurable software system."""
import ast
import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.stats import mannwhitneyu

from varats.data.databases.performance_evolution_database import (
    PerformanceEvolutionDatabase,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


def rrs(
    feature_matrix: pd.DataFrame,
    values: pd.Series,
    min_size: int = 10,
    significance_level: float = 0.01,
    min_effect_size: float = 0.8,
    max_depth: tp.Optional[int] = None
) -> tp.Set[str]:
    if max_depth is not None:
        max_depth -= 1
        if max_depth < 0:
            return set()

    relevant_features: tp.Set[str] = set()
    for feature in feature_matrix.columns:
        selected = values[feature_matrix[feature] == 1]
        deselected = values[feature_matrix[feature] == 0]
        if len(selected) < min_size or len(deselected) < min_size:
            continue

        U1, p = mannwhitneyu(selected, deselected)
        U2 = len(selected) * len(deselected) - U1

        # common language effect size
        e1 = U1 / (len(selected) * len(deselected))
        e2 = U2 / (len(selected) * len(deselected))

        if p < significance_level:
            if e1 >= min_effect_size or e2 >= min_effect_size:
                relevant_features.add(feature)

            relevant_features.update(
                rrs(
                    feature_matrix[feature_matrix[feature] == 1
                                  ].drop(feature, axis="columns"), selected,
                    min_size, significance_level, min_effect_size, max_depth
                )
            )
            relevant_features.update(
                rrs(
                    feature_matrix[feature_matrix[feature] == 0
                                  ].drop(feature, axis="columns"), deselected,
                    min_size, significance_level, min_effect_size, max_depth
                )
            )

    return relevant_features


def create_heatmap(
    case_study: CaseStudy, project_name: str, commit_map: CommitMap
) -> pd.DataFrame:
    df = PerformanceEvolutionDatabase.get_data_for_project(
        project_name, ["revision", "config_id", "wall_clock_time"],
        commit_map,
        case_study,
        cached_only=True
    )
    df["wall_clock_time"] = df["wall_clock_time"].apply(
        lambda x: np.average(ast.literal_eval(x))
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
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        return [
            PerformanceEvolutionDiffPlot(self.plot_config, **self.plot_kwargs)
        ]
