"""Plots for the impact of revisions."""
import typing as tp

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from varats.data.metrics import apply_tukeys_fence
from varats.mapping.author_map import generate_author_map
from varats.mapping.commit_map import get_commit_map, CommitMap
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.commit_trend import interactions_and_lines_per_commit_wrapper
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.plots.surviving_commits import get_lines_per_commit_long
from varats.project.project_util import get_primary_project_source
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    ShortCommitHash,
    FullCommitHash,
    create_commit_lookup_helper,
    CommitRepoPair,
)


def revision_impact(case_study: CaseStudy) -> pd.DataFrame:
    """Returns a dataframe with the impact of each revision of a single
    case_study."""
    interaction_data = interactions_and_lines_per_commit_wrapper(
        case_study, False
    )
    interaction_data["interactions_diff"] = \
        interaction_data.groupby("base_hash", sort=False)[
            "interactions"].diff().astype(float)
    interaction_data["lines_diff"] = \
        interaction_data.groupby("base_hash", sort=False)[
            "lines"].diff().astype(float)
    interaction_data.drop(columns=["base_hash"], inplace=True)
    interaction_data["interactions_diff"] = interaction_data["interactions_diff"
                                                            ].abs()
    interaction_data["lines_diff"] = interaction_data["lines_diff"].abs()
    data = interaction_data.groupby("revision").agg({
        "interactions": "sum",
        "interactions_diff": "sum",
        "lines_diff": "sum",
        "lines": "sum"
    })
    data["interaction_change"
        ] = data["interactions_diff"] / data["interactions"]
    data["line_change"] = data["lines_diff"] / data["lines"]
    impacted = pd.NamedAgg(
        column="interactions_diff",
        aggfunc=lambda column: column[column > 1].count() / column.count()
    )
    data["impacted_commits"] = interaction_data.groupby("revision").agg(
        impacted_commits=impacted
    )["impacted_commits"]
    return data.reset_index().astype(float)


def impact_data(case_studys: tp.List[CaseStudy]) -> pd.DataFrame:
    """Returns a dataframe with the impact of each revision of a list of
    case_studies."""
    data = pd.DataFrame({
        "revision": [],
        "interactions": [],
        "interactions_diff": [],
        "interaction_change": [],
        "lines": [],
        "lines_diff": [],
        "line_change": [],
        "impacted_commits": [],
        "project": [],
    })
    for case_study in case_studys:
        cs_data = revision_impact(case_study)
        cs_data.insert(1, "project", case_study.project_name)
        data = pd.concat([data, cs_data],
                         ignore_index=True,
                         copy=False,
                         join="inner")
    return data


def calc_missing_revisions_impact(
    case_studys: tp.List[CaseStudy], boundary_gradient: float
) -> tp.Set[FullCommitHash]:
    commit_map: CommitMap = get_commit_map(case_studys[0].project_name)

    def head_cm_neighbours(lhs_cm: int, rhs_cm: int) -> bool:
        return lhs_cm + 1 == rhs_cm

    new_revs: tp.Set[FullCommitHash] = set()

    data = impact_data(case_studys)
    data.fillna(value=0, inplace=True)
    df_iter = data.iterrows()
    _, last_row = next(df_iter)
    for _, row in df_iter:
        change = row["impacted_commits"]
        if change > (boundary_gradient):
            lhs_cm = last_row["revision"]
            rhs_cm = row["revision"]
            if head_cm_neighbours(lhs_cm, rhs_cm):
                print(
                    "Found steep gradient between neighbours " +
                    f"{lhs_cm} - {rhs_cm}: {round(change, 5)}"
                )
            else:
                print(
                    "Unusual gradient between " +
                    f"{lhs_cm} - {rhs_cm}: {round(change, 5)}"
                )
                new_rev_id = round((lhs_cm + rhs_cm) / 2.0)
                new_rev = commit_map.c_hash(new_rev_id)
                print(f"-> Adding {new_rev} as new revision to the sample set")
                new_revs.add(new_rev)
            print()
        last_row = row
    print(new_revs)
    return new_revs


