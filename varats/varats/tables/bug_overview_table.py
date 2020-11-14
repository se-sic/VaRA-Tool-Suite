"""Module for writing bug-data metrics tables."""
import typing as tp
from pathlib import Path

import numpy as np
import pandas as pd
from tabulate import tabulate

from varats.project.project_util import get_project_cls_by_name
from varats.provider.bug.bug_provider import BugProvider
from varats.tables.table import Table, TableFormat


class BugOverviewTable(Table):
    """Visualizes bug metrics of a project."""

    NAME = "bug_overview"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        project_name = self.table_kwargs["project"]

        with BugProvider.create_provider_for_project(
            get_project_cls_by_name(project_name)
        ) as provider:
            if provider:
                bug_provider = provider
            else:
                bug_provider = BugProvider.create_default_provider(
                    get_project_cls_by_name(project_name)
                )

        variables = ["fixing hash", "fixing message", "fixing author"]
        pybugs = bug_provider.find_all_pygit_bugs()

        data_rows = [[
            pybug.fixing_commit.hex, pybug.fixing_commit.message,
            pybug.fixing_commit.author
        ] for pybug in pybugs]

        bug_df = pd.DataFrame(columns=variables, data=np.array(data_rows))

        if self.format in [
            TableFormat.latex, TableFormat.latex_raw, TableFormat.latex_booktabs
        ]:
            tex_code = bug_df.to_latex(bold_rows=True, multicolumn_format="c")
            return str(tex_code) if tex_code else ""
        return tabulate(bug_df, bug_df.columns, self.format.value)

    def save(
        self,
        path: tp.Optional[Path] = None,
    ) -> None:
        filetype = self.format_filetypes.get(self.format, "txt")

        if path is None:
            table_dir = self.table_kwargs("table_dir")
        else:
            table_dir = path

        filename = f"{self.NAME}_{self.table_kwargs('project')}"
        content = self.tabulate()

        with open(table_dir / f"{filename}.{filetype}", "w") as output_file:
            output_file.write(content)
