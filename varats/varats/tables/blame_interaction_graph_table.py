"""Module for writing bug-data metrics tables."""
import typing as tp

import pandas as pd
from tabulate import tabulate

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.table.table import Table, wrap_table_in_document, TableFormat
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    DUMMY_COMMIT,
)


class BlameInteractionGraphMetricsTable(Table):
    """Visualizes bug metrics of a project."""

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

        degree_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            cig = create_blame_interaction_graph(
                project_name, revision
            ).commit_interaction_graph
            commit_lookup = create_commit_lookup_helper(project_name)

            def filter_nodes(node: CommitRepoPair) -> bool:
                if node.commit_hash == DUMMY_COMMIT:
                    return False
                return bool(commit_lookup(node))

            data = pd.DataFrame([{
                "node_degree": cig.degree(node),
                "node_out_degree": cig.out_degree(node),
                "node_in_degree": cig.in_degree(node),
            } for node in cig.nodes if filter_nodes(node)])
            degree_data.append(
                pd.DataFrame.from_dict({
                    project_name: {
                        ("nodes", ""):
                            len(cig.nodes),
                        ("edges", ""):
                            len(cig.edges),
                        ("node degree", "mean"):
                            data["node_degree"].mean(),
                        ("node degree", "median"):
                            data["node_degree"].median(),
                        ("node degree", "min"):
                            data["node_degree"].min(),
                        ("node degree", "max"):
                            data["node_degree"].max(),
                        ("node out degree", "mean"):
                            data["node_out_degree"].mean(),
                        ("node out degree", "median"):
                            data["node_out_degree"].median(),
                        ("node out degree", "min"):
                            data["node_out_degree"].min(),
                        ("node out degree", "max"):
                            data["node_out_degree"].max(),
                        ("node in degree", "mean"):
                            data["node_in_degree"].mean(),
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
        if self.format in [
            TableFormat.latex, TableFormat.latex_booktabs, TableFormat.latex_raw
        ]:
            table = df.to_latex(bold_rows=True, multicolumn_format="c")
            return str(table) if table else ""
        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
