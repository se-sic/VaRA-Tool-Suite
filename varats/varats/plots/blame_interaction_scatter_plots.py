"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
    AIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.project.project_util import get_local_project_gits
from varats.utils.git_util import (
    create_commit_lookup_helper,
    CommitRepoPair,
    ChurnConfig,
    calc_repo_code_churn,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
)


def apply_tukeys_fence(
    data: pd.DataFrame, column: str, k: float
) -> pd.DataFrame:
    """
    Removes rows which are outliers in the given column using Tukey's fence.

    Tukey's fence defines all values to be outliers that are outside the range
    `[q1 - k * (q3 - q1), q3 + k * (q3 - q1)]`, i.e., values that are further
    than `k` times the inter-quartile range away from the first or third
    quartile.

    Common values for ``k``:
    - 2.2 (“Fine-Tuning Some Resistant Rules for Outlier Labeling”
           Hoaglin and Iglewicz (1987))
    - 1.5 (outliers, “Exploratory Data Analysis”, John W. Tukey (1977))
    - 3.0 (far out outliers, “Exploratory Data Analysis”, John W. Tukey (1977))

    Args:
        data: data to remove outliers from
        column: column to use for outlier detection
        k: multiplicative factor on the inter-quartile-range

    Returns:
        the data without outliers
    """
    q1 = data[column].quantile(0.25)
    q3 = data[column].quantile(0.75)
    iqr = q3 - q1
    return data.loc[(data[column] >= q1 - k * iqr) &
                    (data[column] <= q3 + k * iqr)]


class CentralCodeScatterPlot(Plot):
    """
    Plot commit node degrees vs.

    commit size.
    """

    NAME = 'central_code_scatter'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]
        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()

        commit_lookup = create_commit_lookup_helper(project_name)
        repo_lookup = get_local_project_gits(project_name)
        churn_config = ChurnConfig.create_c_style_languages_config()
        code_churn_lookup: tp.Dict[str, tp.Dict[FullCommitHash,
                                                tp.Tuple[int, int, int]]] = {}
        for repo_name, repo in repo_lookup.items():
            code_churn_lookup[repo_name] = calc_repo_code_churn(
                repo, churn_config
            )

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
            _, insertions, _ = code_churn_lookup[commit.repository_name][
                commit.commit_hash]
            nodes.append(({
                "Case Study": project_name,
                "commit_hash": commit.commit_hash,
                "Commit Size": insertions,
                "Node Degree": cig.degree(node),
            }))
        data = pd.DataFrame(nodes)
        data = apply_tukeys_fence(data, "Commit Size", 3.0)
        grid = multivariate_grid(
            "Commit Size", "Node Degree", "Case Study", data, global_kde=False
        )

        ax = grid.ax_joint
        ax.axvline(data["Commit Size"].quantile(0.20), color="red")
        ax.axhline(data["Node Degree"].quantile(0.80), color="red")

        # highlight_data = data[data["commit_hash"] == FullCommitHash(
        #     "348e6946c187eb68839e71a03101d75b5865a389"
        # )]
        #
        # ax.scatter(
        #     x=highlight_data["Commit Size"],
        #     y=highlight_data["Node Degree"],
        #     color="red",
        #     marker="x",
        #     linewidth=2
        # )
        # ax.annotate(
        #     "348e694",
        #     xy=(highlight_data["Commit Size"], highlight_data["Node Degree"]),
        #     xycoords="data",
        #     xytext=(0.2, 0.9),
        #     textcoords='axes fraction',
        #     arrowprops=dict(arrowstyle="-|>", shrinkB=5, facecolor="black")
        # )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class AuthorInteractionScatterPlot(Plot):
    """
    Plot author node degrees vs.

    number of (surviving) commits.
    """

    NAME = 'author_interaction_scatter'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

        aig = create_blame_interaction_graph(project_name, revision
                                            ).author_interaction_graph()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, aig.nodes[node])
            nodes.append(({
                "project": project_name,
                "author": node_attrs["author"],
                "# Interacting authors": aig.degree(node),
                "# Commits": node_attrs["num_commits"],
            }))
        data = pd.DataFrame(nodes)
        multivariate_grid(
            "# Commits",
            "# Interacting authors",
            "project",
            data,
            global_kde=False
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError
