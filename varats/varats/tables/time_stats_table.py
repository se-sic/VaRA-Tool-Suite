"""Module for `TimeStatsTable`."""
import typing as tp

import numpy as np
import pandas as pd

from varats.experiment.experiment_util import VersionExperiment
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import TimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE


class TimeStatsTable(Table, table_name="time_stats"):
    """
    Compute execution time statistics for `TimeReportAggregate` and render into
    a table to enable comparison of different experiments.

    Assumes single workload per case study.
    """

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for experiment_type in self.table_kwargs["experiment_type"]:
            if not issubclass(experiment_type, VersionExperiment):
                print(
                    f"Skipping {experiment_type} because it is not a "
                    f"subclass of {VersionExperiment} and probably doesn't "
                    "have a shorthand attribute."
                )
                continue

            for case_study in case_studies:
                project_name = case_study.project_name

                report_files = get_processed_revisions_files(
                    project_name, experiment_type, TimeReportAggregate,
                    get_case_study_file_name_filter(case_study), False
                )

                for report in report_files:
                    time_aggregated = TimeReportAggregate(report.full_path())
                    report_name = time_aggregated.filename

                    mean_runtime = np.mean(
                        time_aggregated.measurements_wall_clock_time
                    )
                    std_runtime = np.std(
                        time_aggregated.measurements_wall_clock_time
                    )
                    mean_ctx = np.mean(
                        time_aggregated.measurements_ctx_switches
                    )
                    std_ctx = np.std(time_aggregated.measurements_ctx_switches)

                    new_row = {
                        "Binary":
                            report_name.binary_name,
                        "Experiment":
                            experiment_type.shorthand(),
                        "Commit":
                            report_name.commit_hash,
                        "Runtime Mean (Std)":
                            f"{round(mean_runtime, 2)} "
                            f"({round(std_runtime, 2)})",
                        "Ctx-Switches Mean (Std)":
                            f"{round(mean_ctx, 2)} ({round(std_ctx, 2)})",
                        "Samples":
                            len(time_aggregated.reports())
                    }

                    df = df.append(new_row, ignore_index=True)

        df.sort_values(["Binary", "Experiment"], inplace=True)

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
