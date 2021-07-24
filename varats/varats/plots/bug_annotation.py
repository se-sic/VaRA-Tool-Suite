"""Annotate Bug data to a plot."""
import typing as tp

from benchbuild.project import Project
from matplotlib import axes

from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.provider.bug.bug_provider import BugProvider
from varats.utils.git_util import FullCommitHash


def draw_bugs(
    axis: axes.Axes,
    project: tp.Type[Project],
    revisions: tp.List[FullCommitHash],
    extra_plot_cfg: tp.Optional[tp.Dict[str, tp.Any]] = None
) -> None:
    """
    Annotates bugs for a project in an existing plot.

    Args:
        axis: the axis to use for the plot
        project: the project to add bugs for
        revisions: a list of revisions included in the plot in the order they
                   appear on the x-axis
        extra_plot_cfg:
            * linewidth
            * color
            * vertical_alignment
            * label_size
    """
    plot_cfg = {
        "linewidth": 1,
        "color": "green",
        "vertical_alignment": "bottom",
        "label_size": 2,
    }
    if extra_plot_cfg is not None:
        plot_cfg.update(extra_plot_cfg)

    cmap = create_lazy_commit_map_loader(project.NAME)()
    revision_time_ids = [cmap.time_id(rev) for rev in revisions]

    bug_provider = BugProvider.get_provider_for_project(project)
    for rawbug in bug_provider.find_raw_bugs():
        bug_time_id = cmap.time_id(rawbug.fixing_commit)
        if bug_time_id in revision_time_ids:
            index = float(revisions.index(rawbug.fixing_commit))
        else:
            # revision not in sample; draw line between closest samples
            index = len([x for x in revision_time_ids if x < bug_time_id]) - 0.5

        label = " ".join([f"#{rawbug.issue_id}"])

        transform = axis.get_xaxis_transform()
        axis.axvline(
            index,
            label=label,
            linewidth=plot_cfg["linewidth"],
            color=plot_cfg["color"]
        )
        axis.text(
            index + 0.1,
            0,
            label,
            transform=transform,
            rotation=90,
            size=plot_cfg["label_size"],
            color=plot_cfg["color"],
            va=plot_cfg["vertical_alignment"]
        )
