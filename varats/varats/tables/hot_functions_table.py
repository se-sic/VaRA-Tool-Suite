"""Module for the HotFunctionsTable."""
import typing as tp

import pandas as pd

from varats.experiments.vara.hot_function_experiment import XRayFindHotFunctions
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.hot_functions_report import WLHotFunctionAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator


class HotFunctionsWLTable(Table, table_name="hot_functions_wl"):
    """Table that shows hot functions per workload along with specific
    statistics."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            experiment_type = XRayFindHotFunctions
            report_files = get_processed_revisions_files(
                project_name, experiment_type, WLHotFunctionAggregate,
                get_case_study_file_name_filter(case_study)
            )

            for report_filepath in report_files:
                agg_hot_functions_report = WLHotFunctionAggregate(
                    report_filepath.full_path()
                )
                report_file = agg_hot_functions_report.filename

                hot_funcs = agg_hot_functions_report.hot_functions_per_workload(
                    threshold=2
                )

                entries = []
                for workload_name in agg_hot_functions_report.workload_names():
                    hot_func_data = hot_funcs[workload_name]

                    total_time = sum(hf.sum_time for hf in hot_func_data)

                    for hf in hot_func_data:
                        new_row = {
                            "Project": project_name,
                            "Binary": report_file.binary_name,
                            "Workload": workload_name,
                            "FunctionName": hf.name,
                            "TimeSpent": hf.sum_time,
                            "RelativeTime": hf.sum_time / total_time
                        }

                        entries.append(pd.DataFrame([new_row]))

                df = pd.concat(entries, ignore_index=True)

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


class HotFunctionsWLTableGenerator(
    TableGenerator, generator_name="hot-functions-wl", options=[]
):
    """Generator for `HotFunctionsTable`."""

    def generate(self) -> tp.List[Table]:
        return [HotFunctionsWLTable(self.table_config, **self.table_kwargs)]


class HotFunctionConfig(Table, table_name="hot_function_config"):
    """Table that shows hot functions of a project differentiated by different
    configurations."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        entries = []
        for case_study in case_studies:
            project_name = case_study.project_name

            experiment_type = XRayFindHotFunctions

            for config_id in case_study.get_config_ids_for_revision(
                case_study.revisions[0]
            ):
                report_files = get_processed_revisions_files(
                    project_name,
                    experiment_type,
                    WLHotFunctionAggregate,
                    get_case_study_file_name_filter(case_study),
                    config_id=config_id
                )

                for report_filepath in report_files:
                    agg_hot_functions_report = WLHotFunctionAggregate(
                        report_filepath.full_path()
                    )

                    hot_funcs = agg_hot_functions_report.hot_functions_per_workload(
                        threshold=2
                    )

                    for workload_name in agg_hot_functions_report.workload_names(
                    ):
                        hot_func_data = hot_funcs[workload_name]
                        new_row = {
                            "Project": project_name,
                            "Config ID": config_id,
                            "NumHotFunctions": len(hot_func_data),
                            "HotFunctions": {hf.name for hf in hot_func_data}
                        }

                        entries.append(new_row)

        df = pd.DataFrame(entries)

        df.sort_values(["Project", "Config ID"], inplace=True)
        df.set_index(
            ["Project", "Config ID"],
            inplace=True,
        )

        if table_format == TableFormat.LATEX:
            df["HotFunctions"] = df["HotFunctions"].apply(
                lambda functions:
                {function.replace('_', "-") for function in functions}
            )

        kwargs: tp.Dict[str, tp.Any] = {}

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class HotFunctionConfigTableGenerator(
    TableGenerator, generator_name="hot-functions-agg", options=[]
):
    """Generator for `HotFunctionsConfigTable`."""

    def generate(self) -> tp.List[Table]:
        return [HotFunctionConfig(self.table_config, **self.table_kwargs)]
