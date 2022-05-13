"""Module for writing SZZ quality metrics tables."""
import typing as tp

from varats.data.databases.szz_quality_metrics_database import (
    PyDrillerSZZQualityMetricsDatabase,
    SZZUnleashedQualityMetricsDatabase,
)
from varats.data.reports.szz_report import SZZTool
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_CASE_STUDY,
    EnumChoice,
)


class SZZQualityMetricsTable(Table, table_name="szz_quality_metrics"):
    """Visualizes SZZ quality metrics for a project."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        project_name = self.table_kwargs["case_study"].project_name
        szz_tool: SZZTool = self.table_kwargs["szz_tool"]

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
            raise ValueError(f"Unknown SZZ tool '{szz_tool.tool_name}'")

        data.rename(columns=columns, inplace=True)
        data.set_index(["fix", "introducer"], inplace=True)
        data.sort_values("score", inplace=True)
        data.sort_index(level="fix", sort_remaining=False, inplace=True)

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["multicolumn_format"] = "c"
            kwargs["longtable"] = True

        return dataframe_to_table(
            data, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


REQUIRE_SZZ_TOOL: CLIOptionTy = make_cli_option(
    "--szz-tool",
    type=EnumChoice(SZZTool, case_sensitive=False),
    required=True,
    help="The SZZ tool for which to show the data."
)


class SZZQualityMetricsTableGenerator(
    TableGenerator,
    generator_name="szz-quality-metrics-table",
    options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_SZZ_TOOL]
):
    """Generates a szz-quality-metrics table for the selected case study."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            SZZQualityMetricsTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
