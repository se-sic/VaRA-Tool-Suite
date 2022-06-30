"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd
import seaborn as sns
from benchbuild.utils.revision_ranges import RevisionRange
from git import Commit
from pygit2 import Repository

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import processed_revisions_for_case_study
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.project.project_util import (
    get_local_project_git,
    get_local_project_git_path,
)
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.git_util import FullCommitHash, CommitRepoPair


def get_submodule_changes_for_commit(
    repo: Repository, commit: Commit
) -> tp.List[tp.Tuple[str, str, str]]:
    submodules = repo.listall_submodules()
    submodule_changes: tp.List[tp.Tuple[str, str, str]] = []
    for parent in commit.parents:
        diff = repo.diff(parent, commit)
        for delta in list(diff.deltas):
            if delta.new_file.path in submodules:
                submodule_name = repo.lookup_submodule(delta.new_file.path).name
                submodule_changes.append((
                    submodule_name, str(delta.old_file.id),
                    str(delta.new_file.id)
                ))
    return submodule_changes


class LibInteractionPlot(Plot, plot_name='lib_inter'):
    """Library Interaction Plot."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["case_study"]
        project_name = case_study.project_name
        project_repo = get_local_project_git(project_name)

        revisions = processed_revisions_for_case_study(case_study, BlameReport)

        dfs: tp.List[pd.DataFrame] = []

        for analyzed_revision in revisions:
            commit = project_repo.get(analyzed_revision.hash)
            submodule_changes = get_submodule_changes_for_commit(
                project_repo, commit
            )
            new_lib_commits: tp.List[CommitRepoPair] = []
            for name, old, new in submodule_changes:
                rev_range = RevisionRange(old, new)
                rev_range.init_cache(
                    str(get_local_project_git_path(project_name, name))
                )
                for rev in rev_range:
                    new_lib_commits.append(
                        CommitRepoPair(FullCommitHash(rev), name)
                    )

            cig = create_blame_interaction_graph(
                project_name, analyzed_revision
            ).commit_interaction_graph()
            affected_commits: tp.Set[CommitRepoPair] = set()
            for node in new_lib_commits:
                if node in cig.nodes:
                    affected_commits.update(cig.successors(node))
                    affected_commits.update(cig.predecessors(node))

            dfs.append(
                pd.DataFrame({
                    "revision": analyzed_revision.short_hash,
                    "commits": cig.number_of_nodes(),
                    "affected": len(affected_commits)
                },
                             index=[analyzed_revision.hash])
            )

        df = pd.concat(dfs)
        ax = sns.lineplot(data=df, x="revision", y="commits")
        sns.lineplot(data=df, x="revision", y="affected", ax=ax)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class LibInteractionPlotGenerator(
    PlotGenerator,
    generator_name="lib-inter",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a violin plot showing the distribution of interacting authors
    for each case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            LibInteractionPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
