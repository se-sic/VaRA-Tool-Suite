"""Module for phasar global analysis evaluation table."""
import logging
import typing as tp
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr
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
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import ProjectBinaryWrapper
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat

LOG = logging.Logger(__name__)


def create_df_for_report(
    report: tp.Optional[tp.Any], name_id: str
) -> pd.DataFrame:
    """Creates a dataframe that inclues all relevant information of the
    report."""

    def fill_in_data(
        cs_dict: tp.Dict[str, tp.Any], report: GlobalsReport
    ) -> None:
        cs_dict["auto-Gs"] = "Yes" if report.auto_globals else "No"

        cs_dict["#agc"] = report.num_analyzed_global_ctors
        cs_dict["#agd"] = report.num_analyzed_global_dtors
        cs_dict["#g-distinct"] = report.num_global_distrinct_types
        cs_dict["#g-int"] = report.num_global_int_typed
        cs_dict["#g-uses"] = report.num_global_uses
        cs_dict["#globals"] = report.num_globals
        cs_dict["#ntvas"] = report.num_non_top_vals_at_start
        cs_dict["#ntvae"] = report.num_non_top_vals_at_end
        cs_dict["#RGG"] = report.num_required_globals_generation

        cs_dict["Time"] = float(f"{report.runtime_in_secs.mean:.2f}")
        perc_stddev = (
            report.runtime_in_secs.stddev / report.runtime_in_secs.mean * 100
        )
        cs_dict["Stddev"] = float(f"{report.runtime_in_secs.stddev:.2f}")
        cs_dict["SDev %"] = float(f"{perc_stddev:.1f}")
        cs_dict["Runs"] = report.runs

    def fill_in_empty(cs_dict: tp.Dict[str, tp.Any]) -> None:
        cs_dict["auto-Gs"] = "-"

        cs_dict["#agc"] = "-"
        cs_dict["#agd"] = "-"
        cs_dict["#g-distinct"] = "-"
        cs_dict["#g-int"] = "-"
        cs_dict["#g-uses"] = "-"
        cs_dict["#globals"] = "-"
        cs_dict["#ntvas"] = "-"
        cs_dict["#ntvae"] = "-"
        cs_dict["#RGG"] = "-"

        cs_dict["Time"] = "-"
        cs_dict["Stddev"] = "-"
        cs_dict["SDev %"] = "-"
        cs_dict["Runs"] = "-"

    # Handle list
    cs_dict: tp.Dict[str, tp.Any] = {}
    if report:
        fill_in_data(cs_dict, report)
    else:
        fill_in_empty(cs_dict)

    return pd.DataFrame.from_dict({name_id: cs_dict}, orient="index")


def filter_report_paths_binary(
    report_files: tp.List[Path], binary: ProjectBinaryWrapper
) -> tp.List[Path]:
    return list(
        filter(
            lambda x: ReportFilename(x).binary_name == binary.name, report_files
        )
    )


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

        for case_study in sorted(case_studies, key=lambda x: x.project_name):
            report_files_with = get_processed_revisions_files(
                case_study.project_name, GlobalsReportWith,
                get_case_study_file_name_filter(case_study)
            )
            report_files_without = get_processed_revisions_files(
                case_study.project_name, GlobalsReportWithout,
                get_case_study_file_name_filter(case_study)
            )

            if len(report_files_with) > 1 or len(report_files_without) > 1:
                LOG.debug(f"report_files_with={report_files_with}")
                LOG.debug(f"report_files_without={report_files_with}")
                raise AssertionError("To many report files given!")

            def insert_data_if_present(
                report: tp.Optional[GlobalsReport], name_id: str,
                cs_data: tp.List[pd.DataFrame]
            ) -> None:
                res = create_df_for_report(report, name_id)
                if res is not None:
                    cs_data.append(res)

            if len(case_study.revisions) > 1:
                LOG.debug(
                    "This tabled is only designed for usage with one revision "
                    "but we found more. All revisions expect for the first "
                    "one are ignored."
                )

            for binary in case_study.project_cls.binaries_for_revision(
                case_study.revisions[0]
            ):
                if len(
                    case_study.project_cls.binaries_for_revision(
                        case_study.revisions[0]
                    )
                ) > 1:
                    unique_cs_name = case_study.project_name + "-" + binary.name
                else:
                    unique_cs_name = case_study.project_name

                # With
                report_files_with_for_binary = filter_report_paths_binary(
                    report_files_with, binary
                )

                report_with: tp.Optional[GlobalsReportWith] = None
                if report_files_with_for_binary:
                    report_with = load_globals_with_report(
                        report_files_with_for_binary[0]
                    )

                insert_data_if_present(report_with, unique_cs_name, cs_data)

                # Without
                report_files_without_for_binary = filter_report_paths_binary(
                    report_files_without, binary
                )

                report_without: tp.Optional[GlobalsReportWithout] = None
                if report_files_without_for_binary:
                    report_without = load_globals_without_report(
                        report_files_without_for_binary[0]
                    )

                insert_data_if_present(report_without, unique_cs_name, cs_data)

        df = pd.concat(cs_data)
        df = df.round(2)

        div_series = df[df['auto-Gs'] == 'No'].Time / df[df['auto-Gs'] == 'Yes'
                                                        ].Time
        rggs = df[df['auto-Gs'] == 'No']['#RGG']
        rho_p = pearsonr(rggs, div_series)

        mean_stddev = df[df["SDev %"] != '-']["SDev %"].mean()

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            caption = (
                "Pearson correlation coefficient between RGG and Speedup "
                "(TimeWithout / TimeWith) "
                f"is: $\\rho$ = {rho_p[0]:.3f} with a two-sided p-value of "
                f"{rho_p[1]:.3f}."
                f" In total we analyzed {len(rggs)} binaries from "
                f"{len(rggs)-1} different projects. "
                f"Relative mean stddev {mean_stddev:.1f}$\\%$"
            )
            table = df.to_latex(
                bold_rows=True,
                multicolumn_format="c",
                multirow=True,
                longtable=True,
                caption=caption
            )
            return str(table) if table else ""
        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
