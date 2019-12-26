"""
Generate plots to visualize code churn of a software repository.
"""
import typing as tp

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.axes as axes
import matplotlib.style as style

from varats.data.reports.commit_report import CommitMap
from varats.paper.case_study import CaseStudy
from varats.plots.plot import Plot
from varats.utils.project_util import get_local_project_git
from varats.utils.git_util import calc_repo_code_churn


def _build_repo_churn_table(project_name: str,
                            commit_map: CommitMap) -> pd.DataFrame:

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(columns=[
            "revision", "rev_id", "insertions", "deletions", "changed_files"
        ])
        df_layout.rev_id = df_layout.rev_id.astype('int32')
        df_layout.insertions = df_layout.insertions.astype('int64')
        df_layout.deletions = df_layout.deletions.astype('int64')
        df_layout.changed_files = df_layout.changed_files.astype('int64')
        return df_layout

    repo = get_local_project_git(project_name)
    code_churn = calc_repo_code_churn(repo)
    churn_data = pd.DataFrame({
        "revision": [x for x in code_churn],
        "rev_id": [commit_map.time_id(x) for x in code_churn],
        "insertions": [x[1] for x in code_churn.values()],
        "deletions": [x[2] for x in code_churn.values()],
        "changed_files": [x[0] for x in code_churn.values()]
    })

    return pd.concat([create_dataframe_layout(), churn_data])


def draw_code_churn(axis: axes.SubplotBase,
                    project_name: str,
                    commit_map: CommitMap,
                    revision_selector: tp.Callable[[str], bool] = lambda x: True
                   ) -> None:
    """
    Draws a churn plot onto an axis, showing insertions with green and
    deletions with red.

    Args:
        revision_selector: takes a revision string and returns True if this rev
                           should be included
    """
    code_churn = _build_repo_churn_table(project_name, commit_map)

    # code_churn = cs_selector(code_churn)
    code_churn = code_churn[code_churn.apply(
        lambda x: revision_selector(x['revision']), axis=1)]

    code_churn.sort_values(by=['rev_id'], inplace=True)

    revisions = code_churn.rev_id.astype(str) + '-' + code_churn.revision.map(
        lambda x: x[:10])

    axis.fill_between(revisions, code_churn.insertions, 0, facecolor='green')
    axis.fill_between(
        revisions,
        # we need a - here to visualize deletions as negative additions
        -code_churn.deletions,
        0,
        facecolor='red')


class RepoChurnPlot(Plot):
    """
    Plot to visualize code churn for a git repository.
    """

    def __init__(self, **kwargs: tp.Any) -> None:
        super(RepoChurnPlot, self).__init__("repo_churn", **kwargs)

    def plot(self, view_mode: bool) -> None:
        plot_cfg = {
            'linewidth': 1 if view_mode else 0.25,
            'legend_size': 8 if view_mode else 2,
            'xtick_size': 10 if view_mode else 2,
        }
        style.use(self.style)

        case_study: CaseStudy = self.plot_kwargs['plot_case_study']

        _, axis = plt.subplots()
        draw_code_churn(
            axis, self.plot_kwargs['project'], self.plot_kwargs['get_cmap'](),
            case_study.has_revision if case_study else lambda x: True)
        axis.set_yscale('symlog')

        for x_label in axis.get_xticklabels():
            x_label.set_fontsize(plot_cfg['xtick_size'])
            x_label.set_rotation(270)
            x_label.set_fontfamily('monospace')

    def show(self) -> None:
        self.plot(True)
        plt.show()

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError
