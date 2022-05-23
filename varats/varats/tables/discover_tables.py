"""This modules handles auto discovering of tables from the tool suite."""

from varats import tables as __TABLES__


def initialize_tables() -> None:
    # Discover and initialize all plots
    __TABLES__.discover()
