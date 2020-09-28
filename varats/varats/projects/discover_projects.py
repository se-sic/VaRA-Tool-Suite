"""This modules handles auto discovering of projects from the tool suite."""

from varats import projects as __PROJECTS__

PROJECTS_DISCOVERED = False


def initialize_projects() -> None:
    global PROJECTS_DISCOVERED  # pylint: disable=global-statement
    if not PROJECTS_DISCOVERED:
        # Discover and initialize all projects
        __PROJECTS__.discover()
        PROJECTS_DISCOVERED = True
