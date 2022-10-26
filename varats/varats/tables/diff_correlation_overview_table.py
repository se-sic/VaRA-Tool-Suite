"""Module for writing commit-data metrics tables."""
import typing as tp

import pandas as pd

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.case_study import get_unique_cs_name
from varats.paper_mgmt.paper_config import get_paper_config
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class DiffCorrelationOverviewTable(
    Table, table_name="b_diff_correlation_overview_table"
):
    """Visualizes the correlations between different `BlameReport` metrics."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_paper_config().get_all_case_studies()

        variables = {
            "churn": "Churn",
            "num_interactions": "Num Interactions",
            "num_interacting_commits": "Num Interacting Commits",
            "num_interacting_authors": "Num Interacting Authors",
        }
        cs_data = [
            BlameDiffMetricsDatabase.get_data_for_project(
                case_study.project_name, ["revision", *variables.keys()],
                get_commit_map(case_study.project_name), case_study
            ) for case_study in case_studies
        ]
        for data in cs_data:
            data.set_index('revision', inplace=True)
            data.drop(data[data['churn'] == 0].index, inplace=True)
            data.rename(columns=variables, inplace=True)

        correlations = [
            data[variables.values()].corr(method="pearson") for data in cs_data
        ]

        df = pd.concat(
            correlations, axis=1, keys=get_unique_cs_name(case_studies)
        )

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["multicol_align"] = "c"
            style.format(precision=2)

        return dataframe_to_table(
            df,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=False,
            **kwargs
        )


class DiffCorrelationOverviewTableGenerator(
    TableGenerator,
    generator_name="diff-correlation-overview-table",
    options=[]
):
    """Generates a bug-overview table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            DiffCorrelationOverviewTable(
                self.table_config, **self.table_kwargs
            )
        ]
