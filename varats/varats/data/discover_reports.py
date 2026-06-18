"""This modules handles auto discovering of reports from the tool suite."""

from varats import report as __CORE_REPORTS__  # noqa: N812
from varats.data import reports as __REPORTS__  # noqa: N812

__REPORTS_DISCOVERED = False


def initialize_reports() -> None:
    global __REPORTS_DISCOVERED  # noqa: PLW0603
    if not __REPORTS_DISCOVERED:
        # Discover and initialize all Reports
        __REPORTS__.discover()
        __CORE_REPORTS__.discover()
        __REPORTS_DISCOVERED = True
