"""Module for commits survival tables."""
import typing as tp

import pandas as pd

from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plots.commit_trend import lines_per_interactions_squashed
from varats.plots.interactions_change_distribution import (
    revision_impact,
    impact_data,
)
from varats.plots.surviving_commits import lines_and_interactions
from varats.project.project_util import get_primary_project_source
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.git_util import create_commit_lookup_helper, CommitRepoPair


class CommitSurvivalTable(Table, table_name="commit_survival"):
    """Table showing the survival of commits loc over time."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_and_interactions(case_study)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class Impact(Table, table_name="revision_impact"):
    """Table showing the impact of a revision."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        case_studys: tp.List[CaseStudy] = self.table_kwargs["case_study"]
        data = pd.DataFrame({
            "revision": [],
            "interactions": [],
            "interaction_change": [],
            "lines": [],
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
        return dataframe_to_table(data, table_format, wrap_table=wrap_table)


class HighImpactRevisions(Table, table_name="high_impact_revisions"):
    """Table showing high impact revisions."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        project_name: str = self.table_kwargs["case_study"].project_name
        commit_map: CommitMap = get_commit_map(project_name)
        commit_lookup_helper = create_commit_lookup_helper(project_name)
        repo = get_primary_project_source(project_name).local

        def revison_data(time_id: int, prev_time_id,
                         impact: float) -> dict[str, tp.Any]:
            revision = commit_map.c_hash(time_id)
            commit = commit_lookup_helper(CommitRepoPair(revision, repo))
            return {
                "project": project_name,
                "hash": revision,
                "time_id": commit_map.time_id(revision),
                "message": commit.message,
                "author": commit.author.name,
                "impact": impact,
                "prev_revision": prev_time_id
            }

        high_impact_revs: tp.List[dict[str, tp.Any]] = []

        data = impact_data([self.table_kwargs['case_study']])
        data.fillna(value=0, inplace=True)
        df_iter = data.iterrows()
        _, last_row = next(df_iter)
        for _, row in df_iter:
            change = row["impacted_commits"]
            if change > (self.table_kwargs['threshold'] / 100.0):
                lhs_cm = last_row["revision"]
                rhs_cm = row["revision"]
                high_impact_revs.append(revison_data(rhs_cm, lhs_cm, change))
            last_row = row
        return dataframe_to_table(
            pd.DataFrame(high_impact_revs), table_format, wrap_table=wrap_table
        )


class ImpactCorrelation(Table, table_name="impact_correlation"):
    """Table showing the correlation between the impact of revisions and their
    size."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        case_studys: tp.List[CaseStudy] = self.table_kwargs["case_study"]
        data = impact_data(case_studys)
        return dataframe_to_table(
            data.corr(), table_format, wrap_table=wrap_table
        )


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


class ImpactTableGenerator(
    TableGenerator,
    generator_name="revision-impact",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a table showing the impact of a revision."""

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [
            Impact(self.table_config, **self.table_kwargs),
            ImpactCorrelation(self.table_config, **self.table_kwargs)
        ]


class HighImpactTableGenerator(
    TableGenerator,
    generator_name="high-impact-revs",
    options=[
        REQUIRE_CASE_STUDY,
        make_cli_option("--threshold", type=int, default=50, required=True)
    ]
):
    """Generates a table showing high impact revisions."""

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [HighImpactRevisions(self.table_config, **self.table_kwargs)]
