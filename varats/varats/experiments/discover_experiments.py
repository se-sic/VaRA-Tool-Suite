"""This modules handles auto discovering of experiments from the tool suite."""

from varats import experiments as __EXPERIMENTS__


def initialize_experiments() -> None:
    # Discover and initialize all Reports
    __EXPERIMENTS__.discover()
