"""Module for phasar global analysis evaluation table."""
import logging
import typing as tp

import pandas as pd
from tabulate import tabulate

from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
    GlobalsReport,
)
from varats.jupyterhelper.file import (
    load_globals_with_report,
    load_globals_without_report,
)
from varats.paper_mgmt.case_study import (
    CaseStudy,
    get_case_study_file_name_filter,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, wrap_table_in_document, TableFormat

LOG = logging.Logger(__name__)


class PhasarGlobalsDataComparision(Table):
    """Comparision overview of gathered phasar globals analysis data to compare
    the effect of using gloabls analysis."""

    NAME = "phasar_globals"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_studies: tp.List[CaseStudy] = get_loaded_paper_config(
        ).get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []

        for case_study in case_studies:
            report_files_with = get_processed_revisions_files(
                case_study.project_name, GlobalsReportWith,
                get_case_study_file_name_filter(case_study)
            )
            report_files_without = get_processed_revisions_files(
                case_study.project_name, GlobalsReportWithout,
                get_case_study_file_name_filter(case_study)
            )

            if len(report_files_with) > 1 or len(report_files_without) > 1:
                print(f"{report_files_with=}")
                raise AssertionError

            if len(report_files_with) == 0 or len(report_files_without) == 0:
                # Skip projects where we don't have both reports
                continue

            def fill_in_data(
                cs_dict: tp.Dict[str, tp.Any], report: GlobalsReport
            ) -> None:
                cs_dict["auto-Gs"] = report.auto_globals

                cs_dict["#agc"] = report.num_analyzed_global_ctors
                cs_dict["#agd"] = report.num_analyzed_global_dtors
                cs_dict["#g-distinct"] = report.num_global_distrinct_types
                cs_dict["#g-int"] = report.num_global_int_typed
                cs_dict["#g-uses"] = report.num_global_uses
                cs_dict["#g-vars"] = report.num_global_vars
                cs_dict["#globals"] = report.num_globals
                cs_dict["#ntvas"] = report.num_non_top_vals_at_start
                cs_dict["#ntvae"] = report.num_non_top_vals_at_end
                cs_dict["#RGG"] = report.num_required_globals_generation

                cs_dict["Time"] = report.runtime_in_secs.mean
                cs_dict["Stddev"] = report.runtime_in_secs.stddev
                cs_dict["Runs"] = report.runs

            # Handle with
            report_with = load_globals_with_report(report_files_with[0])
            cs_dict = {}
            fill_in_data(cs_dict, report_with)

            cs_data.append(
                pd.DataFrame.from_dict({case_study.project_name: cs_dict},
                                       orient="index")
            )

            # Handle without
            report_without = load_globals_without_report(
                report_files_without[0]
            )

            cs_dict = {}
            fill_in_data(cs_dict, report_without)

            cs_data.append(
                pd.DataFrame.from_dict({case_study.project_name: cs_dict},
                                       orient="index")
            )

        df = pd.concat(cs_data).sort_index()
        df = df.round(2)
        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            table = df.to_latex(
                bold_rows=True, multicolumn_format="c", multirow=True
            )
            return str(table) if table else ""
        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
