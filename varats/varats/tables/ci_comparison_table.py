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
    shared_edge_weight_spearman,
    shared_node_degree_spearman,
    author_centrality_dataframe,
    author_centrality_spearman,
    create_author_interaction_graph,
    edge_overlap,
    top_ranked_items,
    unique_neighbor_degrees,
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
                "Edges": summary.edges,
                "Density": summary.density,
                "gini coefficient": summary.gini,
            })

    return pd.DataFrame(rows, columns=[
        "Project",
        "Analysis",
        "Edges",
        "Density",
        "gini coefficient",
    ])


class CommitInteractionGraphSummaryTable(
    Table,
    table_name="cig-graph-comparison",
):
    """Summarize both commit-interaction graphs for each project."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]
        comparison: AnalysisComparison = self.table_kwargs["comparison"]
        data = graph_summary_dataframe(case_studies, comparison)
        if data.empty:
            raise TableDataEmpty()

        data = data.round({"Density": 4, "gini coefficient": 4})
        style = data.style.hide(axis="index").format({
            "Density": "{:.4f}",
            "gini coefficient": "{:.4f}",
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
    generator_name="cig-graph-comparison",
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


def _comparison_rows(
        case_studies: tp.Iterable[CaseStudy],
        comparison: AnalysisComparison,
        metric: tp.Callable[[object, object], float],
        label: str = "Spearman",
) -> pd.DataFrame:
    rows: tp.List[tp.Dict[str, tp.Any]] = []
    for case_study in case_studies:
        try:
            left, right = load_comparison_graphs(case_study, comparison)
        except PlotDataEmpty:
            continue
        rows.append({
            "Project": case_study.project_name,
            "Comparison": (
                f"{comparison.left_analysis.value} vs "
                f"{comparison.right_analysis.value}"
            ),
            label: metric(left, right),
        })
    return pd.DataFrame(rows, columns=["Project", "Comparison", label])


class CommitInteractionJaccardTable(Table, table_name="cig-edge-jaccard"):
    """Jaccard edge overlap as percentages."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        rows = []
        comparison = self.table_kwargs["comparison"]
        for case_study in self.table_kwargs["case_studies"]:
            try:
                left, right = load_comparison_graphs(case_study, comparison)
            except PlotDataEmpty:
                continue
            overlap = edge_overlap(left, right)
            rows.append({
                "Project": case_study.project_name,
                "Comparison": f"{comparison.left_analysis.value} vs {comparison.right_analysis.value}",
                "Jaccard (%)": 100 * overlap.jaccard,
            })
        data = pd.DataFrame(rows, columns=["Project", "Comparison", "Jaccard (%)"])
        if data.empty:
            raise TableDataEmpty()
        style = data.style.hide(axis="index").format({"Jaccard (%)": "{:.1f}%"})
        return dataframe_to_table(data, table_format, style, wrap_table=wrap_table, wrap_landscape=True)


