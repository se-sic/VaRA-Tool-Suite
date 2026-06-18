"""This modules handles auto discovering of plots from the tool suite."""

from varats import plots as __PLOTS__  # noqa: N812

__PLOTS_DISCOVERED = False


def initialize_plots() -> None:
    global __PLOTS_DISCOVERED  # noqa: PLW0603
    if not __PLOTS_DISCOVERED:
        # Discover and initialize all plots
        __PLOTS__.discover()
        __PLOTS_DISCOVERED = True
