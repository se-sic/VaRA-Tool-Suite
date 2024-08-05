"""Module for the HotFunctionsTable."""
import typing as tp

import pandas as pd
from jinja2.nodes import Continue

from varats.experiments.base.perf_sampling import PerfSampling
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class HotFunctionsTable(Table, table_name="hot_functions"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        entries = []

        for case_study in case_studies:
            cs_entries = []
            project_name = case_study.project_name

            report_files = get_processed_revisions_files(
                project_name,
                PerfSampling,
                WLFunctionOverheadReportAggregate,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            for report_filepath in report_files:
                agg_hot_functions_report = WLFunctionOverheadReportAggregate(
                    report_filepath.full_path()
                )

                report_file = agg_hot_functions_report.filename

                hot_funcs = agg_hot_functions_report.hot_functions_per_workload(
                    threshold=5
                )

                for workload_name in agg_hot_functions_report.workload_names():
                    if "countries" in workload_name or "example" in workload_name:
                        continue

                    hot_func_data = hot_funcs[workload_name]
                    for hf in hot_func_data:
                        cs_entries.append({
                            "Project": project_name,
                            "Binary": report_file.binary_name,
                            "Revision": str(report_file.commit_hash),
                            "Workload": workload_name,
                            "FunctionName": hf
                        })

            # funcs = {entry["FunctionName"] for entry in cs_entries}
            # print(f"{project_name}: {funcs}")
            entries += cs_entries

        df = pd.DataFrame.from_records(entries).drop_duplicates()
        df.sort_values(["Project", "Binary"], inplace=True)
        df.set_index(
            ["Project", "Binary"],
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


class HotFunctionsTableGenerator(
    TableGenerator, generator_name="hot-functions", options=[]
):
    """Generator for `HotFunctionsTable`."""

    def generate(self) -> tp.List[Table]:
        return [HotFunctionsTable(self.table_config, **self.table_kwargs)]
