"""This modules handles auto discovering of reports from the tool suite."""

from varats.data import reports as __REPORTS__


def initialize_reports() -> None:
    # Discover and initialize all Reports
    __REPORTS__.discover()