class CommitInteractionJaccardTableGenerator(TableGenerator, generator_name="cig-edge-jaccard", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [CommitInteractionJaccardTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class EdgeRankAgreementSpearmanTable(Table, table_name="cig-edge-weight-spearman"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        comparison = self.table_kwargs["comparison"]
        data = _comparison_rows(self.table_kwargs["case_studies"], comparison, shared_edge_weight_spearman)
        if data.empty:
            raise TableDataEmpty()
        style = data.style.hide(axis="index").format({"Spearman": "{:.3f}"})
        return dataframe_to_table(data, table_format, style, wrap_table=wrap_table, wrap_landscape=True)


class EdgeRankAgreementSpearmanTableGenerator(TableGenerator, generator_name="cig-edge-weight-spearman", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [EdgeRankAgreementSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class NodeDegreeRankSpearmanTable(Table, table_name="cig-node-degree-spearman"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        comparison = self.table_kwargs["comparison"]
        data = _comparison_rows(self.table_kwargs["case_studies"], comparison, shared_node_degree_spearman)
        if data.empty:
            raise TableDataEmpty()
        style = data.style.hide(axis="index").format({"Spearman": "{:.3f}"})
        return dataframe_to_table(data, table_format, style, wrap_table=wrap_table, wrap_landscape=True)


class NodeDegreeRankSpearmanTableGenerator(TableGenerator, generator_name="cig-node-degree-spearman", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [NodeDegreeRankSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


def _top_overlap_data(
        case_studies: tp.Iterable[CaseStudy],
        comparison: AnalysisComparison,
        author_metric: tp.Optional[str] = None,
) -> pd.DataFrame:
    rows = []
    left_name = comparison.left_analysis.value.lower()
    right_name = comparison.right_analysis.value.lower()
    comparison_name = (
        f"{comparison.left_analysis.value}-"
        f"{comparison.right_analysis.value}"
    )
    for case_study in case_studies:
        try:
            left_graph, right_graph = load_comparison_graphs(
                case_study,
                comparison,
            )
        except PlotDataEmpty:
            continue
        graphs = {
            left_name: left_graph,
            right_name: right_graph,
        }
        if author_metric:
            graphs = {
                name: create_author_interaction_graph(
                    graph, case_study.project_name
                )
                for name, graph in graphs.items()
            }

        ranked = {}
        for name in (left_name, right_name):
            graph = graphs[name]
            if author_metric:
                values = dict(graph.degree(weight="amount")) if author_metric == "degree" else author_centrality_dataframe(graph, graph, "eigenvector").set_index("Author")["Left centrality"].to_dict()
            else:
                values = unique_neighbor_degrees(graph)
            ranked[name] = set(item for item, _ in top_ranked_items(values, 10))
        rows.append({
            "Project": case_study.project_name,
            comparison_name: f"{len(ranked[left_name] & ranked[right_name])}/10",
        })
    return pd.DataFrame(rows, columns=["Project", comparison_name])


class TopNodeDegreeOverlapTable(Table, table_name="cig-node-degree-top10"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(
            self.table_kwargs["case_studies"],
            self.table_kwargs["comparison"],
        )
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopNodeDegreeOverlapTableGenerator(TableGenerator, generator_name="cig-node-degree-top10", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [TopNodeDegreeOverlapTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class AuthorCentralitySpearmanTable(Table, table_name="author_centrality_spearman_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        comparison = self.table_kwargs["comparison"]
        metric = self.table_kwargs["metric"]
        rows = []
        for case_study in self.table_kwargs["case_studies"]:
            try:
                left, right = load_comparison_graphs(case_study, comparison)
            except PlotDataEmpty:
                continue
            rows.append({
                "Project": case_study.project_name,
                "Comparison": f"{comparison.left_analysis.value} vs {comparison.right_analysis.value}",
                "Spearman": author_centrality_spearman(
                    left, right, case_study.project_name, metric
                ),
            })
        data = pd.DataFrame(rows, columns=["Project", "Comparison", "Spearman"])
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index").format({"Spearman": "{:.3f}"}), wrap_table=wrap_table, wrap_landscape=True)


class AuthorDegreeSpearmanTable(AuthorCentralitySpearmanTable, table_name="aig-degree-spearman"):
    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        kwargs["metric"] = "degree"
        super().__init__(*args, **kwargs)


class AuthorEigenvectorSpearmanTable(AuthorCentralitySpearmanTable, table_name="aig-eigen-spearman"):
    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        kwargs["metric"] = "eigenvector"
        super().__init__(*args, **kwargs)


class AuthorDegreeSpearmanTableGenerator(TableGenerator, generator_name="aig-degree-spearman", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [AuthorDegreeSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class AuthorEigenvectorSpearmanTableGenerator(TableGenerator, generator_name="aig-eigen-spearman", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [AuthorEigenvectorSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class TopAuthorDegreeOverlapTable(Table, table_name="aig-degree-top10"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(
            self.table_kwargs["case_studies"],
            self.table_kwargs["comparison"],
            "degree",
        )
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorEigenvectorOverlapTable(Table, table_name="aig-eigen-top10"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(
            self.table_kwargs["case_studies"],
            self.table_kwargs["comparison"],
            "eigenvector",
        )
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorDegreeOverlapTableGenerator(TableGenerator, generator_name="aig-degree-top10", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [TopAuthorDegreeOverlapTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class TopAuthorEigenvectorOverlapTableGenerator(TableGenerator, generator_name="aig-eigen-top10", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [TopAuthorEigenvectorOverlapTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]
