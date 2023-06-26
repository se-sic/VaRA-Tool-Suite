import typing as tp

import pandas as pd

from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.plots.revision_impact import impact_data
from varats.project.project_util import get_primary_project_source
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_CASE_STUDY,
    REQUIRE_CASE_STUDY,
)
from varats.utils.git_util import create_commit_lookup_helper, CommitRepoPair


class Impact(Table, table_name="revision_impact"):
    """Table showing the impact of a revision."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        data = self.table_kwargs["data"]
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


class ImpactDistribution(Table, table_name="impact_distribution"):
    """Table showing high impact revisions."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""

        high_impact_revs: dict[str, tp.Any] = {}

        data = self.table_kwargs["data"]
        data.fillna(value=0, inplace=True)
        project_groups = data.groupby("project")
        for project, project_data in project_groups:
            project_counts: tp.List[int] = []
            for i in range(100 // 10):
                project_counts.append(
                    len(
                        project_data[project_data["impacted_commits"] >
                                     (i * 10 / 100)]
                    )
                )

            high_impact_revs[project] = project_counts
        print(high_impact_revs)
        return dataframe_to_table(
            pd.DataFrame.from_dict(
                high_impact_revs,
                orient='index',
                columns=[i * 10 for i in range(100 // 10)]
            ),
            table_format,
            wrap_table=wrap_table
        )


class LineImpactDistribution(Table, table_name="line_impact_distribution"):
    """Table showing high impact revisions."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""

        high_impact_revs: tp.List[dict[str, tp.Any]] = []

        data = self.table_kwargs["data"]
        data.fillna(value=0, inplace=True)
        project_groups = data.groupby("project")
        for project, project_data in project_groups:
            project_counts: dict[int, tp.Any] = {}
            for i in range(100 // 10):
                project_counts[i] = project_data[project_data["line_change"] >
                                                 (i / 100)].count()
            high_impact_revs.append({project: project_counts})
        return dataframe_to_table(
            pd.DataFrame(high_impact_revs), table_format, wrap_table=wrap_table
        )


class ImpactCorrelation(Table, table_name="impact_correlation"):
    """Table showing the correlation between the impact of revisions and their
    size."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        data = self.table_kwargs["data"]
        correlation_data = data.groupby("project"
                                       ).corr()["impacted_commits"].unstack()
        correlation_data.drop(["impacted_commits", "interactions", "lines"],
                              axis=1,
                              inplace=True)
        return dataframe_to_table(
            correlation_data, table_format, wrap_table=wrap_table
        )


class ImpactCorrelationAgg(Table, table_name="impact_correlation_agg"):
    """Table showing the correlation between the impact of revisions and their
    size."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        """Tabulate the table."""
        data = self.table_kwargs["data"]
        correlation_data = data.corr()
        correlation_data.drop(["impacted_commits", "interactions", "lines"],
                              axis=1,
                              inplace=True)
        return dataframe_to_table(
            correlation_data, table_format, wrap_table=wrap_table
        )


class ImpactTableGenerator(
    TableGenerator,
    generator_name="revision-impact",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a table showing the impact of a revision."""

    def generate(self) -> tp.List['varats.table.table.Table']:
        data = impact_data(self.table_kwargs['case_study'])
        self.table_kwargs['data'] = data
        return [
            Impact(self.table_config, **self.table_kwargs),
            ImpactCorrelation(self.table_config, **self.table_kwargs),
            ImpactCorrelationAgg(self.table_config, **self.table_kwargs)
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


class ImpactDistributionGenerator(
    TableGenerator,
    generator_name="impact-distribution",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.table.table.Table']:
        self.table_kwargs['data'] = impact_data(self.table_kwargs['case_study'])
        return [
            ImpactDistribution(self.table_config, **self.table_kwargs),
            LineImpactDistribution(self.table_config, **self.table_kwargs)
        ]
