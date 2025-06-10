import typing as tp

import numpy as np
import pandas as pd

from varats.data.databases.hidden_configurability_database import aggregate_data
from varats.data.reports.hidden_configurability_report import (
    HiddenConfigurabilityReport,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    FindHiddenConfigurationPoints,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableGenerator, TableFormat
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import create_multi_case_study_choice


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

            if report.get_num_configurability_points(
            ) == 0 and self.table_kwargs["hide_zero"]:
                continue

            new_row = {
                "Case Study": case_study.project_name,
                "Total": report.get_num_configurability_points(),
            }

            for kind, count in report.get_num_configurability_points_by_kind(
            ).items():
                new_row[kind] = count

            table_data.append(new_row)

        df = pd.DataFrame(table_data)

        df.sort_values(by="Case Study", inplace=True)

        return dataframe_to_table(df, table_format, wrap_table=wrap_table)


class HiddenVariabilityOverviewTableGenerator(
    TableGenerator,
    generator_name="hidden-var-overview",
    options=[
        make_cli_option(
            "--hide-zero",
            is_flag=True,
            default=False,
            help="Hide projects with zero hidden configurability points."
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [
            HiddenVariabilityOverviewTable(
                self.table_config, **self.table_kwargs
            )
        ]


class HCPerfTable(Table, table_name="hc_perf_overview"):

    @property
    def name(self) -> str:
        return f"{self.NAME}{'_'.join([cs.project_name for cs in self.table_kwargs['case_studies']])}"

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = self.table_kwargs["case_studies"]

        significant_results = pd.DataFrame()

        for case_study in case_studies:
            cs_data = aggregate_data(case_study, None)

            if cs_data.empty:
                continue

            # Filter only significant rows
            def filter_results(row: pd.Series) -> bool:
                # Remove baseline data
                if row["config_opportunity"] == "__baseline__":
                    return False

                if row["metric"] == "wall_clock_time" and np.mean(
                    row["value"]
                ) < 1:
                    return False

                if row["metric"] == "max_resident_size" and np.mean(
                    row["value"]
                ) < 5000:
                    return False

                if row["significance"] >= 0.05:
                    return False

                if abs(row["value_relative"]) < 0.05:
                    return False

                return True

            cs_data = cs_data[cs_data["config_opportunity"] != "__baseline__"]
            cs_data["Project"] = case_study.project_name
            cs_data["value_relative"] = cs_data["value_relative"].apply(
                np.median
            )
            cs_data["significance"] = cs_data["significance"].apply(
                lambda x: x.pvalue
            )
            cs_data = cs_data[cs_data.apply(filter_results, axis=1)]

            cs_data.drop(columns=["value"], inplace=True)
            significant_results = pd.concat([significant_results, cs_data],
                                            ignore_index=True)

        # Rearrange columns
        col_mappings = {
            "config_id": "Config",
            "binary-wl": "Workload",
            "significance": "p-value",
            "config_opportunity": "opportunity",
        }

        column_order = [
            "Project", "metric", "config_id", "binary-wl", "config_opportunity",
            "variation", "significance", "value_relative"
        ]
        significant_results = significant_results[column_order]

        significant_results = significant_results.rename(columns=col_mappings)

        significant_results.sort_values(
            by=["Project", "metric", "Config", "opportunity", "variation"],
            inplace=True
        )

        return dataframe_to_table(
            significant_results, table_format, wrap_table=wrap_table
        )


class HCPerfGenerator(
    TableGenerator,
    generator_name="hc_perf_overview",
    options=[
        make_cli_option(
            "--case-studies",
            type=create_multi_case_study_choice(),
            help="Case studies to include"
        )
    ]
):

    def generate(self) -> tp.List[Table]:
        return [HCPerfTable(self.table_config, **self.table_kwargs)]
