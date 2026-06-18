"""This modules handles auto discovering of experiments from the tool suite."""

from varats import experiments as __EXPERIMENTS__  # noqa: N812

__EXPERIMENTS_DISCOVERED: bool = False


def initialize_experiments() -> None:
    global __EXPERIMENTS_DISCOVERED  # noqa: PLW0603
    if not __EXPERIMENTS_DISCOVERED:
        # Discover and initialize all Experiments
        __EXPERIMENTS__.discover()
        __EXPERIMENTS_DISCOVERED = True
