"""Tables comparing commit-interaction graphs across analyses."""

import typing as tp

import click
import pandas as pd

from varats.data.reports.commit_interaction_comparison import (
    ALLOWED_ANALYSIS_COMPARISONS,
    AnalysisComparison,
    graph_summary,
    load_all_analysis_graphs,
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
                "Unique edges": summary.edges,
                "Density": summary.density,
                "gini coefficient": summary.gini,
            })

    return pd.DataFrame(rows, columns=[
        "Project",
        "Analysis",
        "Unique edges",
        "Density",
        "gini coefficient",
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


class CommitInteractionJaccardTable(Table, table_name="commit_interaction_jaccard_table"):
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


class CommitInteractionJaccardTableGenerator(TableGenerator, generator_name="commit-interaction-jaccard-table", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [CommitInteractionJaccardTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class EdgeRankAgreementSpearmanTable(Table, table_name="edge_rank_agreement_spearman_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        comparison = self.table_kwargs["comparison"]
        data = _comparison_rows(self.table_kwargs["case_studies"], comparison, shared_edge_weight_spearman)
        if data.empty:
            raise TableDataEmpty()
        style = data.style.hide(axis="index").format({"Spearman": "{:.3f}"})
        return dataframe_to_table(data, table_format, style, wrap_table=wrap_table, wrap_landscape=True)


class EdgeRankAgreementSpearmanTableGenerator(TableGenerator, generator_name="edge-rank-agreement-spearman-table", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [EdgeRankAgreementSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class NodeDegreeRankSpearmanTable(Table, table_name="node_degree_rank_spearman_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        comparison = self.table_kwargs["comparison"]
        data = _comparison_rows(self.table_kwargs["case_studies"], comparison, shared_node_degree_spearman)
        if data.empty:
            raise TableDataEmpty()
        style = data.style.hide(axis="index").format({"Spearman": "{:.3f}"})
        return dataframe_to_table(data, table_format, style, wrap_table=wrap_table, wrap_landscape=True)


class NodeDegreeRankSpearmanTableGenerator(TableGenerator, generator_name="node-degree-rank-spearman-table", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [NodeDegreeRankSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


def _display_item(item: object) -> str:
    """Use a compact commit hash where possible, otherwise the item name."""
    commit_hash = getattr(item, "commit_hash", None)
    if commit_hash is not None:
        return str(getattr(commit_hash, "hash", commit_hash))[:12]
    return str(item)


def _top_commit_table_data(case_studies: tp.Iterable[CaseStudy]) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        try:
            graphs = load_all_analysis_graphs(case_study)
        except PlotDataEmpty:
            continue
        ranked = {
            name: dict(top_ranked_items(unique_neighbor_degrees(graph), 10))
            for name, graph in graphs.items()
        }
        for rank in range(1, 11):
            rows.append({
                "Project": case_study.project_name,
                "Rank": rank,
                "CF-Direct": _display_item(next((n for n, r in ranked["cfd"].items() if r == rank), "—")),
                "CF-Collective": _display_item(next((n for n, r in ranked["cfc"].items() if r == rank), "—")),
                "Data-flow": _display_item(next((n for n, r in ranked["df"].items() if r == rank), "—")),
            })
    return pd.DataFrame(rows, columns=["Project", "Rank", "CF-Direct", "CF-Collective", "Data-flow"])


class TopNodeDegreeTable(Table, table_name="top_node_degree_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_commit_table_data(self.table_kwargs["case_studies"])
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopNodeDegreeTableGenerator(TableGenerator, generator_name="top-node-degree-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopNodeDegreeTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]


def _top_overlap_data(case_studies: tp.Iterable[CaseStudy], author_metric: tp.Optional[str] = None) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        try:
            graphs = load_all_analysis_graphs(case_study)
            if author_metric:
                graphs = {name: create_author_interaction_graph(
                    graph, case_study.project_name
                ) for name, graph in graphs.items()}
        except PlotDataEmpty:
            continue
        ranked = {}
        for name, graph in graphs.items():
            if author_metric:
                values = dict(graph.degree(weight="amount")) if author_metric == "degree" else author_centrality_dataframe(graph, graph, "eigenvector").set_index("Author")["Left centrality"].to_dict()
            else:
                values = unique_neighbor_degrees(graph)
            ranked[name] = set(item for item, _ in top_ranked_items(values, 10))
        rows.append({
            "Project": case_study.project_name,
            "CFD-CFC": f"{len(ranked['cfd'] & ranked['cfc'])}/10",
            "CFD-DF": f"{len(ranked['cfd'] & ranked['df'])}/10",
            "CFC-DF": f"{len(ranked['cfc'] & ranked['df'])}/10",
        })
    return pd.DataFrame(rows, columns=["Project", "CFD-CFC", "CFD-DF", "CFC-DF"])


class TopNodeDegreeOverlapTable(Table, table_name="top_node_degree_overlap_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(self.table_kwargs["case_studies"])
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopNodeDegreeOverlapTableGenerator(TableGenerator, generator_name="top-node-degree-overlap-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopNodeDegreeOverlapTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]


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


class AuthorDegreeSpearmanTable(AuthorCentralitySpearmanTable, table_name="author_degree_spearman_table"):
    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        kwargs["metric"] = "degree"
        super().__init__(*args, **kwargs)


class AuthorEigenvectorSpearmanTable(AuthorCentralitySpearmanTable, table_name="author_eigenvector_spearman_table"):
    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        kwargs["metric"] = "eigenvector"
        super().__init__(*args, **kwargs)


class AuthorDegreeSpearmanTableGenerator(TableGenerator, generator_name="author-degree-spearman-table", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [AuthorDegreeSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


class AuthorEigenvectorSpearmanTableGenerator(TableGenerator, generator_name="author-eigenvector-spearman-table", options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
    def generate(self) -> tp.List[Table]:
        case_studies = self.table_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(self.table_kwargs.pop("comparison"))
        return [AuthorEigenvectorSpearmanTable(self.table_config, case_studies=case_studies, comparison=comparison, **self.table_kwargs)]


def _top_author_table_data(
        case_studies: tp.Iterable[CaseStudy], metric: str,
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        try:
            commit_graphs = load_all_analysis_graphs(case_study)
        except PlotDataEmpty:
            continue
        author_graphs = {
            name: create_author_interaction_graph(graph, case_study.project_name)
            for name, graph in commit_graphs.items()
        }
        ranked = {}
        for name, graph in author_graphs.items():
            if metric == "degree":
                values = dict(graph.degree(weight="amount"))
            else:
                values = author_centrality_dataframe(graph, graph, "eigenvector")
                values = values.set_index("Author")["Left centrality"].to_dict()
            ranked[name] = dict(top_ranked_items(values, 10))
        for rank in range(1, 11):
            rows.append({
                "Project": case_study.project_name,
                "Rank": rank,
                "CF-Direct": _display_item(next((n for n, r in ranked["cfd"].items() if r == rank), "—")),
                "CF-Collective": _display_item(next((n for n, r in ranked["cfc"].items() if r == rank), "—")),
                "Data-flow": _display_item(next((n for n, r in ranked["df"].items() if r == rank), "—")),
            })
    return pd.DataFrame(rows, columns=["Project", "Rank", "CF-Direct", "CF-Collective", "Data-flow"])


class TopAuthorDegreeTable(Table, table_name="top_author_degree_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_author_table_data(self.table_kwargs["case_studies"], "degree")
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorEigenvectorTable(Table, table_name="top_author_eigenvector_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_author_table_data(self.table_kwargs["case_studies"], "eigenvector")
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorDegreeTableGenerator(TableGenerator, generator_name="top-author-degree-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopAuthorDegreeTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]


class TopAuthorEigenvectorTableGenerator(TableGenerator, generator_name="top-author-eigenvector-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopAuthorEigenvectorTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]


class TopAuthorDegreeOverlapTable(Table, table_name="top_author_degree_overlap_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(self.table_kwargs["case_studies"], "degree")
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorEigenvectorOverlapTable(Table, table_name="top_author_eigenvector_overlap_table"):
    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        data = _top_overlap_data(self.table_kwargs["case_studies"], "eigenvector")
        if data.empty:
            raise TableDataEmpty()
        return dataframe_to_table(data, table_format, data.style.hide(axis="index"), wrap_table=wrap_table, wrap_landscape=True)


class TopAuthorDegreeOverlapTableGenerator(TableGenerator, generator_name="top-author-degree-overlap-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopAuthorDegreeOverlapTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]


class TopAuthorEigenvectorOverlapTableGenerator(TableGenerator, generator_name="top-author-eigenvector-overlap-table", options=[REQUIRE_MULTI_CASE_STUDY]):
    def generate(self) -> tp.List[Table]:
        return [TopAuthorEigenvectorOverlapTable(self.table_config, case_studies=self.table_kwargs.pop("case_study"), **self.table_kwargs)]
