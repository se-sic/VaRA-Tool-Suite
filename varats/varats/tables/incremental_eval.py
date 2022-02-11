import typing as tp

import pandas as pd
from pylatex import Document, Package
from tabulate import tabulate

from varats.data.reports.incremental_reports import AnalysisType
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat


def __round_and_format_delta(base_line, increment) -> float:
    delta = increment - float(base_line)
    per_delta = delta / float(base_line) * 100
    per_delta = round(per_delta, 2)
    return per_delta


def create_df_for_report(report, project_name, t):
    cs_dict: tp.Dict[tp.Tuple[str, str], tp.Any] = {}

    cs_dict[("taint", "WPA")] = 42
    cs_dict[("taint", "INC")] = 21
    cs_dict[("taint", "delta")] = __round_and_format_delta(42, 21)

    cs_dict[("lca", "WPA")] = 42
    cs_dict[("lca", "INC")] = 53
    cs_dict[("lca", "delta")] = __round_and_format_delta(42, 53)

    cs_dict[("typestate", "WPA")] = 42
    cs_dict[("typestate", "INC")] = 41
    cs_dict[("typestate", "delta")] = __round_and_format_delta(42, 41)

    return pd.DataFrame.from_dict({project_name: cs_dict}, orient="index")


def _color_and_format_delta_cell(x) -> tp.Any:
    if x > 0:
        return "\\cellcolor{cellRed}" + str(x) + "\%"

    return "\\cellcolor{cellGreen}" + str(x) + "\%"


class PhasarGlobalsDataComparision(Table):
    """Comparision overview of gathered phasar-incremental analysis data to
    compare the effect of running an analysis incrementally."""

    NAME = "phasar_inc_overview"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_studies: tp.List[CaseStudy] = get_loaded_paper_config(
        ).get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []

        for case_study in case_studies:
            print(case_study)

            # binary = case_study.project_cls.binaries_for_revision(
            #     case_study.revisions[0]
            # )[0]

            report = None
            project_name = case_study.project_name

            cs_data.append(create_df_for_report(report, project_name, 1))

        df = pd.concat(cs_data)

        df[('taint', 'delta')
          ] = df[('taint', 'delta')].apply(_color_and_format_delta_cell)
        df[('lca', 'delta')
          ] = df[('lca', 'delta')].apply(_color_and_format_delta_cell)
        df[('typestate', 'delta')
          ] = df[('typestate', 'delta')].apply(_color_and_format_delta_cell)

        # Do final formating of column names
        df.rename(
            columns={
                "taint": "Taint",
                "lca": "LCA",
                "typestate": "Typestate",
                "WPA": "\\multicolumn{1}{c}{WPA}",
                "INC": "\\multicolumn{1}{c}{INC}",
                "delta": "\\multicolumn{1}{c}{$\\Delta$}"
            },
            inplace=True
        )

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            caption = ("TEST")
            table = df.to_latex(
                #index=True,
                escape=False,
                column_format="lccc|ccc|ccc",
                # bold_rows=True,
                multicolumn_format="c",
                multicolumn=True,
                # longtable=True,
                caption=caption
            )
            return str(table) if table else ""

        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:

        def add_doc_defs(doc: Document) -> None:
            doc.packages.append(Package('xcolor'))
            doc.packages.append(Package('colortbl'))
            doc.add_color("cellGreen", model="HTML", description="66ff33")
            doc.add_color("cellRed", model="HTML", description="ff3333")

        return wrap_table_in_document(
            table=table, landscape=True, document_decorator=add_doc_defs
        )
