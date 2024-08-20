import typing as tp

import pandas as pd

from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
)
from varats.experiments.vara.hidden_configurability_detector import (
    FindHiddenConfigurationPoints,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat


class HiddenVariabilityOverviewTable(Table, table_name="hidden_var_overview"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        table_data = []

        for case_study in case_studies:
            reports = get_processed_revisions_files(
                case_study.project_name,
                FindHiddenConfigurationPoints,
                FindHiddenConfigurationPoints.report_spec().main_report,
            )

            if not reports:
                continue

            if len(reports) > 1:
                print(f"More than one report for {case_study.project_name}")
                continue

            report = HiddenConfigurabilityReport(reports[0].full_path())

            new_row = {
                "Case Study": case_study.project_name,
                "Total": report.get_num_configurability_points(),
            }

            for kind, count in report.get_num_configurability_points_by_kind(
            ).items():
                new_row[kind] = count

            table_data.append(new_row)

        df = pd.DataFrame(table_data)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HiddenVariabilityOverviewTableGenerator(
    TableGenerator, generator_name="hidden-var-overview", options=[]
):

    def generate(self) -> tp.List[Table]:
        return [
            HiddenVariabilityOverviewTable(
                self.table_config, **self.table_kwargs
            )
        ]
