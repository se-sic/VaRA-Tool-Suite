"""This modules handles auto discovering of projects from the tool suite."""

from varats import projects as __PROJECTS__  # noqa: N812

__PROJECTS_DISCOVERED = False


def initialize_projects() -> None:
    """Discover and initialize all projects."""
    global __PROJECTS_DISCOVERED  # noqa: PLW0603
    if not __PROJECTS_DISCOVERED:
        __PROJECTS__.discover()
        __PROJECTS_DISCOVERED = True
