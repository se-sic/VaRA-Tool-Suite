"""This modules handles auto discovering of reports from the tool suite."""

from varats import report as __CORE_REPORTS__
from varats.data import reports as __REPORTS__


def initialize_reports() -> None:
    # Discover and initialize all Reports
    __REPORTS__.discover()
    __CORE_REPORTS__.discover()
