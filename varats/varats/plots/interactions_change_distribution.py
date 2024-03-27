"""Plot the distributions of change in interactions and lines with commits as
units of space."""
import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.plots.commit_trend import (
    lines_per_interactions_squashed,
    lines_per_interactions_author,
)
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import FullCommitHash


class InteractionChangeDistribution(
    Plot, plot_name="interactions_change_distribution"
):
    """Plot the distributions of change in interactions of commits."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "base_hash": [],
            "interactions_diff": [],
            "project": []
        })
        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        for case_study in case_studys:
            cs_data = lines_per_interactions_squashed(case_study, True)
            cs_data["interactions_diff"] = cs_data.groupby(
                "base_hash", sort=False
            )["interactions"].diff().astype(float)
            cs_data.insert(2, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        data_sub = data.groupby(["base_hash", "project"],
                                sort=False)["interactions_diff"].max()

        df = data_sub.to_frame().reset_index()
        df["interactions_diff"] = df["interactions_diff"].apply(lambda x: x + 1)
        df.sort_values(by=["project"], inplace=True)
        df["project"] = df["project"].apply(lambda x: f"\\textsc{{{x}}}")
        axis = sns.violinplot(
            data=df,
            y="interactions_diff",
            x="project",
            bw=0.15,
            scale="width",
            inner=None,
            cut=0,
        )
        axis.plot(range(len(case_studys)), [1 for _ in case_studys], "--k")

        axis.set_ylabel(
            "Change in $\\frac{interactions}{lines}$",
            fontsize=self.plot_config.font_size
        )
        axis.set_xlabel("Projects", fontsize=self.plot_config.font_size)
        plt.gcf().set_size_inches(10, 5)
        plt.yscale("asinh")


class InteractionChangeAuthorDistribution(
    Plot, plot_name="interactions_change_distribution"
):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "author": [],
            "interactions_diff": [],
            "project": []
        })
        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        for case_study in case_studys:
            cs_data = lines_per_interactions_author(case_study)
            cs_data["interactions_diff"] = cs_data.groupby(
                "author", sort=False
            )["interactions"].diff().astype(float)
            cs_data.insert(
                2, "project", f"\\textsc{{{case_study.project_name}}}"
            )
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        data_sub = data.groupby(["author", "project"],
                                sort=False)["interactions_diff"].sum()
        df = data_sub.to_frame().reset_index()
        axis = sns.violinplot(
            data=df, y="interactions_diff", x="project", bw=0.1, scale="width"
        )
        plt.scale('asinh')
        axis.set_ylabel("Change in \\frac{interactions}{line}")
        axis.set_xlabel("Projects")


class InteractionChangeDistributionGenerator(
    PlotGenerator,
    generator_name="change-distribution",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        return [
            InteractionChangeDistribution(self.plot_config, **self.plot_kwargs),
            InteractionChangeAuthorDistribution(
                self.plot_config, **self.plot_kwargs
            )
        ]
