"""Module for the PerfInterDataTable."""
import typing as tp

import pandas as pd

from varats.experiments.base.perf_sampling import PerfSampling
from varats.jupyterhelper.file import (
    load_wl_function_overhead_report_aggregate,
    load_wl_time_report_aggregate,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
)
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


def _is_ok_twl_report(report: WLTimeReportAggregate, reps: int = 10) -> bool:
    wl = next(iter(report.workload_names()))
    times = report.measurements_wall_clock_time(wl)

    return len(times) == reps and all([t > 0.0 for t in times])


def _is_ok_foh_report(
    report: WLFunctionOverheadReportAggregate,
    reps=10,
    threshold: int = 5
) -> bool:
    wl = next(iter(report.workload_names()))
    reports = report.reports(wl)

    return len(reports) == reps and all([
        len(r.hot_functions(threshold)) > 0 for r in reports
    ])


class PerfInterDataTable(Table, table_name="performance_interaction_data"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        entries: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            project_name = case_study.project_name

            foh_report_files = get_processed_revisions_files(
                project_name,
                PerfSampling,
                WLFunctionOverheadReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            twl_report_files = get_processed_revisions_files(
                project_name,
                PerfSampling,
                WLTimeReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            foh_report_file_data = pd.DataFrame.from_records([{
                "revision": report_file.report_filename.commit_hash,
                "config_id": report_file.report_filename.config_id,
                "report_file": report_file
            } for report_file in foh_report_files])

            twl_report_file_data = pd.DataFrame.from_records([{
                "revision": report_file.report_filename.commit_hash,
                "config_id": report_file.report_filename.config_id,
                "report_file": report_file
            } for report_file in twl_report_files])

            for revision in case_study.revisions:
                short_revision = revision.to_short_commit_hash()
                fho_missing_files = []
                fho_broken_reports = []
                twl_missing_files = []
                twl_broken_reports = []

                for config_id in case_study.get_config_ids_for_revision(
                    revision
                ):
                    if (
                        foh_report_file := foh_report_file_data[(
                            foh_report_file_data["revision"] == short_revision
                        ) & (foh_report_file_data["config_id"] == config_id)]
                    ).empty:
                        fho_missing_files.append((revision, config_id))
                        print(
                            f"[{project_name}] Missing FOH report for {short_revision} and config {config_id}"
                        )
                    else:
                        foh_report = load_wl_function_overhead_report_aggregate(
                            foh_report_file["report_file"].item()
                        )
                        if not _is_ok_foh_report(foh_report):
                            fho_broken_reports.append((revision, config_id))
                            print(
                                f"[{project_name}] Broken FOH report for {short_revision} and config {config_id}"
                            )

                    if (
                        twl_report_file := twl_report_file_data[(
                            twl_report_file_data["revision"] == short_revision
                        ) & (twl_report_file_data["config_id"] == config_id)]
                    ).empty:
                        twl_missing_files.append((revision, config_id))
                        print(
                            f"[{project_name}] Missing TWL report for {short_revision} and config {config_id}"
                        )
                    else:
                        twl_report = load_wl_time_report_aggregate(
                            twl_report_file["report_file"].item()
                        )
                        if not _is_ok_twl_report(twl_report):
                            twl_broken_reports.append((revision, config_id))
                            print(
                                f"[{project_name}] Broken TWL report for {short_revision} and config {config_id}"
                            )

                entries.append({
                    "Project":
                        project_name,
                    "Revision":
                        short_revision.hash,
                    "Configs":
                        len(case_study.get_config_ids_for_revision(revision)),
                    "FHO Missing":
                        len(fho_missing_files),
                    "FHO Broken":
                        len(fho_broken_reports),
                    "TWL Missing":
                        len(twl_missing_files),
                    "TWL Broken":
                        len(twl_broken_reports)
                })

        df = pd.DataFrame.from_records(entries).drop_duplicates()
        df.sort_values(["Project", "Revision"], inplace=True)
        df.set_index(
            ["Project", "Revision"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class PerfInterDataTableGenerator(
    TableGenerator, generator_name="perf-inter-data", options=[]
):
    """Generator for `HotFunctionsTable`."""

    def generate(self) -> tp.List[Table]:
        return [PerfInterDataTable(self.table_config, **self.table_kwargs)]
