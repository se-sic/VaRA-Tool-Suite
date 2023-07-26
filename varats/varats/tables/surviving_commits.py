"""Module for commits survival tables."""
import typing as tp

import pandas as pd

from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plots.commit_trend import lines_per_interactions_squashed
from varats.plots.surviving_commits import (
    lines_and_interactions,
    get_lines_per_commit_long,
    get_interactions_per_commit_long,
)
from varats.project.project_util import get_primary_project_source
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
    REQUIRE_REVISION,
)
from varats.utils.git_util import (
    create_commit_lookup_helper,
    FullCommitHash,
    CommitRepoPair,
    ShortCommitHash,
)


class CommitSurvivalTable(Table, table_name="commit_survival"):
    """Table showing the survival of commits loc over time."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_and_interactions(case_study)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class SingleCommitSurvivalTable(Table, table_name="single_commit_survival"):

    @property
    def name(self) -> str:
        return "single_commit_survival_" + ShortCommitHash(
            self.table_kwargs['revision']
        ).hash

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study = self.table_kwargs['case_study']
        revision = self.table_kwargs['revision']
        lines: pd.DataFrame = get_lines_per_commit_long(case_study, False)

        interactions: pd.DataFrame = get_interactions_per_commit_long(
            case_study, False
        )
        data = lines.merge(
            interactions, how='left', on=["base_hash", "revision"]
        )
        data.dropna(
            axis=0, how='any', inplace=True, subset=["lines", "interactions"]
        )

        data = data[data["base_hash"].apply(lambda x: x.startswith(revision))]
        data.set_index("revision", inplace=True)
        cmap = get_commit_map(case_study.project_name)
        data.sort_index(
            axis=0, key=lambda x: x.map(cmap.short_time_id), inplace=True
        )
        data["time_id"] = data.index.map(cmap.short_time_id)
        data.drop(columns="base_hash", inplace=True)
        return dataframe_to_table(data, table_format, wrap_table=wrap_table)


class CommitSurvivalChangesTable(Table, table_name="interactions_loc_change"):
    """Table showing the change in interactions between revisions."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_per_interactions_squashed(case_study)
        data_frame = data_frame.pivot(
            index="revision", columns="base_hash", values="interactions"
        )
        data_frame.sort_index(axis=0, inplace=True)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class VolatileCommitsTable(Table, table_name="volatile_commits"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studys: tp.List[CaseStudy] = self.table_kwargs["case_study"]
        volatile_commits: tp.List[dict[str, tp.Any]] = []
        for case_study in case_studys:
            project_name = case_study.project_name
            commit_lookup_helper = create_commit_lookup_helper(project_name)
            repo = get_primary_project_source(project_name).local

            def commmit_data(commit: FullCommitHash,
                             change: float) -> dict[str, tp.Any]:
                pygit_commit = commit_lookup_helper(
                    CommitRepoPair(commit, repo)
                )
                return {
                    "project": project_name,
                    "hash": commit,
                    "message": pygit_commit.message,
                    "author": pygit_commit.author.name,
                    "change": change + 1
                }

            cs_data = lines_per_interactions_squashed(case_study, True)
            cs_data["interactions_diff"] = cs_data.groupby(
                "base_hash", sort=False
            )["interactions"].diff().astype(float)
            cs_data.drop("revision", axis=1, inplace=True)
            data = cs_data.groupby(
                "base_hash", sort=False
            )["interactions_diff"].sum().to_frame().reset_index()
            high_q = data["interactions_diff"].quantile(0.95)
            low_q = data["interactions_diff"].quantile(0.05)
            df_iter = data[(data["interactions_diff"] > high_q) |
                           (data["interactions_diff"] < low_q)]
            for _, row in df_iter:
                volatile_commits.append(
                    commmit_data(row["base_hash"], row["interactions_diff"])
                )
        df = pd.DataFrame(volatile_commits)
        df.to_csv("volatile_commits.csv")
        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class CommtiSurvivalGenerator(
    TableGenerator,
    generator_name="commit_survival",
    options=[REQUIRE_CASE_STUDY]
):
    """Generates a table showing the survival of commits loc over time."""

    def generate(self) -> tp.List['varats.table.table.Table']:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")
        return [
            CommitSurvivalChangesTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            ),
            CommitSurvivalTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            )
        ]


class SingleCommitSurvivalGenerator(
    TableGenerator,
    generator_name="single-survival",
    options=[REQUIRE_CASE_STUDY, REQUIRE_REVISION]
):

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [
            SingleCommitSurvivalTable(self.table_config, **self.table_kwargs)
        ]


class VolatileCommitGenerator(
    TableGenerator,
    generator_name="volatile-commits",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [VolatileCommitsTable(self.table_config, **self.table_kwargs)]
