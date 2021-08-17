"""Module for phasar global analysis evaluation table."""
import logging
import typing as tp

import pandas as pd
from scipy.stats import pearsonr, spearmanr
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
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, wrap_table_in_document, TableFormat

LOG = logging.Logger(__name__)


def insert_data_for_case_study_reports(report_files, name_id):
    if len(report_files) > 2 or len(report_files) > 2:
        print(f"report_files={report_files}")
        raise AssertionError

    if len(report_files) == 0 and len(report_files) == 0:
        # Skip projects where we don't have both reports
        return None

    if len(report_files) == 0 and len(report_files) == 1:
        # Skip projects where we don't have both reports
        return None

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
    cs_dict = {}
    if len(report_files) == 0:
        fill_in_empty(cs_dict)
    else:
        report_without = load_globals_without_report(report_files[0])
        if len(report_files) > 1:
            second_report_without = load_globals_with_report(report_files[1])
            report_without.extend_runs(second_report_without)
        fill_in_data(cs_dict, report_without)

    return pd.DataFrame.from_dict({name_id: cs_dict}, orient="index")


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
            if case_study.project_name in (
                'gawk', 'redis', 'x264', 'irssi', 'bitlbee'
            ):
                # Skip broken projects
                continue

            report_files_with = get_processed_revisions_files(
                case_study.project_name,
                GlobalsReportWith,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )
            report_files_without = get_processed_revisions_files(
                case_study.project_name,
                GlobalsReportWithout,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            def insert_data_if_present(report_files, name_id, cs_data):
                res = insert_data_for_case_study_reports(report_files, name_id)
                if res is not None:
                    cs_data.append(res)

            if case_study.project_name == 'libvpx':
                binary_name = "vpxenc"

                def is_from_binary(binary_name):
                    return lambda x: ReportFilename(
                        x
                    ).binary_name == binary_name

                insert_data_if_present(
                    list(
                        filter(is_from_binary(binary_name), report_files_with)
                    ), case_study.project_name + "-" + binary_name, cs_data
                )
                insert_data_if_present(
                    list(
                        filter(
                            lambda x: ReportFilename(x).binary_name ==
                            binary_name, report_files_without
                        )
                    ), case_study.project_name + "-" + binary_name, cs_data
                )
                binary_name = "vpxdec"
                insert_data_if_present(
                    list(
                        filter(
                            lambda x: ReportFilename(x).binary_name ==
                            binary_name, report_files_with
                        )
                    ), case_study.project_name + "-" + binary_name, cs_data
                )
                insert_data_if_present(
                    list(
                        filter(
                            lambda x: ReportFilename(x).binary_name ==
                            binary_name, report_files_without
                        )
                    ), case_study.project_name + "-" + binary_name, cs_data
                )
            else:
                insert_data_if_present(
                    report_files_with, case_study.project_name, cs_data
                )
                insert_data_if_present(
                    report_files_without, case_study.project_name, cs_data
                )

        df = pd.concat(cs_data)
        df = df.round(2)

        div_series = df[df['auto-Gs'] == 'No'].Time / df[df['auto-Gs'] == 'Yes'
                                                        ].Time
        rggs = df[df['auto-Gs'] == 'No']['#RGG']
        rho_p = pearsonr(rggs, div_series)

        mean_stddev = df["SDev %"].mean()

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
                f"Relative mean stddev {mean_stddev:.1f}$\%$"
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
