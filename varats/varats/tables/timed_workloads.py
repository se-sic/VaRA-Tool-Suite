"""Module for the TimedWorkloadsTable."""
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


class TimedWorkloadTable(Table, table_name="timed_workloads"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            report_files = get_processed_revisions_files(
                project_name, TimeReportAggregate,
                get_case_study_file_name_filter(case_study)
            )

            for report_file in report_files:
                agg_time_report = TimeReportAggregate(report_file)
                report_file = agg_time_report.filename

                #mean_runtime = np.mean(time_report.measurements_wall_clock_time)
                #std_runtime = np.std(time_report.measurements_wall_clock_time)
                #mean_ctx = np.mean(time_report.measurements_ctx_switches)
                #std_ctx = np.std(time_report.measurements_ctx_switches)

                new_row = {
                    "Project":
                        project_name,
                    "Binary":
                        report_file.binary_name,
                    "Revision":
                        str(report_file.commit_hash),
                    "Mean wall time (msecs)":
                        # agg_time_report.wall_clock_time.total_seconds() * 1000,
                        np.mean(list(map(lambda x: x * 1000, agg_time_report.measurements_wall_clock_time))),
                    "StdDev":
                        np.std(list(map(lambda x: x * 1000, agg_time_report.measurements_wall_clock_time))),
                    "Max resident size (kbytes)":
                        max(agg_time_report.max_resident_sizes),
                    #"Involuntarty CTX switches":
                    #    agg_time_report.involuntary_ctx_switches
                    "Reps": len(agg_time_report.reports)
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
    TableGenerator, generator_name="timed-workloads", options=[]
):
    """Generator for `TimeWorkloadsTable`."""

    def generate(self) -> tp.List[Table]:
        return [TimedWorkloadTable(self.table_config, **self.table_kwargs)]
