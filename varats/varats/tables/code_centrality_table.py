"""Module for code centrality tables."""
import logging
import typing as tp
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.project.project_util import get_local_project_gits
from varats.table.table import Table, wrap_table_in_document, TableDataEmpty
from varats.table.tables import TableFormat
from varats.utils.git_util import (
    ChurnConfig,
    calc_commit_code_churn,
    create_commit_lookup_helper,
    CommitRepoPair,
    UNCOMMITTED_COMMIT_HASH,
)

LOG = logging.Logger(__name__)


class TopCentralCodeCommitsTable(Table):
    """Table showing commits with highest commit interaction graph node
    degrees."""

    NAME = "top_central_code_commits_table"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_study = self.table_kwargs["table_case_study"]
        num_commits = self.table_kwargs.get("num_commits", 10)

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise TableDataEmpty()

        churn_config = ChurnConfig.create_c_style_languages_config()
        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()
        commit_lookup = create_commit_lookup_helper(project_name)
        repo_lookup = get_local_project_gits(project_name)

        def filter_nodes(node: CommitRepoPair) -> bool:
            if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                return False
            return bool(commit_lookup(node))

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in cig.nodes:
            node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
            commit = node_attrs["commit"]
            if not filter_nodes(commit):
                continue
            _, insertions, _ = calc_commit_code_churn(
                Path(repo_lookup[commit.repository_name].path),
                commit.commit_hash, churn_config
            )
            if insertions == 0:
                LOG.warning(f"Churn for commit {commit} is 0.")
                insertions = 1
            nodes.append(({
                "commit_hash": commit.commit_hash.hash,
                "degree": cig.degree(node),
                "insertions": insertions,
            }))

        data = pd.DataFrame(nodes)
        data["code_centrality"] = data["degree"] - data["insertions"]
        data.set_index("commit_hash", inplace=True)
        top_degree = data["code_centrality"].nlargest(num_commits)
        degree_data = pd.DataFrame.from_dict({
            "commit": top_degree.index.values,
            "centrality": top_degree.values,
        })
        degree_data.sort_values(["centrality", "commit"],
                                ascending=[False, True],
                                inplace=True)

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            table = degree_data.to_latex(
                index=False,
                multicolumn_format="c",
                multirow=True,
                caption=f"Top {num_commits} Central Code Commits"
            )
            return str(table) if table else ""
        return tabulate(degree_data, degree_data.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)
