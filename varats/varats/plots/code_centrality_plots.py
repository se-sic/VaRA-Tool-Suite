"""Module for code centrality plots."""
import logging
import typing as tp
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import style

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.project.project_util import get_local_project_gits
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    ChurnConfig,
    calc_commit_code_churn,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
)

LOG = logging.Logger(__name__)


class CodeCentralityPlot(Plot, plot_name='code_centrality'):
    """Plot code centrality."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["case_study"]

        style.use(self.plot_config.style())
        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle("Central Code")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Code Centrality")
        axes.set_xlabel("Commits")

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

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
                "commit_hash": commit.commit_hash,
                "degree": cig.degree(node),
                "insertions": insertions,
            }))

        data = pd.DataFrame(nodes)
        data["code_centrality"] = data["degree"] - data["insertions"]
        data.sort_values(by="code_centrality", inplace=True)
        centrality_scores = data.loc[:, ["commit_hash", "code_centrality"]]
        centrality_scores.sort_values(by="code_centrality", inplace=True)
        axes.plot(centrality_scores["code_centrality"].values)
        axes.set_ylim(bottom=0)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CodeCentralityPlotGenerator(
    PlotGenerator,
    generator_name="code-centrality",
    options=[REQUIRE_CASE_STUDY]
):
    """Generates quantile plot for a code centrality measure for commits."""

    def generate(self) -> tp.List[Plot]:
        return [CodeCentralityPlot(self.plot_config, **self.plot_kwargs)]
