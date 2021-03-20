import typing as tp
from pathlib import Path

import numpy as np
import plotly.graph_objs as gob
import plotly.offline as offply
import pygit2

from varats.plot.plot import Plot, PlotDataEmpty
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
    map_commit_to_id: tp.Dict[str, int] = {}
    commit_type: tp.Dict[str, str] = {}
    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        # node ids are sorted by time
        map_commit_to_id[commit.hex] = commit_count
        commit_type[commit.hex] = 'default'
        commit_count += 1

    # if less than 2 commits, no graph can be drawn!
    if commit_count < 2:
        raise PlotDataEmpty

    # compute unit circle coordinates for each commit
    # move unit circle such that HEAD is on top
    # use commit_count + 1 since first and last coordinates are equal
    theta_vals = np.linspace(-3 * np.pi / 2, np.pi / 2, commit_count + 1)
    commit_coordinates: tp.List = list()
    for theta in theta_vals:
        commit_coordinates.append(np.array([np.cos(theta), np.sin(theta)]))

    def get_distance(p1, p2):
        # Returns distance between two points
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def get_commit_distance(fix, intro):
        # Returns distance betweeen fix and intro of a bug
        return map_commit_to_id[fix] - map_commit_to_id[intro]

    #defining some constants for diagram generation
    cp_parameters = [1.2, 1.5, 1.8, 2.1]
    distance_thresholds = [
        0,
        get_distance([1, 0], 2 * [np.sqrt(2) / 2]),
        np.sqrt(2),
        get_distance([1, 0], [-np.sqrt(2) / 2, np.sqrt(2) / 2]), 2.0
    ]
    commit_distance_thresholds = [
        0,
        round(0.25 * commit_count),
        round(0.5 * commit_count),
        round(0.75 * commit_count), commit_count
    ]
    edge_colors = ['#d4daff', '#84a9dd', '#5588c8', '#6d8acf']

    node_colors = {
        'fix': 'rgba(0, 177, 106, 1)',
        'introduction': 'rgba(240, 52, 52, 1)',
        'introducing fix': 'rgba(235, 149, 50, 1)',
        'head': 'rgba(142, 68, 173, 1)',
        'fixing head': 'rgba(142, 68, 173, 1)',
        'default': 'rgba(232, 236, 241, 1)'
    }

    def get_interval(distance):
        #get right interval for given distance using distance thresholds
        #interval indices are in [0,3] for 5 thresholds
        k = 0
        while distance_thresholds[k] < distance:
            k += 1
        return k - 1

    def get_commit_interval(distance):
        k = 0
        while commit_distance_thresholds[k] < distance:
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

    # draw relations and preprocess commit types
    lines = []
    intro_annotations = []
    nodes = []
    for bug in bug_set:
        bug_fix = bug.fixing_commit
        fix_ind = map_commit_to_id[bug_fix]
        fix_coordinates = commit_coordinates[fix_ind]

        commit_type[bug_fix] = 'introducing fix' if commit_type[
            bug_fix] == 'introduction' else 'fix'

        for bug_introduction in bug.introducing_commits:
            intro_ind = map_commit_to_id[bug_introduction]
            intro_coordinates = commit_coordinates[intro_ind]

            commit_type[bug_introduction] = 'introducing fix' if commit_type[
                bug_introduction] == 'fix' else 'introduction'

            # get distance between the points and the respective interval index
            dist = get_distance(fix_coordinates, intro_coordinates)
            interval = get_interval(dist)

            commit_dist = get_commit_distance(bug_fix, bug_introduction)
            commit_interval = get_commit_interval(commit_dist)
            color = edge_colors[commit_interval]

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

    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        # draw commit nodes using preprocessed commit types
        commit_id = map_commit_to_id[commit.hex]

        if commit.hex == project_repo.head.target.hex:
            commit_type[commit.hex
                       ] = 'fixing head' if commit_type[commit.hex
                                                       ] == 'fix' else 'head'

        # set node data according to commit type
        node_size = 10 if commit_type[commit.hex] == 'head' or commit_type[
            commit.hex] == 'fixing head' else 8
        node_label = f'{commit_type[commit.hex]} - {commit.hex}'
        node_color = node_colors[commit_type[commit.hex]]

        nodes.append(
            gob.Scatter(
                x=[commit_coordinates[commit_id][0]],
                y=[commit_coordinates[commit_id][1]],
                mode='markers',
                name='',
                marker=dict(symbol='circle', size=node_size, color=node_color),
                text=node_label,
                hoverinfo='text'
            )
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
        margin=dict(l=0, r=0, b=0, t=50),
        plot_bgcolor='rgba(0,0,0,0)'
    )

    data = lines + intro_annotations + nodes
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
        project_name = self.plot_kwargs['project']

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )

        raw_bugs = bug_provider.find_all_raw_bugs()
        self.__figure = _plot_chord_diagram_for_raw_bugs(project_name, raw_bugs)

    def show(self) -> None:
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return
        self.__figure.show()

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'html'
    ) -> None:
        try:
            self.plot(False)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        if filetype == 'html':
            self.__figure.write_html(self.plot_file_name(filetype))
        elif filetype == 'json':
            self.__figure.write_json(self.plot_file_name(filetype))
        else:
            self.__figure.write_image(self.plot_file_name(filetype))

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        return set()
