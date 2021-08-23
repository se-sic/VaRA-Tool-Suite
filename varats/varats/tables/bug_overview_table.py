"""Module for writing bug-data metrics tables."""
import typing as tp

import numpy as np
import pandas as pd
from tabulate import tabulate

from varats.project.project_util import get_project_cls_by_name
from varats.provider.bug.bug_provider import BugProvider
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat


class BugOverviewTable(Table):
    """Visualizes bug metrics of a project."""

    NAME = "bug_overview"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        project_name = self.table_kwargs["project"]

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

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_RAW, TableFormat.LATEX_BOOKTABS
        ]:
            tex_code = bug_df.to_latex(
                bold_rows=True, multicolumn_format="c", longtable=True
            )
            return str(tex_code) if tex_code else ""
        return tabulate(bug_df, bug_df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
