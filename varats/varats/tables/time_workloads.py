"""Module for the TimedWorkloadsTable."""
import typing as tp

import numpy as np
import pandas as pd

from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.report.gnu_time_report import (
    TimeReportAggregate,
    WLTimeReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE


class TimedWorkloadTable(Table, table_name="time_workloads"):
    """Simple table to print the run-time and memory consumption of different
    workloads."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            if len(self.table_kwargs["experiment_type"]) > 1:
                print(
                    "Table can currently handle only a single experiment, "
                    "ignoring everything else."
                )

            report_files = get_processed_revisions_files(
                project_name,
                self.table_kwargs["experiment_type"][0], TimeReportAggregate,
                get_case_study_file_name_filter(case_study)
            )

            def wall_clock_time_in_msecs(
                agg_time_report: WLTimeReportAggregate
            ) -> tp.List[float]:
                return list(
                    map(
                        lambda x: x * 1000,
                        agg_time_report.
                        measurements_wall_clock_time(workload_name)
                    )
                )

            for report_filepath in report_files:
                agg_time_report = WLTimeReportAggregate(
                    report_filepath.full_path()
                )
                report_file = agg_time_report.filename

                for workload_name in agg_time_report.workload_names():
                    new_row = {
                        "Project":
                            project_name,
                        "Binary":
                            report_file.binary_name,
                        "Revision":
                            str(report_file.commit_hash),
                        "Workload":
                            workload_name,
                        "Mean wall time (msecs)":
                            np.mean(wall_clock_time_in_msecs(agg_time_report)),
                        "StdDev":
                            round(
                                np.std(
                                    wall_clock_time_in_msecs(agg_time_report)
                                ), 2
                            ),
                        "Max resident size (kbytes)":
                            max(
                                agg_time_report.
                                max_resident_sizes(workload_name)
                            ),
                        "Reps":
                            len(agg_time_report.reports(workload_name))
                    }

                    df = df.append(new_row, ignore_index=True)

        df.sort_values(["Project", "Binary"], inplace=True)
        df.set_index(
            ["Project", "Binary"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = "llr|rr|r|r"

        return dataframe_to_table(
            df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class TimedWorkloadTableGenerator(
    TableGenerator,
    generator_name="time-workloads",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):
    """Generator for `TimeWorkloadsTable`."""

    def generate(self) -> tp.List[Table]:
        return [TimedWorkloadTable(self.table_config, **self.table_kwargs)]