class RevisionImpactDistribution(
    Plot, plot_name="revision_impact_distribution"
):
    """Plots the distribution of the impact of each revision of a single of
    case_study."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        data = self.plot_kwargs["data"]
        full_data = self.plot_kwargs["data"].copy()
        full_data["project"] = "All"
        data["project"] = data["project"].apply(lambda x: f"\\textsc{{{x}}}")
        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        grid = sns.JointGrid(
            x="project",
            y="impacted_commits",
            data=data,
        )

        sns.violinplot(
            ax=grid.ax_joint,
            data=data,
            y="impacted_commits",
            x="project",
            bw=0.15,
            scale="width",
            inner=None,
            cut=0
        )
        sns.kdeplot(
            ax=grid.ax_marg_y,
            data=full_data,
            y="impacted_commits",
            bw=0.15,
            cut=0,
            fill=True,
        )
        grid.set_axis_labels("Projects", "Impact", fontsize=14)
        plt.gcf().set_size_inches(10, 5)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)


class RevisionImpactDistributionAll(
    Plot, plot_name="revision_impact_distribution_all"
):
    """Plots the distribution of the impact of each revision of a list of
    case_studies."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        data = self.plot_kwargs["data"]
        data.drop(columns=["project"], inplace=True)
        sns.violinplot(data=data, y="impacted_commits", bw=0.15, cut=0)
        plt.ylabel("Impact", fontsize=10)


class RevisionImpactScatterInteractions(
    Plot, plot_name="revision_impact_interactions"
):
    """Plots the impact of each revision compared to its interaction change of a
    list of case_studies."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return calc_missing_revisions_impact(
            self.plot_kwargs["case_study"], boundary_gradient
        )

    def plot(self, view_mode: bool) -> None:
        data = self.plot_kwargs["data"]
        multivariate_grid(
            data, "impacted_commits", "interaction_change", "project"
        )
        ymax = data["interaction_change"].max()
        plt.ylim(-0.001, ymax + 0.01)


class RevisionImpactScatterLines(Plot, plot_name="revision_impact_lines"):
    """Plots the impact of each revision compared to its line change of a list
    of case_studies."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return calc_missing_revisions_impact(
            self.plot_kwargs["case_study"], boundary_gradient
        )

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = self.plot_kwargs["data"]
        data.fillna(value=0, inplace=True)
        if len(case_studys) == 1:
            data = data.loc[data["project"] == case_studys[0].project_name]
            cmap = get_commit_map(case_studys[0].project_name)
            commit_helper = create_commit_lookup_helper(
                case_studys[0].project_name
            )
            repo = get_primary_project_source(case_studys[0].project_name).local
            amap = generate_author_map(case_studys[0].project_name)
            data["project"] = data["revision"].apply(
                lambda x: amap.get_author_by_name(
                    commit_helper(CommitRepoPair(cmap.c_hash(x), repo)).author.
                    name
                )
            )
        data = apply_tukeys_fence(data, "line_change", 3)
        data["project"] = data["project"].apply(lambda x: f"\\textsc{{{x}}}")

        plt.rcParams.update({"text.usetex": True, "font.family": "Helvetica"})
        grid = multivariate_grid(
            data,
            "impacted_commits",
            "line_change",
            "project",
        )
        grid.set_axis_labels("Impact", "Changed Lines", fontsize=10)
        plt.gcf().set_size_inches(10, 5)
        ymax = data["line_change"].max()
        plt.ylim(-0.001, ymax + 0.01)


class RevisionImpactGenerator(
    PlotGenerator,
    generator_name="revision-impact",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        make_cli_option("--individual", type=bool, default=False, is_flag=True)
    ]
):
    """Generates a plot that shows the impact of each revision of a list of
    case_studies."""

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        plots: tp.List[Plot] = []
        self.plot_kwargs["data"] = impact_data(case_studys)
        if self.plot_kwargs["individual"]:
            for case_study in case_studys:
                kwargs = self.plot_kwargs.copy()
                kwargs["case_study"] = [case_study]
                plots.append(
                    RevisionImpactScatterLines(self.plot_config, **kwargs)
                )

        plots.append(
            RevisionImpactScatterLines(self.plot_config, **self.plot_kwargs)
        )
        plots.append(
            RevisionImpactDistribution(self.plot_config, **self.plot_kwargs)
        )
        plots.append(
            RevisionImpactDistributionAll(self.plot_config, **self.plot_kwargs)
        )
        return plots
