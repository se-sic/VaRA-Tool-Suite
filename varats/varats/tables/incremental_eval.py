import typing as tp

import numpy as np
import pandas as pd
from benchbuild.utils.cmd import git
from pylatex import Document, Package
from scipy.stats import gmean
from tabulate import tabulate

from varats.data.reports.incremental_reports import (
    AnalysisType,
    IncrementalReport,
)
from varats.jupyterhelper.file import load_incremental_report
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import (
    wrap_table_in_latex_document,
    dataframe_to_table,
)
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import calc_repo_loc


def _round_and_format_delta(base_line: float, increment: float) -> float:
    delta = increment - float(base_line)
    per_delta = delta / float(base_line) * 100
    per_delta = round(per_delta, 2)
    return per_delta


def create_df_for_report(report: IncrementalReport, project_name, t):
    cs_dict: tp.Dict[tp.Tuple[str, str], tp.Any] = {}

    cs_dict[("taint", "WPA")] = report.ifds_taint_timings().total_wpa()
    cs_dict[("taint", "INC")] = report.ifds_taint_timings().total_incremental()
    cs_dict[("taint", "delta")] = 0

    cs_dict[("lca", "WPA")] = report.ide_lca_timings().total_wpa()
    cs_dict[("lca", "INC")] = report.ide_lca_timings().total_incremental()
    cs_dict[("lca", "delta")] = 0

    cs_dict[("typestate", "WPA")] = report.ide_typestate_timings().total_wpa()
    cs_dict[("typestate", "INC")
           ] = report.ide_typestate_timings().total_incremental()
    cs_dict[("typestate", "delta")] = 0

    return pd.DataFrame.from_dict({project_name: cs_dict}, orient="index")


from random import seed, randint

seed(1)


def create_df_for_report_fake(project_name):

    cs_dict: tp.Dict[tp.Tuple[str, str], tp.Any] = {}

    cs_dict[("taint", "WPA")] = randint(1, 100)
    cs_dict[("taint", "INC")] = randint(1, 100)
    cs_dict[("taint", "delta")] = 0

    cs_dict[("lca", "WPA")] = randint(1, 100)
    cs_dict[("lca", "INC")] = randint(1, 100)
    cs_dict[("lca", "delta")] = 0

    cs_dict[("typestate", "WPA")] = randint(1, 100)
    cs_dict[("typestate", "INC")] = randint(1, 100)
    cs_dict[("typestate", "delta")] = 0

    return pd.DataFrame.from_dict({project_name: cs_dict}, orient="index")


def _color_and_format_delta_cell(x) -> tp.Any:
    if x > 0:
        return "\\cellcolor{cellRed}" + str(x) + "\%"

    return "\\cellcolor{cellGreen}" + str(x) + "\%"


