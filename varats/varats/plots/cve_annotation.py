"""Annotate CVE/CWE data to a plot."""
import typing as tp

from benchbuild.project import Project
from matplotlib import axes

from varats.mapping.commit_map import create_lazy_commit_map_loader
from varats.provider.cve.cve_provider import CVEProvider
from varats.utils.git_util import FullCommitHash


def draw_cves(
    axis: axes.Axes, project: tp.Type[Project],
    revisions: tp.List[FullCommitHash], cve_line_width: int, cve_color: str,
    label_size: int, vertical_alignment: str
) -> None:
    """
    Annotates CVEs for a project in an existing plot.

    Args:
        axis: the axis to use for the plot
        project: the project to add CVEs for
        revisions: a list of revisions included in the plot in the order they
                   appear on the x-axis
        cve_line_width: the line width of CVE annotations
        cve_color: the color of CVE annotations
        label_size: the label size of CVE annotations
        vertical_alignment: the vertical alignment of CVE annotations
    """
    cmap = create_lazy_commit_map_loader(project.NAME)()
    revision_time_ids = [cmap.time_id(rev) for rev in revisions]

    cve_provider = CVEProvider.get_provider_for_project(project)
    for revision, cves in cve_provider.get_revision_cve_tuples():
        cve_time_id = cmap.time_id(revision)
        if cve_time_id in revision_time_ids:
            index = float(revisions.index(revision))
        else:
            # revision not in sample; draw line between closest samples
            index = len([x for x in revision_time_ids if x < cve_time_id]) - 0.5

        transform = axis.get_xaxis_transform()
        for cve in cves:
            axis.axvline(
                index,
                label=cve.cve_id,
                linewidth=cve_line_width,
                color=cve_color
            )
            axis.text(
                index + 0.1,
                0,
                cve.cve_id,
                transform=transform,
                rotation=90,
                size=label_size,
                color=cve_color,
                va=vertical_alignment
            )
