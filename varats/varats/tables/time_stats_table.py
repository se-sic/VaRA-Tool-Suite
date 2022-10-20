"""Module for `TimeStatsTable`."""
import typing as tp

import numpy as np
import pandas as pd

from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.report.gnu_time_report import TimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE


class TimeStatsTable(Table, table_name="time_stats"):
    """Table to compare `TimeReportAggregate` stats between multiple experiments
    ."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            for experiment_type in self.table_kwargs["experiment_type"]:
                report_files = get_processed_revisions_files(
                    project_name, experiment_type, TimeReportAggregate,
                    get_case_study_file_name_filter(case_study), False
                )

                report_file = report_files[0]
                time_aggregated = TimeReportAggregate(report_file)
                report_name = time_aggregated.filename

                mean_runtime = np.mean(
                    time_aggregated.measurements_wall_clock_time
                )
                std_runtime = np.std(
                    time_aggregated.measurements_wall_clock_time
                )
                mean_ctx = np.mean(time_aggregated.measurements_ctx_switches)
                std_ctx = np.std(time_aggregated.measurements_ctx_switches)

                new_row = {
                    "Binary":
                        report_name.binary_name,
                    "Experiment":
                        report_name.experiment_shorthand,
                    "Runtime Mean (Std)":
                        f"{mean_runtime:.2f} ({std_runtime:.2f})",
                    "Ctx-Switches Mean (Std)":
                        f"{mean_ctx:.2f} ({std_ctx:.2f})"
                }

                df = df.append(new_row, ignore_index=True)

        df.sort_values(["Binary", "Experiment"], inplace=True)
        df.set_index(
            ["Binary", "Experiment"],
            inplace=True,
        )

        return dataframe_to_table(
            df, table_format, wrap_table=wrap_table, wrap_landscape=True
        )


class TimeStatsTableGenerator(
    TableGenerator,
    generator_name="time-stats",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):
    """Generator for `TimeStatsTable`."""

    def generate(self) -> tp.List[Table]:
        return [TimeStatsTable(self.table_config, **self.table_kwargs)]