class PhasarIncrementalDataComparision(Table, table_name="phasar_inc_overview"):
    """Comparision overview of gathered phasar-incremental analysis data to
    compare the effect of running an analysis incrementally."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = get_loaded_paper_config(
        ).get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []

        for case_study in case_studies:
            report_files = get_processed_revisions_files(
                case_study.project_name, IncrementalReport,
                get_case_study_file_name_filter(case_study)
            )
            print(f"{report_files=}")

            # binary = case_study.project_cls.binaries_for_revision(
            #     case_study.revisions[0]
            # )[0]

            project_name = case_study.project_name

            current_cs_data: tp.List[pd.DataFrame] = []

            for report_file in report_files:
                report = load_incremental_report(report_file)
                print(report.ide_lca_timings())
                # cs_data.append(create_df_for_report(report, project_name, 1))
                current_cs_data.append(
                    create_df_for_report(report, project_name, 1)
                )

            # current_cs_data.append(create_df_for_report_fake(project_name))
            # current_cs_data.append(create_df_for_report_fake(project_name))
            # current_cs_data.append(create_df_for_report_fake(project_name))
            # current_cs_data.append(create_df_for_report_fake(project_name))

            df = pd.concat(current_cs_data)
            df = df.agg(['mean'])
            df.rename(index={'mean': project_name}, inplace=True)

            df[("taint", "delta")] = _round_and_format_delta(
                df[("taint", "WPA")], df[("taint", "INC")]
            )
            df[
                ("lca", "delta")
            ] = _round_and_format_delta(df[("lca", "WPA")], df[("lca", "INC")])
            df[("typestate", "delta")] = _round_and_format_delta(
                df[("typestate", "WPA")], df[("typestate", "INC")]
            )

            df[("total", "WPA")] = gmean([
                df[("taint", "WPA")], df[("lca", "WPA")],
                df[("typestate", "WPA")]
            ])
            df[("total", "INC")] = gmean([
                df[("taint", "INC")], df[("lca", "INC")],
                df[("typestate", "INC")]
            ])
            df[("total", "delta")] = _round_and_format_delta(
                df[("total", "WPA")], df[("total", "INC")]
            )

            cs_data.append(df)

        df = pd.concat(cs_data)
        df = df.round(2)

        df[('taint', 'delta')
          ] = df[('taint', 'delta')].apply(_color_and_format_delta_cell)
        df[('lca', 'delta')
          ] = df[('lca', 'delta')].apply(_color_and_format_delta_cell)
        df[('typestate', 'delta')
          ] = df[('typestate', 'delta')].apply(_color_and_format_delta_cell)
        df[('total', 'delta')
          ] = df[('total', 'delta')].apply(_color_and_format_delta_cell)

        # Do final formating of column names
        df.rename(
            columns={
                "taint": "Taint",
                "lca": "LCA",
                "typestate": "Typestate",
                "total": "Total",
                "WPA": "\\multicolumn{1}{c}{WPA}",
                "INC": "\\multicolumn{1}{c}{INC}",
                "delta": "\\multicolumn{1}{c}{$\\Delta$}"
            },
            inplace=True
        )

        table_kwargs: tp.Dict[str, tp.Any] = {"bold_rows": True}
        if table_format.is_latex():
            df.style.format('j')
            caption = ("TEST")

            # table_kwargs["index"] = True
            table_kwargs["escape"] = False
            table_kwargs["column_format"] = "lccc|ccc|ccc|ccc"
            # table_kwargs["# bold_rows"] = True
            table_kwargs["multicolumn_format"] = "c"
            table_kwargs["multicolumn"] = True,
            # table_kwargs["longtable"] = True
            table_kwargs["caption"] = caption
            # table_kwargs["float_format"] = '{:0.2f}'.format
            table_kwargs["float_format"] = '%.2f'

        def add_doc_defs(doc: Document) -> None:
            doc.packages.append(Package('xcolor'))
            doc.packages.append(Package('colortbl'))
            doc.add_color("cellGreen", model="HTML", description="66ff33")
            doc.add_color("cellRed", model="HTML", description="ff3333")

        return dataframe_to_table(
            df,
            table_format,
            wrap_table,
            wrap_landscape=True,
            document_decorator=add_doc_defs,
            **table_kwargs
        )


class PhasarIncrementalDataComparisionGenerator(
    TableGenerator, generator_name="phasar-inc-overview", options=[]
):

    def generate(self) -> tp.List[Table]:
        return [
            PhasarIncrementalDataComparision(
                self.table_config, **self.table_kwargs
            )
        ]


class PhasarIncMetricsTable(Table, table_name="phasar_inc_cs_metrics"):
    """Table showing some general information about the case studies in a paper
    config."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            project_cls = get_project_cls_by_name(project_name)
            project_repo = get_local_project_git(project_name)
            project_path = project_repo.path[:-5]
            project_git = git["-C", project_path]

            revision = self.table_kwargs.get("revisions", {}).get(
                case_study.project_name, None
            )
            revisions = case_study.revisions
            if not revision and len(revisions) == 1:
                revision = revisions[0]
            rev_range = revision.hash if revision else "HEAD"

            cs_dict = {
                project_name: {
                    "Domain":
                        str(project_cls.DOMAIN)[0].upper() +
                        str(project_cls.DOMAIN)[1:],
                    "LOC":
                        calc_repo_loc(project_repo, rev_range),
                    "Commits":
                        int(project_git("rev-list", "--count", rev_range)),
                    # "Authors":
                    #     len(
                    #         project_git("shortlog", "-s",
                    #                     rev_range).splitlines()
                    #     )
                    "Samples":
                        len(case_study.revisions)
                }
            }
            # if revision:
            #     cs_dict[project_name]["Revision"] = revision.short_hash

            cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        df = pd.concat(cs_data).sort_index()

        table_kwargs: tp.Dict[str, tp.Any] = {"bold_rows": True}
        if table_format.is_latex():
            table_kwargs["multicolumn_format"] = "c"
            table_kwargs["multirow"] = True

        return dataframe_to_table(
            df, table_format, wrap_table, wrap_landscape=True, **table_kwargs
        )


class PhasarIncMetricsTableGenerator(
    TableGenerator, generator_name="phasar-inc-cs-metrics", options=[]
):

    def generate(self) -> tp.List[Table]:
        return [PhasarIncMetricsTable(self.table_config, **self.table_kwargs)]
