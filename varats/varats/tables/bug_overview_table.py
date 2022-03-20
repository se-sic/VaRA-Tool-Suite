"""Module for writing bug-data metrics tables."""
import typing as tp

import numpy as np
import pandas as pd
from tabulate import tabulate

from varats.paper.case_study import CaseStudy
from varats.project.project_util import get_project_cls_by_name
from varats.provider.bug.bug_provider import BugProvider
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import (
    TableFormat,
    TableGenerator,
    OPTIONAL_REPORT_TYPE,
    REQUIRE_MULTI_CASE_STUDY,
    TableConfig,
)


class BugOverviewTable(Table):
    """Visualizes bug metrics of a project."""

    NAME = "bug_overview_table"

    def __init__(self, table_config: TableConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, table_config, **kwargs)

    def tabulate(self) -> str:
        project_name: str = self.table_kwargs['case_study'].project_name

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )

        variables = [
            "fixing hash", "fixing message", "fixing author", "issue_number"
        ]
        pybugs = bug_provider.find_pygit_bugs()

        data_rows = [[
            pybug.fixing_commit.hex, pybug.fixing_commit.message,
            pybug.fixing_commit.author.name, pybug.issue_id
        ] for pybug in pybugs]

        bug_df = pd.DataFrame(columns=variables, data=np.array(data_rows))
        table_format: TableFormat = self.table_kwargs["format"]

        if table_format in [
            TableFormat.LATEX, TableFormat.LATEX_RAW, TableFormat.LATEX_BOOKTABS
        ]:
            tex_code = bug_df.to_latex(
                bold_rows=True, multicolumn_format="c", longtable=True
            )
            return str(tex_code) if tex_code else ""
        return tabulate(bug_df, bug_df.columns, table_format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)


class BugOverviewTableGenerator(
    TableGenerator,
    generator_name="bug-overview-table",
    options=[REQUIRE_MULTI_CASE_STUDY, OPTIONAL_REPORT_TYPE]
):
    """Generates a bug-overview table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            BugOverviewTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
