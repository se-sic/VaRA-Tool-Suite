"""Module for writing SZZ quality metrics tables."""
import typing as tp

from tabulate import tabulate

from varats.data.databases.szz_quality_metrics_database import (
    PyDrillerSZZQualityMetricsDatabase,
    SZZUnleashedQualityMetricsDatabase,
)
from varats.data.reports.szz_report import SZZTool
from varats.mapping.commit_map import get_commit_map
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat


class BugOverviewTable(Table):
    """Visualizes SZZ quality metrics for a project."""

    NAME = "szz_quality_metrics"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        project_name = self.table_kwargs["project"]
        szz_tool_name: tp.Optional[str] = self.table_kwargs.get(
            "szz_tool", None
        )
        if not szz_tool_name:
            raise ValueError("No szz tool provided")
        szz_tool = SZZTool[szz_tool_name.upper()]

        commit_map = get_commit_map(project_name)
        columns = {
            "revision": "fix",
            "introducer": "introducer",
            "score": "score"
        }
        if szz_tool == SZZTool.PYDRILLER_SZZ:
            data = PyDrillerSZZQualityMetricsDatabase.get_data_for_project(
                project_name, list(columns.keys()), commit_map
            )
        elif szz_tool == SZZTool.SZZ_UNLEASHED:
            data = SZZUnleashedQualityMetricsDatabase.get_data_for_project(
                project_name, list(columns.keys()), commit_map
            )
        else:
            raise ValueError(f"Unknown SZZ tool '{szz_tool_name}'")

        data.rename(columns=columns, inplace=True)
        data.set_index(["fix", "introducer"], inplace=True)
        data.sort_values("score", inplace=True)
        data.sort_index(level="fix", sort_remaining=False, inplace=True)

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_RAW, TableFormat.LATEX_BOOKTABS
        ]:
            tex_code = data.to_latex(multicolumn_format="c", longtable=True)
            return str(tex_code) if tex_code else ""
        return tabulate(data, data.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
