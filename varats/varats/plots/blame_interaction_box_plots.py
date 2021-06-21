"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd
import seaborn as sns

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    CIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.project.project_util import get_local_project_gits
from varats.utils.git_util import (
    ChurnConfig,
    create_commit_lookup_helper,
    CommitRepoPair,
    DUMMY_COMMIT,
    calc_repo_code_churn,
)


class CommitAuthorInteractionGraphViolinPlot(Plot):
    """Box plot of commit-author interaction commit node degrees."""

    NAME = 'caig_box'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            added_project_name = False
            # project_git = git["-C", get_local_project_git(project_name).path]
            # authors = len(project_git("shortlog", "-s", "--all").splitlines())
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            caig = create_blame_interaction_graph(
                project_name, revision
            ).commit_author_interaction_graph(
                outgoing_interactions=True, incoming_interactions=True
            )

            authors = len([
                1 for node in caig.nodes if caig.nodes[node]["author"]
            ])

            for node in caig.nodes:
                node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
                commit = node_attrs["commit"]

                if commit:
                    if not added_project_name:
                        project_names.append(project_name)
                        added_project_name = True
                    nodes.append(({
                        "Case Study": project_name,
                        "commit": commit.commit_hash,
                        "# Interacting Authors": caig.degree(node) / authors
                    }))

        data = pd.DataFrame(nodes)
        sns.violinplot(
            x="Case Study",
            y="# Interacting Authors",
            data=data,
            order=sorted(project_names),
            inner=None,
            color=".95"
        )
        sns.stripplot(
            x="Case Study",
            y="# Interacting Authors",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class CommitAuthorInteractionGraphGrid(Plot):
    """Box plot of commit-author interaction commit node degrees."""

    NAME = 'caig_grid'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        churn_config = ChurnConfig.create_c_style_languages_config()

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        degree_data: tp.List[pd.DataFrame] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            added_project_name = False

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

            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            big = create_blame_interaction_graph(project_name, revision)
            cig = big.commit_interaction_graph()
            caig = big.commit_author_interaction_graph(
                outgoing_interactions=True, incoming_interactions=True
            )

            authors = len([
                1 for node in caig.nodes if caig.nodes[node]["author"]
            ])

            cig_data: tp.Dict[CommitRepoPair, int] = {}
            for node in cig.nodes:
                node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
                commit = node_attrs["commit"]
                if not filter_nodes(commit):
                    continue
                cig_data[commit] = cig.degree(node)

            nodes: tp.List[tp.Dict[str, tp.Any]] = []
            for node in caig.nodes:
                node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
                commit = node_attrs["commit"]

                if commit:
                    if not filter_nodes(commit):
                        continue
                    if not added_project_name:
                        project_names.append(project_name)
                        added_project_name = True

                    _, insertions, _ = code_churn_lookup[commit.repository_name
                                                        ][commit.commit_hash]
                    nodes.append(({
                        "project": project_name,
                        "commit": commit.commit_hash,
                        "num_authors": caig.degree(node) / authors,
                        "insertions": insertions,
                        "node_degree": cig_data[commit]
                    }))

            data = pd.DataFrame(nodes)
            data["insertions"] = data["insertions"]
            data["node_degree"] = normalize(data["node_degree"])
            degree_data.append(data)

        full_data = pd.concat(degree_data)
        # full_data = full_data[full_data["insertions"] <= 0.2]
        grid = sns.PairGrid(
            x_vars=["node_degree", "insertions"],
            y_vars=["num_authors"],
            data=full_data,
            hue="project"
        )
        grid.map(sns.scatterplot, size=2, alpha=0.25)
        grid.add_legend()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
