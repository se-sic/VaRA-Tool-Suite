"""Tables comparing commit-interaction graphs across analyses."""

import typing as tp

import click
import pandas as pd

from varats.data.reports.commit_interaction_comparison import (
    ALLOWED_ANALYSIS_COMPARISONS,
    AnalysisComparison,
    graph_summary,
    load_comparison_graphs,
    parse_analysis_comparison,
)
from varats.paper.case_study import CaseStudy
from varats.plot.plot import PlotDataEmpty
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY

REQUIRE_ANALYSIS_COMPARISON: CLIOptionTy = make_cli_option(
    "--comparison",
    type=click.Choice(
        sorted(ALLOWED_ANALYSIS_COMPARISONS),
        case_sensitive=False,
    ),
    required=True,
    metavar="COMPARISON",
    help=(
        "Analysis pair to compare, for example cfd-df; supported analysis "
        "names are cfd, cfc, and df."
    ),
)


def graph_summary_dataframe(
        case_studies: tp.Iterable[CaseStudy],
        comparison: AnalysisComparison,
) -> pd.DataFrame:
    """Build graph summaries for both analyses in every case study."""
    rows: tp.List[tp.Dict[str, tp.Any]] = []
    for case_study in case_studies:
        try:
            left_graph, right_graph = load_comparison_graphs(
                case_study,
                comparison,
            )
        except PlotDataEmpty:
            continue

        for analysis, graph in (
                (comparison.left_analysis.value, left_graph),
                (comparison.right_analysis.value, right_graph),
        ):
            summary = graph_summary(graph)
            rows.append({
                "Project": case_study.project_name,
                "Analysis": analysis,
                "Nodes": summary.nodes,
                "Unique edges": summary.edges,
                "Density": summary.density,
                "Degree Gini": summary.degree_gini,
            })

    return pd.DataFrame(rows, columns=[
        "Project",
        "Analysis",
        "Nodes",
        "Unique edges",
        "Density",
        "Degree Gini",
    ])


class CommitInteractionGraphSummaryTable(
    Table,
    table_name="commit_interaction_graph_summary_table",
):
    """Summarize both commit-interaction graphs for each project."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]
        comparison: AnalysisComparison = self.table_kwargs["comparison"]
        data = graph_summary_dataframe(case_studies, comparison)
        if data.empty:
            raise TableDataEmpty()

        data = data.round({"Density": 4, "Degree Gini": 4})
        style = data.style.hide(axis="index").format({
            "Density": "{:.4f}",
            "Degree Gini": "{:.4f}",
        })
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True

        return dataframe_to_table(
            data,
            table_format,
            style,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs,
        )


class CommitInteractionGraphSummaryTableGenerator(
    TableGenerator,
    generator_name="commit-interaction-graph-summary-table",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate a graph-level summary for selected case studies."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.table_kwargs.pop("comparison")
        )
        return [
            CommitInteractionGraphSummaryTable(
                self.table_config,
                case_studies=case_studies,
                comparison=comparison,
                **self.table_kwargs,
            )
        ]
