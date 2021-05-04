"""Module for writing bug-data metrics tables."""
import typing as tp

import networkx as nx
import pandas as pd
from benchbuild.utils.cmd import git
from tabulate import tabulate

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import get_local_project_git
from varats.table.table import Table, wrap_table_in_document, TableFormat


def _generate_graph_table(
    case_studies: tp.List[CaseStudy], graph_generator: tp.Callable[[str, str],
                                                                   nx.DiGraph],
    table_format: TableFormat
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
                        int(project_git("rev-list", "--count", "HEAD")),
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
    if table_format in [
        TableFormat.latex, TableFormat.latex_booktabs, TableFormat.latex_raw
    ]:
        table = df.to_latex(bold_rows=True, multicolumn_format="c")
        return str(table) if table else ""
    return tabulate(df, df.columns, table_format.value)


class CommitInteractionGraphMetricsTable(Table):
    """Commit interaction graph statistics in table form."""

    NAME = "cig_metrics_table"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        if "project" not in self.table_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.table_kwargs:
                case_studies = [self.table_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.table_kwargs["project"]
                )

        def create_graph(project_name: str, revision: str) -> nx.DiGraph:
            return create_blame_interaction_graph(project_name, revision
                                                 ).commit_interaction_graph()

        return _generate_graph_table(case_studies, create_graph, self.format)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)


class AuthorInteractionGraphMetricsTable(Table):
    """Author interaction graph statistics in table form."""

    NAME = "aig_metrics_table"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        if "project" not in self.table_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.table_kwargs:
                case_studies = [self.table_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.table_kwargs["project"]
                )

        def create_graph(project_name: str, revision: str) -> nx.DiGraph:
            return create_blame_interaction_graph(project_name, revision
                                                 ).author_interaction_graph()

        return _generate_graph_table(case_studies, create_graph, self.format)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)


class CommitAuthorInteractionGraphMetricsTable(Table):
    """Commit-Author interaction graph statistics in table form."""

    NAME = "caig_metrics_table"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        if "project" not in self.table_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.table_kwargs:
                case_studies = [self.table_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.table_kwargs["project"]
                )

        def create_graph(project_name: str, revision: str) -> nx.DiGraph:
            return create_blame_interaction_graph(
                project_name, revision
            ).commit_author_interaction_graph()

        return _generate_graph_table(case_studies, create_graph, self.format)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
