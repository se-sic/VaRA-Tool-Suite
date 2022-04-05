"""Module for writing bug-data metrics tables."""
import typing as tp

import networkx as nx
import pandas as pd
from benchbuild.utils.cmd import git

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    AIGNodeAttrs,
    create_file_based_interaction_graph,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.project.project_util import get_local_project_git
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import FullCommitHash


def _generate_graph_table(
    case_studies: tp.List[CaseStudy],
    graph_generator: tp.Callable[[str, FullCommitHash], nx.DiGraph],
    table_format: TableFormat, wrap_table: bool
) -> str:
    degree_data: tp.List[pd.DataFrame] = []
    for case_study in case_studies:
        project_name = case_study.project_name
        project_git = git["-C", get_local_project_git(project_name).path]
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            continue

        graph = graph_generator(project_name, revision)

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in graph.nodes:
            nodes.append(({
                "node_degree": graph.degree(node),
                "node_out_degree": graph.out_degree(node),
                "node_in_degree": graph.in_degree(node),
            }))

        data = pd.DataFrame(nodes)
        degree_data.append(
            pd.DataFrame.from_dict({
                project_name: {
                    ("commits", ""):
                        int(project_git("rev-list", "--count", revision.hash)),
                    ("authors", ""):
                        len(
                            project_git("shortlog", "-s", "--all").splitlines()
                        ),
                    ("nodes", ""):
                        len(graph.nodes),
                    ("edges", ""):
                        len(graph.edges),
                    ("node degree", "mean"):
                        data["node_degree"].mean(),
                    ("node degree", "median"):
                        data["node_degree"].median(),
                    ("node degree", "min"):
                        data["node_degree"].min(),
                    ("node degree", "max"):
                        data["node_degree"].max(),
                    ("node out degree", "median"):
                        data["node_out_degree"].median(),
                    ("node out degree", "min"):
                        data["node_out_degree"].min(),
                    ("node out degree", "max"):
                        data["node_out_degree"].max(),
                    ("node in degree", "median"):
                        data["node_in_degree"].median(),
                    ("node in degree", "min"):
                        data["node_in_degree"].min(),
                    ("node in degree", "max"):
                        data["node_in_degree"].max(),
                }
            },
                                   orient="index")
        )

    df = pd.concat(degree_data).round(2)

    kwargs: tp.Dict[str, tp.Any] = {"bold_rows": True}
    if table_format.is_latex():
        kwargs["multicolumn_format"] = "c"
        kwargs["multirow"] = True

    return dataframe_to_table(
        df, table_format, wrap_table, wrap_landscape=True, **kwargs
    )


class CommitInteractionGraphMetricsTable(Table, table_name="cig_metrics_table"):
    """Commit interaction graph statistics in table form."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:

        def create_graph(
            project_name: str, revision: FullCommitHash
        ) -> nx.DiGraph:
            return create_blame_interaction_graph(project_name, revision
                                                 ).commit_interaction_graph()

        return _generate_graph_table(
            self.table_kwargs["case_study"], create_graph, table_format,
            wrap_table
        )


class CommitInteractionGraphMetricsTableGenerator(
    TableGenerator,
    generator_name="cig-metrics-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a cig-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            CommitInteractionGraphMetricsTable(
                self.table_config, **self.table_kwargs
            )
        ]


class AuthorInteractionGraphMetricsTable(Table, table_name="aig_metrics_table"):
    """Author interaction graph statistics in table form."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:

        def create_graph(
            project_name: str, revision: FullCommitHash
        ) -> nx.DiGraph:
            return create_blame_interaction_graph(project_name, revision
                                                 ).author_interaction_graph()

        return _generate_graph_table(
            self.table_kwargs["case_study"], create_graph, table_format,
            wrap_table
        )


class AuthorInteractionGraphMetricsTableGenerator(
    TableGenerator,
    generator_name="aig-metrics-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates an aig-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            AuthorInteractionGraphMetricsTable(
                self.table_config, **self.table_kwargs
            )
        ]


class CommitAuthorInteractionGraphMetricsTable(
    Table, table_name="caig_metrics_table"
):
    """Commit-Author interaction graph statistics in table form."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:

        def create_graph(
            project_name: str, revision: FullCommitHash
        ) -> nx.DiGraph:
            return create_blame_interaction_graph(
                project_name, revision
            ).commit_author_interaction_graph()

        return _generate_graph_table(
            self.table_kwargs["case_study"], create_graph, table_format,
            wrap_table
        )


class CommitAuthorInteractionGraphMetricsTableGenerator(
    TableGenerator,
    generator_name="caig-metrics-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a caig-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            CommitAuthorInteractionGraphMetricsTable(
                self.table_config, **self.table_kwargs
            )
        ]


class AuthorBlameVsFileDegreesTable(
    Table, table_name="aig_file_vs_blame_degrees_table"
):
    """Table showing authors with the highest author interaction graph node
    degrees."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]

        project_name: str = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise TableDataEmpty()

        blame_aig = create_blame_interaction_graph(project_name, revision
                                                  ).author_interaction_graph()
        file_aig = create_file_based_interaction_graph(
            project_name, revision
        ).author_interaction_graph()

        blame_nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in blame_aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, blame_aig.nodes[node])

            blame_neighbors = set(blame_aig.successors(node)
                                 ).union(blame_aig.predecessors(node))
            file_neighbors = set(file_aig.successors(node)
                                ).union(file_aig.predecessors(node))
            blame_nodes.append(({
                "author": f"{node_attrs['author']}",
                "blame_num_commits": node_attrs['num_commits'],
                "blame_node_degree": blame_aig.degree(node),
                "author_diff": len(blame_neighbors.difference(file_neighbors))
            }))
        blame_data = pd.DataFrame(blame_nodes)
        blame_data.set_index("author", inplace=True)

        file_nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in file_aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, file_aig.nodes[node])
            file_nodes.append(({
                "author": f"{node_attrs['author']}",
                "file_num_commits": node_attrs['num_commits'],
                "file_node_degree": file_aig.degree(node)
            }))
        file_data = pd.DataFrame(file_nodes)
        file_data.set_index("author", inplace=True)

        degree_data = blame_data.join(file_data, how="outer")

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["index"] = True
            kwargs["multicolumn_format"] = "c"
            kwargs["multirow"] = True

        return dataframe_to_table(
            degree_data,
            table_format,
            wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class AuthorBlameVsFileDegreesTableGenerator(
    TableGenerator,
    generator_name="aig-file-vs-blame-degrees-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates an aig-file-vs-blame-degrees table for the selected case
    study(ies)."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            AuthorBlameVsFileDegreesTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
