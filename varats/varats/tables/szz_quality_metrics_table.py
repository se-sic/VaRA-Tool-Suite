"""Module for writing SZZ quality metrics tables."""
import typing as tp

from tabulate import tabulate

from varats.data.databases.szz_quality_metrics_database import (
    PyDrillerSZZQualityMetricsDatabase,
    SZZUnleashedQualityMetricsDatabase,
)
from varats.data.reports.szz_report import SZZTool
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import (
    TableFormat,
    TableGenerator,
    REQUIRE_MULTI_CASE_STUDY,
    OPTIONAL_REPORT_TYPE,
)


# TODO: Rename class to something similar to NAME
# TODO: Add option for SZZ tool
class BugOverviewTable(Table, table_name="szz_quality_metrics"):
    """Visualizes SZZ quality metrics for a project."""

    def tabulate(self, table_format: TableFormat) -> str:
        project_name = self.table_kwargs["case_study"].project_name
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

        if table_format in [
            TableFormat.LATEX, TableFormat.LATEX_RAW, TableFormat.LATEX_BOOKTABS
        ]:
            tex_code = data.to_latex(multicolumn_format="c", longtable=True)
            return str(tex_code) if tex_code else ""
        return tabulate(data, data.columns, table_format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)


class BugOverviewTableGenerator(
    TableGenerator,
    generator_name="szz-quality-metrics-table",
    options=[REQUIRE_MULTI_CASE_STUDY, OPTIONAL_REPORT_TYPE]
):
    """Generates a szz-quality-metrics table for the selected case study."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            BugOverviewTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
