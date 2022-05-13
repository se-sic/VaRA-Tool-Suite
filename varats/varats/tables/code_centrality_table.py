"""Module for code centrality tables."""
import logging
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.project.project_util import get_local_project_gits
from varats.table.table import Table, TableDataEmpty
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import (
    ChurnConfig,
    calc_commit_code_churn,
    create_commit_lookup_helper,
    CommitRepoPair,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
)

LOG = logging.Logger(__name__)


def _collect_cig_node_data(
    project_name: str, revision: FullCommitHash
) -> tp.List[tp.Dict[str, tp.Any]]:
    churn_config = ChurnConfig.create_c_style_languages_config()
    cig = create_blame_interaction_graph(project_name,
                                         revision).commit_interaction_graph()
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
            Path(repo_lookup[commit.repository_name].path), commit.commit_hash,
            churn_config
        )
        if insertions == 0:
            LOG.warning(f"Churn for commit {commit} is 0.")
            insertions = 1
        nodes.append(({
            "commit_hash": commit.commit_hash.hash,
            "degree": cig.degree(node),
            "insertions": insertions,
        }))
    return nodes


class TopCentralCodeCommitsTable(
    Table, table_name="top_central_code_commits_table"
):
    """Table showing commits with highest commit interaction graph node
    degrees."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study = self.table_kwargs["case_study"]
        num_commits = self.table_kwargs["num_commits"]

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise TableDataEmpty()

        nodes = _collect_cig_node_data(project_name, revision)
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

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["index"] = False
            kwargs["multicolumn_format"] = "c"
            kwargs["multirow"] = True
            kwargs["caption"] = f"Top {num_commits} Central Code Commits"

        return dataframe_to_table(
            degree_data,
            table_format,
            wrap_table,
            wrap_landscape=True,
            **kwargs
        )


OPTIONAL_NUM_COMMITS: CLIOptionTy = make_cli_option(
    "--num-commits",
    type=int,
    default=10,
    required=False,
    metavar="NUM",
    help="Number of commits in the table."
)


class TopCentralCodeCommitsTableGenerator(
    TableGenerator,
    generator_name="top-central-code-commits-table",
    options=[REQUIRE_MULTI_CASE_STUDY, OPTIONAL_NUM_COMMITS]
):
    """Generates a top-central-code-commits table for the selected case
    study(ies)."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            TopCentralCodeCommitsTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]
