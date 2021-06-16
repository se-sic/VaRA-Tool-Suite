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
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.project.project_util import get_local_project_gits
from varats.utils.git_util import (
    create_commit_lookup_helper,
    CommitRepoPair,
    DUMMY_COMMIT,
    ChurnConfig,
    calc_repo_code_churn,
)


class CentralCodeScatterPlot(Plot):
    """
    Plot commit node degrees vs.

    commit size.
    """

    NAME = 'central_code_scatter'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        if "project" not in self.plot_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.plot_kwargs:
                case_studies = [self.plot_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.plot_kwargs["project"]
                )

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        churn_config = ChurnConfig.create_c_style_languages_config()

        degree_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            cig = create_blame_interaction_graph(project_name, revision
                                                ).commit_interaction_graph()
            commit_lookup = create_commit_lookup_helper(project_name)
            repo_lookup = get_local_project_gits(project_name)
            code_churn_lookup: tp.Dict[str, tp.Dict[str, tp.Tuple[int, int,
                                                                  int]]] = {}
            for repo_name, repo in repo_lookup.items():
                code_churn_lookup[repo_name] = calc_repo_code_churn(
                    repo, churn_config
                )

            def filter_nodes(node: CommitRepoPair) -> bool:
                if node.commit_hash == DUMMY_COMMIT:
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
                    "project": project_name,
                    "commit_hash": commit.commit_hash,
                    "insertions": insertions,
                    "node_degree": cig.degree(node),
                }))
            data = pd.DataFrame(nodes)
            data["insertions"] = normalize(data["insertions"])
            data["node_degree"] = normalize(data["node_degree"])
            degree_data.append(data)

        full_data = pd.concat(degree_data)
        full_data = full_data[full_data["insertions"] <= 0.2]
        multivariate_grid(
            "insertions", "node_degree", "project", full_data, global_kde=False
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
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
        if "project" not in self.plot_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.plot_kwargs:
                case_studies = [self.plot_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.plot_kwargs["project"]
                )

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        degree_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            aig = create_blame_interaction_graph(project_name, revision
                                                ).author_interaction_graph()

            nodes: tp.List[tp.Dict[str, tp.Any]] = []
            for node in aig.nodes:
                node_attrs = tp.cast(AIGNodeAttrs, aig.nodes[node])
                nodes.append(({
                    "project": project_name,
                    "author": node_attrs["author"],
                    "node_degree": aig.degree(node),
                    "num_commits": node_attrs["num_commits"],
                }))
            data = pd.DataFrame(nodes)
            data["num_commits"] = normalize(data["num_commits"])
            data["node_degree"] = normalize(data["node_degree"])
            degree_data.append(data)

        multivariate_grid(
            "num_commits",
            "node_degree",
            "project",
            pd.concat(degree_data),
            global_kde=False
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
