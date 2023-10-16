"""Module for the TimedWorkloadsTable."""
import typing as tp

import numpy as np
import pandas as pd

from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_CASE_STUDY


import re

budgetre = re.compile("RunTracedNaive([0-9]+)")

def budget_from_experiment_name(name):
    if (m := re.search(budgetre, name)) is not None:
        return int(m.group(1))
    elif name == "RunTraced":
        return 0
    elif name == "RunUntraced":
        return -1


class TimedWorkloadTable(Table, table_name="time_workloads_2"):
    """Simple table to print the run-time and memory consumption of different
    workloads."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        df = pd.DataFrame()

        case_study = self.table_kwargs["case_study"]
        project_name = case_study.project_name

        experiments = self.table_kwargs["experiment_type"]

        for experiment in experiments:

            project_name = case_study.project_name

            report_files = get_processed_revisions_files(
                project_name, experiment,
                WLTimeReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
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

                for workload_name in agg_time_report.workload_names():
                    new_row = {
                        "Experiment":
                            experiment.NAME,
                        "Budget": budget_from_experiment_name(experiment.NAME),
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
                        "Reps":
                            len(agg_time_report.reports(workload_name))
                    }

                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        df.sort_values(["Workload", "Budget"], inplace=True)

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = "llr|rr|r|r"

        return dataframe_to_table(
            df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class TimedWorkloadTableGenerator(
    TableGenerator,
    generator_name="time-workloads-2",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_CASE_STUDY]
):
    """Generator for `TimeWorkloadsTable`."""

    def generate(self) -> tp.List[Table]:
        return [TimedWorkloadTable(self.table_config, **self.table_kwargs)]
