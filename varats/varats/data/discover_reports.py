"""This modules handles auto discovering of reports from the tool suite."""

from varats import report as __CORE_REPORTS__
from varats.data import reports as __REPORTS__

__REPORTS_DISCOVERED = False


def initialize_reports() -> None:
    global __REPORTS_DISCOVERED  # pylint: disable=global-statement
    if not __REPORTS_DISCOVERED:
        # Discover and initialize all Reports
        __REPORTS__.discover()
        __CORE_REPORTS__.discover()
        __REPORTS_DISCOVERED = True
