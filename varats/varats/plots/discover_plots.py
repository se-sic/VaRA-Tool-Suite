"""This modules handles auto discovering of plots from the tool suite."""

from varats import plots as __PLOTS__


def initialize_plots() -> None:
    # Discover and initialize all plots
    __PLOTS__.discover()
