import typing as tp

import numpy as np
import plotly.grid_objs as gob
import plotly.plotly as ply
import pygit2

from varats.plot.plot import Plot
from varats.project.project_util import (
    get_project_cls_by_name,
    get_local_project_git,
)
from varats.provider.bug.bug import RawBug
from varats.provider.bug.bug_provider import BugProvider


def _plot_chord_diagram_for_raw_bugs(
    project_name: str, bug_set: tp.Set[RawBug]
) -> None:
    """Creates a chord diagram representing relations between introducing/fixing
    commits for a given set of RawBugs."""
    project_repo = get_local_project_git(project_name)

    # maps commit hex -> node id
    commit_count = 0
    map_commits_to_nodes: tp.Dict[str, int] = {}
    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        # node ids are sorted by time
        map_commits_to_nodes[commit.hex] = commit_count
        commit_count += 1

    # compute unit circle coordinates for each commit
    theta_vals = np.linspace(0, 2 * np.pi, commit_count)
    commit_coordinates: tp.List = list()
    for theta in theta_vals:
        commit_coordinates.append(np.cos(theta), np.sin(theta))

    def get_distance(p1, p2):
        # Returns distance between two points
        return np.linalg.norm(np.array(p1) - np.array(p2))

    cp_parameters = [1.2, 1.5, 1.8, 2.1]
    #thresholds for different distance intervals
    distance_thresholds[
        0,
        get_distance([1, 0], 2 * [np.sqrt(2) / 2]),
        np.sqrt(2),
        get_distance([1, 0], [-np.sqrt(2) / 2, np.sqrt(2) / 2]), 2.0]

    def get_interval(distance):
        #get right interval for given distance using distance thresholds
        k = 0
        while distance_thresholds[k] < distance:
            k += 1
        return k - 1

    # implements bezier edges to display between commit nodes
    def get_bezier_curve(ctrl_points, num_points=5):
        n = len(ctrl_points)

        def get_coordinate(factor):
            points_cp = np.copy(ctrl_points)
            for r in range(1, n):
                points_cp[:n - r, :] = (
                    1 - factor
                ) * points_cp[:n - r, :] + factor * points_cp[1:n - r + 1, :]
            return points_cp[0, :]

        point_space = np.linspace(0, 1, num_points)
        return np.array([
            get_coordinate(point_space[k]) for k in range(num_points)
        ])

    lines = []
    for bug in bug_set:
        bug_fix = bug.fixing_commit
        fix_ind = map_commits_to_nodes[bug_fix]

        for bug_introduction in bug.introducing_commits:
            intro_ind = map_commits_to_nodes[bug_introduction]
            # TODO draw line between them

    # TODO draw graph


class BugFixingRelationPlot(Plot):
    """Plot showing which commit fixed a bug introduced by which commit."""

    NAME = 'bug_relation_graph'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def supports_stage_separation() -> bool:
        return False

    def plot(self, view_mode: bool) -> None:
        """Plots bug plot for the whole project."""
        project_name = self.plot_kwargs["project"]

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )

        raw_bugs = bug_provider.find_all_raw_bugs()
        _plot_chord_diagram_for_raw_bugs(project_name, raw_bugs)

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return set()
