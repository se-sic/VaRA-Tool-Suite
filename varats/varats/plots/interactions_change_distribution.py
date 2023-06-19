import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import colors

from varats.mapping.commit_map import get_commit_map, CommitMap
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.commit_trend import (
    lines_per_interactions_squashed,
    lines_per_interactions,
    lines_per_interactions_author,
    interactions_per_commit_wrapper,
    lines_per_commit_wrapper,
)
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.plots.surviving_commits import get_lines_per_commit_long
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import FullCommitHash, ShortCommitHash


def revision_impact(case_study: CaseStudy) -> pd.DataFrame:
    interaction_data = interactions_per_commit_wrapper(case_study, False)
    lines_data = get_lines_per_commit_long(case_study, False)
    cmap = get_commit_map(case_study.project_name)
    lines_data = lines_data.apply(
        lambda x: (
            cmap.short_time_id(x["revision"]), ShortCommitHash(x["base_hash"]),
            x["lines"]
        ),
        axis=1,
        result_type="broadcast"
    )
    lines_data.sort_values(by="revision", inplace=True)
    interaction_data["interactions_diff"] = \
        interaction_data.groupby("base_hash", sort=False)[
            "interactions"].diff().astype(float)
    interaction_data["lines_diff"] = \
        lines_data.groupby("base_hash", sort=False)[
            "lines"].diff().astype(float)
    interaction_data["lines"] = lines_data["lines"]
    interaction_data.drop(columns=["base_hash"], inplace=True)
    interaction_data["interactions_diff"] = interaction_data["interactions_diff"
                                                            ].abs()
    interaction_data["lines_diff"] = interaction_data["lines_diff"].abs()
    data = interaction_data.groupby("revision").agg({
        "interactions": "sum",
        "interactions_diff": "sum",
        "lines_diff": "sum"
    })
    data["lines"] = lines_data.groupby("revision").agg({"lines": "sum"}
                                                      )["lines"]
    data["interaction_change"
        ] = data["interactions_diff"] / data["interactions"]
    print(data)
    data["line_change"] = data["lines_diff"] / data["lines"]
    impacted = pd.NamedAgg(
        column="interactions_diff",
        aggfunc=lambda column: column[column > 1].count() / column.count()
    )
    data["impacted_commits"] = interaction_data.groupby("revision").agg(
        impacted_commits=impacted
    )["impacted_commits"]
    return data.reset_index().astype(float)


class RevisionImpactDistribution(
    Plot, plot_name="revision_impact_distribution"
):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "revision": [],
            "interaction_change": [],
            "project": []
        })
        for case_study in case_studys:
            cs_data = revision_impact(case_study)
            print(cs_data)
            cs_data.insert(1, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        print(data)
        axis = sns.violinplot(data=data, y="change", x="project", bw=0.15)
        axis.plot(range(len(case_studys)), [0 for _ in case_studys], "--k")
        #divnorm = colors.TwoSlopeNorm(vmin=-1,vcenter=0,vmax=df["interactions_diff"].max())
        #plt.yscale("asinh")


def impact_data(case_studys: tp.List[CaseStudy]):
    data = pd.DataFrame({
        "revision": [],
        "interaction_change": [],
        "line_change": [],
        "impacted_commits": [],
        "project": []
    })
    for case_study in case_studys:
        cs_data = revision_impact(case_study)
        cs_data.insert(1, "project", case_study.project_name)
        data = pd.concat([data, cs_data],
                         ignore_index=True,
                         copy=False,
                         join="inner")
    return data


class RevisionImpactScatterInteractions(
    Plot, plot_name="revision_impact_interactions"
):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        commit_map: CommitMap = get_commit_map(
            self.plot_kwargs['case_study'][0].project_name
        )

        def head_cm_neighbours(lhs_cm: int, rhs_cm: int) -> bool:
            return lhs_cm + 1 == rhs_cm

        new_revs: tp.Set[FullCommitHash] = set()

        data = impact_data(self.plot_kwargs['case_study'])
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
                    print(
                        f"-> Adding {new_rev} as new revision to the sample set"
                    )
                    new_revs.add(new_rev)
                print()
            last_row = row
        return new_revs

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = impact_data(case_studys)
        multivariate_grid(
            data, "impacted_commits", "interaction_change", "project"
        )
        ymax = data["interaction_change"].max()
        plt.ylim(-0.01, ymax + 0.01)


class RevisionImpactScatterLines(Plot, plot_name="revision_impact_lines"):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = impact_data(case_studys)
        multivariate_grid(data, "impacted_commits", "line_change", "project")
        ymax = data["line_change"].max()
        plt.ylim(-0.01, ymax + 0.01)


class RevisionImpactScatter(Plot, plot_name="revision_impact"):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "revision": [],
            "interaction_change": [],
            "line_change": [],
            "impacted_commits": [],
            "project": []
        })
        for case_study in case_studys:
            cs_data = revision_impact(case_study)
            cs_data.insert(1, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        print(data)
        multivariate_grid(data, "impacted_commits", "change", "project")


class InteractionChangeDistribution(
    Plot, plot_name="interactions_change_distribution"
):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "base_hash": [],
            "interactions_diff": [],
            "project": []
        })
        for case_study in case_studys:
            cs_data = lines_per_interactions_squashed(case_study, True)
            cs_data["interactions_diff"] = cs_data.groupby(
                "base_hash", sort=False
            )["interactions"].diff().astype(float)
            print(cs_data)
            cs_data.insert(2, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        print(data)
        data_sub = data.groupby(["base_hash", "project"],
                                sort=False)["interactions_diff"].sum()

        print(data_sub)
        df = data_sub.to_frame().reset_index()
        df["interactions_diff"] = df["interactions_diff"].apply(lambda x: x + 1)
        print(df.dtypes)
        axis = sns.violinplot(
            data=df, y="interactions_diff", x="project", bw=0.15
        )
        axis.plot(range(len(case_studys)), [1 for _ in case_studys], "--k")
        #divnorm = colors.TwoSlopeNorm(vmin=-1,vcenter=0,vmax=df["interactions_diff"].max())

        axis.set_ylabel("")
        axis.yaxis.set_visible(False)
        plt.yscale("asinh")
        axis.set_yticklabels([])


class InteractionChangeAuthorDistribution(
    Plot, plot_name="interactions_change_distribution"
):

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__(plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studys: tp.List[CaseStudy] = self.plot_kwargs["case_study"]
        data = pd.DataFrame({
            "author": [],
            "interactions_diff": [],
            "project": []
        })
        for case_study in case_studys:
            cs_data = lines_per_interactions_author(case_study)
            cs_data["interactions_diff"] = cs_data.groupby(
                "author", sort=False
            )["interactions"].diff().astype(float)
            print(cs_data)
            cs_data.insert(2, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        print(data)
        data_sub = data.groupby(["author", "project"],
                                sort=False)["interactions_diff"].sum()
        print(data_sub)
        df = data_sub.to_frame().reset_index()
        print(df.dtypes)
        axis = sns.violinplot(
            data=df, y="interactions_diff", x="project", bw=0.1
        )
        plt.scale('asinh')
        axis.set_ylabel("")
        axis.set_xlabel("")


class InteractionChangeDistributionGenerator(
    PlotGenerator,
    generator_name="change-distribution",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        return [
            InteractionChangeDistribution(self.plot_config, **self.plot_kwargs),
            #InteractionChangeAuthorDistribution(self.plot_config,**self.plot_kwargs)
        ]


class RevisionImpactGenerator(
    PlotGenerator,
    generator_name="revision-impact",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        return [
            #RevisionImpactDistribution(self.plot_config, **self.plot_kwargs),
            RevisionImpactScatterInteractions(
                self.plot_config, **self.plot_kwargs
            ),
            RevisionImpactScatterLines(self.plot_config, **self.plot_kwargs),
            #RevisionImpactScatter(self.plot_config, **self.plot_kwargs)
            #InteractionChangeAuthorDistribution(self.plot_config,**self.plot_kwargs)
        ]
