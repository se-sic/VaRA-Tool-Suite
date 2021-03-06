import typing as tp

import numpy as np
import plotly.graph_objs as gob
import plotly.offline as offply
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
) -> gob.Figure:
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
    # move unit circle such that HEAD is on top
    theta_vals = np.linspace(-3 * np.pi / 2, np.pi / 2, commit_count)
    commit_coordinates: tp.List = list()
    for theta in theta_vals:
        commit_coordinates.append(np.array([np.cos(theta), np.sin(theta)]))

    def get_distance(p1, p2):
        # Returns distance between two points
        return np.linalg.norm(np.array(p1) - np.array(p2))

    #defining some constants for diagram generation
    cp_parameters = [1.2, 1.5, 1.8, 2.1]
    distance_thresholds = [
        0.0,
        get_distance([1, 0], 2 * [np.sqrt(2) / 2]),
        np.sqrt(2),
        get_distance([1, 0], [-np.sqrt(2) / 2, np.sqrt(2) / 2]), 2.0
    ]
    edge_colors = ['#d4daff', '#84a9dd', '#5588c8', '#6d8acf']
    node_color = 'rgba(0,51,181, 0.85)'
    init_color = 'rgba(207, 0, 15, 1)'

    def get_interval(distance):
        #get right interval for given distance using distance thresholds
        #interval indices are in [0,3] for 5 thresholds
        k = 0
        while distance_thresholds[k] < distance:
            k += 1
        return k - 1

    # implements bezier edges to display between commit nodes
    def get_bezier_curve(ctrl_points, num_points=5):
        n = len(ctrl_points)

        def get_coordinate_on_curve(factor):
            points_cp = np.copy(ctrl_points)
            for r in range(1, n):
                points_cp[:n - r, :] = (
                    1 - factor
                ) * points_cp[:n - r, :] + factor * points_cp[1:n - r + 1, :]
            return points_cp[0, :]

        point_space = np.linspace(0, 1, num_points)
        return np.array([
            get_coordinate_on_curve(point_space[k]) for k in range(num_points)
        ])

    lines = []
    intro_annotations = []
    nodes = []
    for bug in bug_set:
        bug_fix = bug.fixing_commit
        fix_ind = map_commits_to_nodes[bug_fix]
        fix_coordinates = commit_coordinates[fix_ind]

        for bug_introduction in bug.introducing_commits:
            intro_ind = map_commits_to_nodes[bug_introduction]
            intro_coordinates = commit_coordinates[intro_ind]

            # get distance between the points and the respective interval index
            dist = get_distance(fix_coordinates, intro_coordinates)
            interval = get_interval(dist)
            color = edge_colors[interval]

            control_points = [
                fix_coordinates, fix_coordinates / cp_parameters[interval],
                intro_coordinates / cp_parameters[interval], intro_coordinates
            ]
            curve_points = get_bezier_curve(control_points)

            lines.append(
                gob.Scatter(
                    x=curve_points[:, 0],
                    y=curve_points[:, 1],
                    mode='lines',
                    line=dict(color=color, shape='spline'),
                    hoverinfo='none'
                )
            )

            intro_annotations.append(
                gob.Scatter(
                    x=curve_points[:, 0],
                    y=curve_points[:, 1],
                    mode='markers',
                    marker=dict(size=0.5, color=edge_colors),
                    text=f'introduced by {bug_introduction}',
                    hoverinfo='text'
                )
            )

        #add fixing commits as vertices
        nodes.append(
            gob.Scatter(
                x=[fix_coordinates[0]],
                y=[fix_coordinates[1]],
                mode='markers',
                name='',
                marker=dict(
                    symbol='circle',
                    size=10,
                    color=node_color,
                    line=dict(color=edge_colors, width=0.5)
                ),
                text=f'bug fix: {bug_fix}',
                hoverinfo='text'
            )
        )

    init = gob.Scatter(
        x=[commit_coordinates[0][0]],
        y=[commit_coordinates[0][1]],
        mode='markers',
        name='',
        marker=dict(
            symbol='circle',
            size=12,
            color=init_color,
            line=dict(color=edge_colors, width=0.5)
        ),
        text='HEAD',
        hoverinfo='text'
    )

    title = f'Bug fixing relations for {project_name}'
    axis = dict(
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title=''
    )  #hide the axis

    width = 900
    height = 900
    layout = gob.Layout(
        title=title,
        showlegend=False,
        autosize=False,
        width=width,
        height=height,
        xaxis=dict(axis),
        yaxis=dict(axis),
        hovermode='closest',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    data = lines + intro_annotations + nodes + [init]
    return gob.Figure(data=data, layout=layout)


class BugFixingRelationPlot(Plot):
    """Plot showing which commit fixed a bug introduced by which commit."""

    NAME = 'bug_relation_graph'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    @staticmethod
    def supports_stage_separation() -> bool:
        return False

    def plot(self, view_mode: bool) -> None:
        """Plots bug plot for the whole project."""
        project_name = self.plot_kwargs["project"]

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )

        raw_bugs = bug_provider.find_all_raw_bugs()
        figure = _plot_chord_diagram_for_raw_bugs(project_name, raw_bugs)
        #filename must be left empty for plot command
        if view_mode:
            figure.show()
        else:
            offply.plot(figure, filename=self.plot_file_name(""))

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return set()
