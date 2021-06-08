"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd
import seaborn as sns
from benchbuild.utils.cmd import git

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.project.project_util import get_local_project_git


class CommitAuthorInteractionGraphViolinPlot(Plot):
    """
    Plot node degrees of all commit interaction graphs in the current paper
    config.

    Additional arguments:
      - sort: criteria to sort the revisions [degree, time]
    """

    NAME = 'caig_violin'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            added_project_name = False
            project_git = git["-C", get_local_project_git(project_name).path]
            authors = len(project_git("shortlog", "-s", "--all").splitlines())
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            caig = create_blame_interaction_graph(
                project_name, revision
            ).commit_author_interaction_graph()

            for node in caig.nodes:
                node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
                commit = node_attrs["commit"]

                if commit:
                    if not added_project_name:
                        project_names.append(project_name)
                        added_project_name = True
                    nodes.append(({
                        "project": project_name,
                        "commit": commit.commit_hash,
                        "num_authors": caig.degree(node) / authors
                    }))

        data = pd.DataFrame(nodes)
        sns.boxplot(
            x="project",
            y="num_authors",
            data=data,
            order=sorted(project_names)
        )

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
