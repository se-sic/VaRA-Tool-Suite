"""Module for writing commit-data metrics tables."""
import typing as tp
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from varats.data.databases.blame_diff_metrics_database import (
    BlameDiffMetricsDatabase,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.case_study import get_unique_cs_name
from varats.paper_mgmt.paper_config import get_paper_config
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat


class DiffCorrelationOverviewTable(Table):
    """Visualizes the correlations between different `BlameReport` metrics."""

    NAME = "b_diff_correlation_overview"

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_studies = get_paper_config().get_all_case_studies()

        variables = [
            "churn", "num_interactions", "num_interacting_commits",
            "num_interacting_authors"
        ]
        cs_data = [
            BlameDiffMetricsDatabase.get_data_for_project(
                case_study.project_name, ["revision", *variables],
                get_commit_map(case_study.project_name), case_study
            ) for case_study in case_studies
        ]
        for data in cs_data:
            data.set_index('revision', inplace=True)
            data.drop(data[data['churn'] == 0].index, inplace=True)

        correlations = [
            data[variables].corr(method="pearson") for data in cs_data
        ]

        df = pd.concat(
            correlations, axis=1, keys=get_unique_cs_name(case_studies)
        )

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            table = df.to_latex(bold_rows=True, multicolumn_format="c")
            return str(table) if table else ""
        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table)

    def save(
        self,
        path: tp.Optional[Path] = None,
        wrap_document: bool = False
    ) -> None:
        filetype = self.format_filetypes.get(self.format, "txt")

        if path is None:
            table_dir = Path(self.table_kwargs["table_dir"])
        else:
            table_dir = path

        table = self.tabulate()
        if wrap_document:
            table = self.wrap_table(table)

        with open(table_dir / f"{self.name}.{filetype}", "w") as outfile:
            outfile.write(table)
